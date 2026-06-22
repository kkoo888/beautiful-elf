"""专家团 LangGraph 图架构 — PM 委派模式

架构:
  1. pm_analyze: PM 分析任务，输出分配计划（Send API 动态 fan-out）
  2. expert_execute: 单个专家执行子任务（并行，通过 Send 并发）
  3. pm_evaluate: PM 评估所有专家结果，决定通过/返工
  4. pm_report: PM 汇总最终报告

图结构:
  START → pm_analyze → [Send("expert", assignment) for each] → pm_evaluate
                                                                      │
                                                                      ├─ pass → pm_report → END
                                                                      └─ fail → pm_analyze（Loop，current_round + 1）

关键设计:
  - Send API 动态 fan-out：pm_analyze 返回 assignments，通过 Send 并发派发专家节点
  - Annotated[list, add] reducer：专家结果自动合并（并行写入安全）
  - 条件路由：pm_evaluate 根据 overall_pass 决定走向
  - Loop 上限：max_rounds 控制最大返工轮次
  - get_stream_writer()：节点内推送实时事件（替代 asyncio.Queue）
  - WebSocket 保留：_ws_broadcast 推送前端实时状态
"""
import json
import re
from datetime import datetime
from typing import Any
from langgraph.graph import StateGraph, END, START, CompiledGraph
from langgraph.types import Send
from typing_extensions import TypedDict, Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import _content_blocks_to_str
from app.core.logging import get_logger
from app.agent.expert_team.reasoning import generate_reasoning, format_reasoning_for_prompt
from app.agent.expert_team.tot import explore_thoughts, format_tot_for_prompt
from app.agent.expert_team.reflexion import generate_reflexion, format_reflexion_for_prompt, store_reflexion_as_memory
from app.agent.expert_team.consistency import execute_with_self_consistency
from app.agent.expert_team.memory import recall_experience
from app.agent.expert_team.lats import run_lats, format_lats_for_prompt
from app.agent.fact_verifier import verify_facts

logger = get_logger(__name__)


async def _get_llm_for_verify(db, provider_id: int, model_name: str, temperature: float):
    """获取 LLM 实例（供 fact_verify 使用）"""
    from app.agent.llm_service import llm_service
    return await llm_service.get_chat_llm(db, provider_id=provider_id, model_name=model_name, temperature=temperature)


# ─── State 定义 ─────────────────────────────────────────

def _merge_dicts(old: list[dict], new: list[dict]) -> list[dict]:
    """Reducer: 合并列表（并行专家写入安全）"""
    return old + new


class ExpertTeamState(TypedDict, total=False):
    """专家团图状态"""

    # ── 输入 ──────────────────────────────────────────
    input_text: str
    team_id: int
    run_id: int
    max_rounds: int
    current_round: int
    max_debate_rounds: int   # 最大辩论轮次（默认 1，可配置）
    current_debate_round: int  # 当前辩论轮次
    db: Any  # AsyncSession（运行时注入，不参与 checkpoint）

    # ── PM 输出 ──────────────────────────────────────
    pm_plan: str               # PM 的分配计划 JSON 原文
    assignments: list[dict]    # [{expert_id, expert_name, expert_role, subtask, avatar}]

    # ── 专家结果（Reducer: 并行追加）──────────────────
    expert_results: Annotated[list[dict], _merge_dicts]
    # [{expert_id, expert_name, expert_role, output, tokens, status, duration_ms}]

    # ── PM 评估 ──────────────────────────────────────
    pm_evaluation: dict        # {overall_pass, scores, reason, feedback_map}

    # ── 最终输出 ─────────────────────────────────────
    final_report: str

    # ── 元数据 ───────────────────────────────────────
    total_tokens: int
    discussion: list[dict]
    max_execution_time: int

    # ── 专家配置（传入用）────────────────────────────
    experts_data: list[dict]   # 专家列表
    leader_data: dict          # PM 配置
    pm_provider_id: int
    pm_model_name: str
    pm_temperature: float

    # ── 反馈（返工用）────────────────────────────────
    feedback_map: dict         # {expert_id: feedback} 传给下一轮 pm_analyze


# ─── 辅助函数 ──────────────────────────────────────────

def _parse_assignments(pm_output: str, experts_data: list[dict]) -> list[dict]:
    """解析 PM 输出的分配计划 JSON"""
    try:
        data = json.loads(pm_output)
    except (json.JSONDecodeError, TypeError):
        # 尝试从 markdown code block 提取
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', pm_output, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                match = None
        if not match:
            match = re.search(r'\{[^{}]*"assignments"[^{}]*\[.*?\][^{}]*\}', pm_output, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    logger.warning("PM 输出无法解析，fallback 为全员分配")
                    return [
                        {"expert_id": e["id"], "subtask": f"分析: {pm_output[:200]}"}
                        for e in experts_data
                    ]
            else:
                logger.warning("PM 输出无法解析，fallback 为全员分配")
                return [
                    {"expert_id": e["id"], "subtask": f"分析: {pm_output[:200]}"}
                    for e in experts_data
                ]

    assignments = data.get("assignments", [])
    if not assignments:
        return [
            {"expert_id": e["id"], "subtask": f"分析: {pm_output[:200]}"}
            for e in experts_data
        ]
    return assignments


def _parse_evaluation(eval_output: str) -> dict:
    """解析 PM 评估 JSON"""
    try:
        data = json.loads(eval_output.strip())
        return {
            "overall_pass": data.get("overall_pass", False),
            "scores": data.get("scores", []),
            "reason": data.get("reason", ""),
            "feedback_map": {
                s["expert_id"]: s.get("feedback", "")
                for s in data.get("scores", [])
                if s.get("expert_id") and s.get("feedback")
            },
        }
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass

    match = re.search(r'\{[\s\S]*"overall_pass"[\s\S]*\}', eval_output)
    if match:
        try:
            data = json.loads(match.group())
            return {
                "overall_pass": data.get("overall_pass", False),
                "scores": data.get("scores", []),
                "reason": data.get("reason", ""),
                "feedback_map": {
                    s["expert_id"]: s.get("feedback", "")
                    for s in data.get("scores", [])
                    if s.get("expert_id") and s.get("feedback")
                },
            }
        except json.JSONDecodeError:
            pass

    lower = eval_output.lower()
    passed = '"overall_pass": true' in lower or '达标' in eval_output
    return {"overall_pass": passed, "scores": [], "reason": eval_output[:200], "feedback_map": {}}


def _enrich_assignment(assign: dict, experts_data: list[dict]) -> dict:
    """为 assignment 补充专家元信息"""
    expert = next((e for e in experts_data if e["id"] == assign.get("expert_id")), None)
    if not expert:
        return assign
    return {
        **assign,
        "expert_name": expert.get("member_name", ""),
        "expert_role": expert.get("member_role", ""),
        "avatar": expert.get("avatar", "🤖"),
    }


# ─── 图节点 ────────────────────────────────────────────

async def pm_analyze(state: ExpertTeamState) -> dict:
    """PM 分析任务，输出分配计划"""
    from app.services.expert_team_service import _call_llm, _ws_broadcast

    from langgraph.config import get_stream_writer
    writer = get_stream_writer()
    team_id = state["team_id"]
    leader = state["leader_data"]
    current_round = state.get("current_round", 1)
    feedback_map = state.get("feedback_map", {})

    await _ws_broadcast(team_id, "expert_status", {
        "expertName": leader.get("member_name", "PM"),
        "expertRole": "PM/组长",
        "status": "running",
        "round": current_round,
        "runId": state.get("run_id"),
    })

    # 构建专家列表文本（对标 CrewAI role+goal+backstory 三要素）
    experts_data = state["experts_data"]
    expert_list_str = "\n".join([
        f"- ID={e['id']} {e['member_name']}({e['member_role']})"
        + (f" — 目标: {e['goal']}" if e.get('goal') else "")
        + (f" — 背景: {e['backstory']}" if e.get('backstory') else "")
        + (f" — 可委派" if e.get('is_delegation_allowed') else "")
        for e in experts_data
    ])

    # ── P0: PM 角色升级（对标 MetaGPT PM + CrewAI Hierarchical）──
    pm_system = leader.get("system_prompt") or (
        "你是一位资深项目经理（PM），擅长任务拆解、资源调度和质量把控。\n"
        "你的核心能力：\n"
        "1. 快速理解用户需求的本质\n"
        "2. 将复杂任务拆解为可执行的子任务\n"
        "3. 根据团队成员的专业能力精准分配\n"
        "4. 设定明确的质量标准和验收条件"
    )
    orchestrator_prompt = leader.get("orchestrator_prompt") or (
        "## 任务分析框架\n"
        "1. **核心问题**：用户真正想要解决什么问题？\n"
        "2. **关键维度**：需要哪些专业视角来全面分析？\n"
        "3. **依赖关系**：子任务之间是否有先后依赖？\n"
        "4. **质量标准**：什么样的结果算「达标」？\n\n"
        "## 分配原则\n"
        "- 每个子任务必须有明确的交付物描述\n"
        "- 优先分配给最匹配的专家（按专长匹配）\n"
        "- 可并行的任务分配给不同专家同时执行\n"
        "- 子任务数量控制在 2-10 个，避免过度拆解\n\n"
        "## 输出要求\n"
        "严格按 JSON 格式输出分配计划。\n"
        "- 通知专家开始执行任务"
    )

    # 返工反馈注入
    feedback_section = ""
    if feedback_map and current_round > 1:
        feedback_lines = [f"- 专家 ID={eid}: {fb}" for eid, fb in feedback_map.items()]
        feedback_section = f"\n\n## 上一轮 PM 反馈（请务必参考改进）\n" + "\n".join(feedback_lines)

    analyze_prompt = f"""{pm_system}

## 团队成员
{expert_list_str}

## 工作指令
{orchestrator_prompt}

## 用户任务
{state['input_text']}{feedback_section}

请分析任务并输出分配计划（JSON 格式）。"""

    content, tokens = await _call_llm(
        state.get("db"),
        state["pm_provider_id"],
        state["pm_model_name"],
        analyze_prompt,
        temperature=state.get("pm_temperature", 0.3),
    )

    content = _content_blocks_to_str(content)
    assignments = _parse_assignments(content, experts_data)
    enriched = [_enrich_assignment(a, experts_data) for a in assignments]

    # 推送 PM 计划事件
    writer({"type": "pm_plan", "round": current_round, "content": content})

    await _ws_broadcast(team_id, "expert_thinking", {
        "expertName": leader.get("member_name", "PM"),
        "expertRole": "PM/组长",
        "round": current_round,
        "content": content,
        "runId": state.get("run_id"),
    })
    await _ws_broadcast(team_id, "expert_status", {
        "expertName": leader.get("member_name", "PM"),
        "expertRole": "PM/组长",
        "status": "done",
        "round": current_round,
        "runId": state.get("run_id"),
    })

    return {
        "pm_plan": content,
        "assignments": enriched,
        "total_tokens": tokens,
        "discussion": [{
            "round": current_round,
            "expertName": leader.get("member_name", "PM"),
            "expertRole": "PM/组长",
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }],
    }


async def expert_execute(state: ExpertTeamState) -> dict:
    """单个专家执行子任务 — 由 Send API 并发派发

    state 是 Send payload = assignment + 上下文字段。
    """
    import asyncio
    from app.services.expert_team_service import _call_llm, _ws_broadcast

    from langgraph.config import get_stream_writer
    writer = get_stream_writer()
    team_id = state["team_id"]
    expert_id = state["expert_id"]
    expert_name = state.get("expert_name", f"Expert-{expert_id}")
    expert_role = state.get("expert_role", "")
    avatar = state.get("avatar", "🤖")
    subtask = state.get("subtask", "")
    current_round = state.get("current_round", 1)

    # 查找专家配置
    expert_conf = next((e for e in state["experts_data"] if e["id"] == expert_id), None)
    if not expert_conf:
        return {"expert_results": [{
            "expert_id": expert_id, "expert_name": expert_name,
            "expert_role": expert_role, "output": f"[专家配置不存在: ID={expert_id}]",
            "tokens": 0, "status": "failed", "duration_ms": 0,
        }]}

    # 推送开始事件
    writer({"type": "expert_start", "expertId": expert_id, "expertName": expert_name, "expertRole": expert_role, "avatar": avatar, "subtask": subtask, "round": current_round})
    await _ws_broadcast(team_id, "expert_status", {
        "expertName": expert_name, "expertRole": expert_role,
        "avatar": avatar, "status": "running", "round": current_round,
        "runId": state.get("run_id"),
    })

    # 构建上下文（之前轮次的讨论）
    context_text = ""
    discussion = state.get("discussion", [])
    if discussion:
        ctx_parts = []
        for msg in discussion:
            if msg.get("round", 0) < current_round:
                ctx_parts.append(f"### {msg['expertName']}({msg['expertRole']}) 第{msg['round']}轮\n{msg['content']}")
        if ctx_parts:
            context_text = "\n\n".join(ctx_parts)

    # 返工反馈
    feedback_text = (state.get("feedback_map") or {}).get(expert_id, "")
    feedback_section = f"\n\n## PM 改进建议（请务必参考）\n{feedback_text}" if feedback_text else ""
    context_section = f"\n\n## 之前讨论\n{context_text}" if context_text else ""

    # ── P0: 专家角色升级（对标 CrewAI role+goal+backstory + ReAct CoT）──
    expert_system = expert_conf.get("system_prompt") or (
        f"你是{expert_name}，角色是{expert_role}。\n"
        f"{expert_conf.get('goal', '') or ''}\n"
        f"{expert_conf.get('backstory', '') or ''}"
    ).strip()

    # ── Reflexion 经验召回: 从 Memory 中检索该专家的历史反思 ──
    reflexion_recall = ""
    try:
        past_experience = await recall_experience(
            expert_id=expert_id, subtask=subtask, top_k=3,
        )
        if past_experience:
            reflexion_recall = past_experience
            writer({"type": "expert_recall", "expertId": expert_id,
                    "expertName": expert_name, "has_experience": True})
    except Exception as e:
        logger.debug(f"经验召回失败（跳过）: {e}")

    # Verbose 控制（对标 CrewAI verbose 参数）
    is_verbose = expert_conf.get("verbose", False)
    detail_instruction = (
        "请详细展示你的推理过程和中间步骤。"
        if is_verbose else
        "直接给出分析结论，省略中间推理过程。"
    )

    # ── P0: 执行前反思 + ToT 多路径探索 ──
    expert_goal = expert_conf.get("goal", "")
    skills_desc = ""
    try:
        skills_desc = ", ".join(
            s.get("name", "") for s in (expert_conf.get("skills") or expert_conf.get("tools_json") or [])
        )
    except Exception:
        pass

    # 1. Reasoning: 执行前反思（挑战/策略/工具/风险/关键点）
    reasoning_obj = await generate_reasoning(
        db=state.get("db"), provider_id=expert_conf.get("provider_id") or state["pm_provider_id"],
        model_name=expert_conf.get("model_name") or state["pm_model_name"],
        expert_name=expert_name, expert_role=expert_role, expert_goal=expert_goal,
        subtask=subtask, skills_desc=skills_desc, context=context_text,
        temperature=float(expert_conf.get("temperature") or 0.3),
    )
    reasoning_text = format_reasoning_for_prompt(reasoning_obj)
    if reasoning_text:
        writer({"type": "expert_reasoning", "expertId": expert_id, "expertName": expert_name,
                "challenges": reasoning_obj.challenges if reasoning_obj else [],
                "strategy": reasoning_obj.strategy if reasoning_obj else ""})

    # 2. ToT: 多路径探索（3 条思路 → 评估 → 选最优）
    tot_obj = await explore_thoughts(
        db=state.get("db"), provider_id=expert_conf.get("provider_id") or state["pm_provider_id"],
        model_name=expert_conf.get("model_name") or state["pm_model_name"],
        expert_name=expert_name, expert_role=expert_role,
        subtask=subtask, context=context_text, n_branches=3,
        temperature=float(expert_conf.get("temperature") or 0.7),
    )
    tot_text = format_tot_for_prompt(tot_obj)
    if tot_text:
        writer({"type": "expert_tot", "expertId": expert_id, "expertName": expert_name,
                "branches": len(tot_obj.branches) if tot_obj else 0,
                "best_approach": tot_obj.branches[tot_obj.best_index].approach if tot_obj and tot_obj.branches else ""})

    # 3. LATS: 蒙特卡洛树搜索（仅复杂任务，由配置启用）
    lats_text = ""
    use_lats = expert_conf.get("use_lats", False)
    if use_lats:
        try:
            _expert_temp = float(expert_conf.get("temperature") or 0.7)
            lats_llm = await _get_llm_for_verify(state.get("db"), expert_provider_id, expert_model_name, _expert_temp)
            lats_result = await run_lats(
                llm=lats_llm, problem=subtask, context=context_text,
                max_iterations=5, max_children=3, temperature=_expert_temp,
            )
            lats_text = format_lats_for_prompt(lats_result)
            if lats_text:
                writer({"type": "expert_lats", "expertId": expert_id,
                        "expertName": expert_name, "nodes": lats_result.total_nodes if lats_result else 0})
        except Exception as e:
            logger.debug(f"LATS 失败（降级为 ToT）: {e}")

    # 可委派的队友列表
    is_delegation_allowed = expert_conf.get("is_delegation_allowed", 0)
    delegate_section = ""
    if is_delegation_allowed:
        teammates = [
            f"- ID={e['id']} {e['member_name']}({e['member_role']}): {e.get('goal', '')}"
            for e in state["experts_data"]
            if e["id"] != expert_id
        ]
        if teammates:
            delegate_section = (
                "\n\n## 可委派的队友\n"
                + "\n".join(teammates)
                + "\n\n如果你认为某个子任务更适合其他专家处理，"
                "请在回答末尾用以下格式标注委派请求：\n"
                "`[DELEGATE] expert_id=<ID> subtask=<任务描述>`"
            )

    expert_prompt = f"""{expert_system}
{reasoning_text}{tot_text}{lats_text}{reflexion_recall}

## 你的任务
{subtask}

## 原始用户问题
{state['input_text']}{context_section}{feedback_section}

## 思考框架
请按以下步骤完成任务：

1. **背景分析**：这个问题的背景和上下文是什么？
2. **关键要素**：从你的专业角度，需要关注哪些关键点？
3. **深度分析**：基于你的专业知识，给出详细分析
4. **结论建议**：给出明确的结论和可操作的建议
4. **实施方案**：按可操作方案严格执行任务

## 输出要求
- 结构清晰，使用标题和要点列表
- 给出具体数据/案例支撑，避免空泛
- 结论明确，建议可操作
- {detail_instruction}{delegate_section}"""

    expert_provider_id = expert_conf.get("provider_id") or state["pm_provider_id"]
    expert_model_name = expert_conf.get("model_name") or state["pm_model_name"]
    expert_temperature = float(expert_conf.get("temperature") or 0.7)
    max_execution_time = int(expert_conf.get("max_execution_time") or state.get("max_execution_time", 120))

    exp_start = datetime.now()
    try:
        # ── Self-Consistency: 多路径投票（NeurIPS 2023, GSM8K +17.9%）──
        n_paths = int(expert_conf.get("consistency_paths", 1) or 1)
        if n_paths > 1:
            content, consistency_tokens, all_paths = await execute_with_self_consistency(
                db=state.get("db"), provider_id=expert_provider_id,
                model_name=expert_model_name, prompt=expert_prompt,
                n_paths=n_paths, base_temperature=0.3, temperature_step=0.2,
                timeout_seconds=max_execution_time,
            )
            tokens = consistency_tokens
            writer({"type": "expert_consistency", "expertId": expert_id,
                    "expertName": expert_name, "paths": n_paths,
                    "selected": f"best_of_{len(all_paths)}"})
        else:
            content, tokens = await asyncio.wait_for(
                _call_llm(state.get("db"), expert_provider_id, expert_model_name, expert_prompt, temperature=expert_temperature),
                timeout=max_execution_time,
            )
            content = _content_blocks_to_str(content)
        duration_ms = int((datetime.now() - exp_start).total_seconds() * 1000)

        # ── Self-Correct: 自评修正（评分不足时自动修正一次）──
        if content and len(content.strip()) < 100:
            try:
                correct_prompt = f"""你的输出过短（{len(content.strip())}字），请重新执行任务。

## 任务
{subtask}

## 原始用户问题
{state['input_text']}

请给出详细、完整的分析（至少200字）。"""
                corrected_content, correct_tokens = await asyncio.wait_for(
                    _call_llm(state.get("db"), expert_provider_id, expert_model_name, correct_prompt, temperature=expert_temperature),
                    timeout=max_execution_time,
                )
                corrected_content = _content_blocks_to_str(corrected_content)
                if corrected_content and len(corrected_content.strip()) > len(content.strip()):
                    content = corrected_content
                    tokens += correct_tokens
                    writer({"type": "expert_self_correct", "expertId": expert_id,
                            "expertName": expert_name, "reason": "output_too_short"})
            except Exception as e:
                logger.debug(f"Self-Correct 失败（保留原输出）: {e}")

        # ── Delegation 解析（对标 CrewAI allow_delegation）──
        delegation_results = []
        if is_delegation_allowed:
            import re as _re
            delegate_matches = _re.findall(r'\[DELEGATE]\s*expert_id=(\d+)\s*subtask=(.+?)(?:\n|$)', content)
            for match in delegate_matches:
                target_id = int(match[0])
                delegate_subtask = match[1].strip()
                target_expert = next((e for e in state["experts_data"] if e["id"] == target_id), None)
                if target_expert:
                    try:
                        delegate_prompt = f"你是{target_expert['member_name']}，角色是{target_expert['member_role']}。\n{target_expert.get('goal', '') or ''}\n{target_expert.get('backstory', '') or ''}\n\n## 委派任务（来自 {expert_name}）\n{delegate_subtask}\n\n请简洁完成此任务。"
                        delegate_content, delegate_tokens = await _call_llm(
                            state.get("db"), target_expert.get("provider_id") or expert_provider_id,
                            target_expert.get("model_name") or expert_model_name,
                            delegate_prompt, temperature=float(target_expert.get("temperature") or 0.7),
                        )
                        delegate_content = _content_blocks_to_str(delegate_content)
                        delegation_results.append(f"\n\n[委派结果 - {target_expert['member_name']}({target_expert['member_role']})]:\n{delegate_content}")
                        tokens += delegate_tokens
                        writer({"type": "delegation", "from": expert_name, "to": target_expert['member_name'], "subtask": delegate_subtask})
                    except Exception as e:
                        logger.warning(f"委派给 {target_expert['member_name']} 失败: {e}")
                        delegation_results.append(f"\n\n[委派失败 - {target_expert['member_name']}]: {e}")

            # 从输出中移除 DELEGATE 标记
            if delegate_matches:
                content = _re.sub(r'\[DELEGATE]\s*expert_id=\d+\s*subtask=.+?(?:\n|$)', '', content).strip()

        if delegation_results:
            content += "\n".join(delegation_results)

        # ── Reflexion: 事后反思（NeurIPS 2023, HumanEval 67→91%）──
        try:
            reflexion_obj = await generate_reflexion(
                db=state.get("db"), provider_id=expert_provider_id,
                model_name=expert_model_name, expert_name=expert_name,
                expert_role=expert_role, subtask=subtask,
                output=content, duration_ms=duration_ms,
                temperature=float(expert_conf.get("temperature") or 0.3),
            )
            if reflexion_obj:
                reflexion_text = format_reflexion_for_prompt(reflexion_obj)
                # 存入记忆（跨轮次可召回）
                await store_reflexion_as_memory(
                    expert_id=expert_id, team_id=team_id,
                    reflexion=reflexion_obj, db=state.get("db"),
                )
                writer({"type": "expert_reflexion", "expertId": expert_id,
                        "expertName": expert_name, "success": reflexion_obj.success,
                        "insights": reflexion_obj.key_insights[:2]})
        except Exception as e:
            logger.debug(f"Reflexion 生成失败（非致命）: {e}")

        # ── Fact Verify: 原子声明验证（幻觉检测与修正）──
        try:
            fact_result = await verify_facts(
                llm=await _get_llm_for_verify(state.get("db"), expert_provider_id, expert_model_name, 0.2),
                text=content, context=context_text, temperature=0.2,
            )
            if fact_result and fact_result.refuted > 0:
                content = fact_result.corrected_text
                writer({"type": "expert_fact_verify", "expertId": expert_id,
                        "expertName": expert_name,
                        "total": fact_result.total_claims,
                        "refuted": fact_result.refuted,
                        "hallucination_rate": f"{fact_result.hallucination_rate:.1%}"})
        except Exception as e:
            logger.debug(f"Fact Verify 失败（非致命）: {e}")

        # 推送完成事件
        writer({"type": "expert_done", "expertId": expert_id, "expertName": expert_name, "expertRole": expert_role, "avatar": avatar, "content": content, "round": current_round, "durationMs": duration_ms})
        await _ws_broadcast(team_id, "expert_thinking", {
            "expertName": expert_name, "expertRole": expert_role,
            "avatar": avatar, "round": current_round, "content": content,
            "runId": state.get("run_id"), "durationMs": duration_ms,
        })
        await _ws_broadcast(team_id, "expert_status", {
            "expertName": expert_name, "expertRole": expert_role,
            "avatar": avatar, "status": "done", "round": current_round,
            "runId": state.get("run_id"), "durationMs": duration_ms,
        })

        return {
            "expert_results": [{
                "expert_id": expert_id, "expert_name": expert_name,
                "expert_role": expert_role, "output": content,
                "tokens": tokens, "status": "done", "duration_ms": duration_ms,
            }],
            "total_tokens": tokens,
            "discussion": [{
                "round": current_round, "expertName": expert_name,
                "expertRole": expert_role, "content": content,
                "timestamp": datetime.now().isoformat(),
            }],
        }

    except asyncio.TimeoutError:
        duration_ms = int((datetime.now() - exp_start).total_seconds() * 1000)
        timeout_msg = f"[执行超时: 超过 {max_execution_time} 秒]"
        await _ws_broadcast(team_id, "expert_status", {
            "expertName": expert_name, "expertRole": expert_role,
            "avatar": avatar, "status": "failed", "round": current_round,
            "runId": state.get("run_id"), "durationMs": duration_ms,
        })
        return {
            "expert_results": [{
                "expert_id": expert_id, "expert_name": expert_name,
                "expert_role": expert_role, "output": timeout_msg,
                "tokens": 0, "status": "failed", "duration_ms": duration_ms,
            }],
        }

    except Exception as e:
        logger.error(f"专家 {expert_name} 执行失败: {e}")
        duration_ms = int((datetime.now() - exp_start).total_seconds() * 1000)
        await _ws_broadcast(team_id, "expert_status", {
            "expertName": expert_name, "expertRole": expert_role,
            "avatar": avatar, "status": "failed", "round": current_round,
            "runId": state.get("run_id"), "duration_ms": duration_ms,
        })
        return {
            "expert_results": [{
                "expert_id": expert_id, "expert_name": expert_name,
                "expert_role": expert_role, "output": f"[执行失败: {e}]",
                "tokens": 0, "status": "failed", "duration_ms": duration_ms,
            }],
        }


async def pm_evaluate(state: ExpertTeamState) -> dict:
    """PM 评估所有专家结果，决定通过或返工"""
    from app.services.expert_team_service import _call_llm, _ws_broadcast

    from langgraph.config import get_stream_writer
    writer = get_stream_writer()
    team_id = state["team_id"]
    leader = state["leader_data"]
    current_round = state.get("current_round", 1)
    expert_results = state.get("expert_results", [])

    await _ws_broadcast(team_id, "expert_status", {
        "expertName": leader.get("member_name", "PM"),
        "expertRole": "PM/组长",
        "status": "running",
        "round": current_round,
        "runId": state.get("run_id"),
    })

    pm_system = leader.get("system_prompt") or "你是一位资深项目经理（PM），擅长任务拆解和资源调度。"

    results_text = "\n\n".join([
        f"### {r['expert_name']}({r['expert_role']}) — 子任务: {r.get('subtask', '')}\n{r['output']}"
        for r in expert_results
    ])

    # ── P0: PM 评估升级（Rubric 评分 + 结构化反馈，对标 MetaGPT QAEngineer）──
    eval_prompt = f"""{pm_system}

## 用户原始任务
{state['input_text']}

## 专家完成情况（第 {current_round} 轮）
{results_text}

## 评估维度（每项 1-10 分）
1. **完整性**（completeness）：是否覆盖了子任务的所有要求？
2. **准确性**（accuracy）：信息是否准确、有依据、无明显错误？
3. **深度**（depth）：分析是否深入，是否有独到见解？
4. **可用性**（usability）：输出是否可直接使用，建议是否可操作？
5. **风险识别**（risk_awareness）：是否识别了潜在风险和不确定性？

## 评分标准
- 8-10：优秀，超出预期
- 6-7：合格，基本达标
- 4-5：一般，需要改进
- 1-3：不合格，需要返工

## 达标条件
- 所有专家平均分 >= 6 且无单项低于 4 → overall_pass = true
- 否则 → overall_pass = false

你必须严格按照 JSON 格式输出，不要添加其他文字。
输出 JSON 格式：
{{"scores": [{{"expert_id": ID, "score": 分数, "completeness": N, "accuracy": N, "depth": N, "usability": N, "risk_awareness": N, "feedback": "具体改进建议"}}], "overall_pass": true/false, "reason": "总体评价", "avg_score": 平均分}}"""

    content, tokens = await _call_llm(
        state.get("db"),
        state["pm_provider_id"],
        state["pm_model_name"],
        eval_prompt,
        temperature=state.get("pm_temperature", 0.3),
    )

    content = _content_blocks_to_str(content)
    evaluation = _parse_evaluation(content)

    # ── 元评估: 检测评估器偏差（Agent-as-a-Judge）──
    try:
        from app.agent.meta_evaluator import meta_evaluate
        meta_result = await meta_evaluate(
            llm=await _get_llm_for_verify(state.get("db"), state["pm_provider_id"], state["pm_model_name"], 0.2),
            evaluations=[{"score": s.get("score", 5), "passed": s.get("score", 5) >= 6, "reason": s.get("feedback", "")} for s in evaluation.get("scores", [])],
        )
        if meta_result:
            evaluation["meta_eval"] = {
                "bias": meta_result.bias_direction,
                "calibration": meta_result.calibration_score,
                "recommendation": meta_result.recommendation,
            }
            writer({"type": "pm_meta_eval", "round": current_round,
                    "bias": meta_result.bias_direction,
                    "calibration": meta_result.calibration_score})
    except Exception as e:
        logger.debug(f"元评估失败（非致命）: {e}")

    # 推送评估事件
    writer({"type": "pm_eval", "round": current_round, "evaluation": evaluation})

    await _ws_broadcast(team_id, "expert_thinking", {
        "expertName": leader.get("member_name", "PM"),
        "expertRole": "PM/组长",
        "round": current_round, "content": content,
        "runId": state.get("run_id"),
    })
    await _ws_broadcast(team_id, "expert_status", {
        "expertName": leader.get("member_name", "PM"),
        "expertRole": "PM/组长",
        "status": "done", "round": current_round,
        "runId": state.get("run_id"),
    })

    return {
        "pm_evaluation": evaluation,
        "feedback_map": evaluation.get("feedback_map", {}),
        "total_tokens": tokens,
        "discussion": [{
            "round": current_round,
            "expertName": leader.get("member_name", "PM"),
            "expertRole": "PM/组长(评估)",
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }],
    }


async def debate_round(state: ExpertTeamState) -> dict:
    """P1: 辩论轮 — 专家交叉质询，提升分析深度

    对标 AutoGen GroupChat Debate 模式：
      - 每个专家审阅其他专家的结论
      - 提出质疑、补充或反驳
      - 修正自己的观点

    设计原则：
      - 支持多轮辩论（max_debate_rounds 可配置，默认 1 轮）
      - 辩论结果追加到 discussion，供 PM 评估参考
      - 只在首轮执行辩论（返工轮不辩论，直接评估）
    """
    from app.services.expert_team_service import _call_llm, _ws_broadcast
    from langgraph.config import get_stream_writer
    writer = get_stream_writer()

    team_id = state["team_id"]
    expert_results = state.get("expert_results", [])
    current_round = state.get("current_round", 1)
    max_debate_rounds = state.get("max_debate_rounds", 1)
    current_debate_round = state.get("current_debate_round", 0)

    # 只在第 1 轮且有 2+ 专家结果时执行辩论，且未超过最大辩论轮次
    if current_round > 1 or len(expert_results) < 2:
        return {}
    if current_debate_round >= max_debate_rounds:
        return {}

    writer({"type": "debate_start", "round": current_round, "message": "开始交叉质询..."})
    await _ws_broadcast(team_id, "expert_progress", {
        "status": "debating", "round": current_round, "runId": state.get("run_id"),
    })

    # 构建其他专家结论的摘要
    results_summaries = []
    for r in expert_results:
        if r.get("status") == "done" and r.get("output"):
            summary = r["output"][:500]  # 取前 500 字
            results_summaries.append(f"**{r['expert_name']}({r['expert_role']})**: {summary}")

    if len(results_summaries) < 2:
        return {}

    all_summaries = "\n\n".join(results_summaries)

    # 每个专家审阅其他人结论，提出质疑
    debate_results = []
    for r in expert_results:
        if r.get("status") != "done" or not r.get("output"):
            continue

        expert_conf = next((e for e in state["experts_data"] if e["id"] == r["expert_id"]), None)
        expert_system = expert_conf.get("system_prompt") if expert_conf else ""
        if not expert_system:
            expert_system = f"你是{r['expert_name']}，角色是{r['expert_role']}。"

        # 构建其他专家结论（排除自己）
        other_summaries = []
        for s in expert_results:
            if s["expert_id"] != r["expert_id"] and s.get("status") == "done":
                other_summaries.append(f"**{s['expert_name']}({s['expert_role']})**: {s['output'][:300]}")
        others_text = "\n\n".join(other_summaries)

        debate_prompt = f"""{expert_system}

## 你的原始分析
{r['output'][:500]}

## 其他专家的分析
{others_text}

## 交叉质询任务
请从你的专业角度：
1. **认同点**：其他专家哪些观点你是认同的？为什么？
2. **质疑点**：哪些观点你认为有问题或不够全面？具体指出
3. **补充**：基于其他专家的分析，你能补充什么新视角？
4. **修正**：综合所有观点后，你是否需要修正自己的结论？

请简洁回答，每点 2-3 句话即可。"""

        expert_provider_id = (expert_conf.get("provider_id") if expert_conf else None) or state["pm_provider_id"]
        expert_model_name = (expert_conf.get("model_name") if expert_conf else None) or state["pm_model_name"]
        expert_temperature = float((expert_conf.get("temperature") if expert_conf else None) or 0.5)

        try:
            content, tokens = await _call_llm(
                state.get("db"), expert_provider_id, expert_model_name,
                debate_prompt, temperature=expert_temperature,
            )
            content = _content_blocks_to_str(content)
            debate_results.append({
                "round": current_round,
                "expertName": r["expert_name"],
                "expertRole": r["expert_role"],
                "content": f"【交叉质询】\n{content}",
                "timestamp": datetime.now().isoformat(),
                "is_debate": True,
            })
            writer({"type": "debate_done", "expertName": r["expert_name"], "content": content[:200]})
        except Exception as e:
            logger.warning(f"辩论轮 {r['expert_name']} 失败: {e}")

    await _ws_broadcast(team_id, "expert_progress", {
        "status": "debate_done", "round": current_round, "runId": state.get("run_id"),
    })

    return {"discussion": debate_results, "current_debate_round": current_debate_round + 1}


async def pm_report(state: ExpertTeamState) -> dict:
    """PM 汇总最终报告"""
    from app.services.expert_team_service import _call_llm, _ws_broadcast

    from langgraph.config import get_stream_writer
    writer = get_stream_writer()
    team_id = state["team_id"]
    leader = state["leader_data"]

    pm_system = leader.get("system_prompt") or "你是一位资深项目经理（PM），擅长任务拆解和资源调度。"
    # ── P0: 报告生成升级（结构化输出 + 多视角综合 + 风险提示）──
    synthesizer_prompt = leader.get("synthesizer_prompt") or (
        "请综合所有专家的分析结果，生成结构化的最终报告。\n\n"
        "## 报告结构\n"
        "1. **核心结论**（3-5 条关键发现）\n"
        "2. **各专家观点摘要**（每人 2-3 句核心观点）\n"
        "3. **共识与分歧**（哪些观点一致？哪些存在分歧？分歧的原因是什么？）\n"
        "4. **关键建议**（可操作的具体建议，按优先级排序）\n"
        "5. **风险提示**（需要注意的不确定性和风险）\n"
        "6. **执行路线图**（如果需要落地，推荐的步骤和顺序并开始委托对应专家执行）"
    )

    expert_results = state.get("expert_results", [])
    final_results_text = "\n\n".join([
        f"### {r['expert_name']}({r['expert_role']}) — {r.get('subtask', '')}\n{r['output']}"
        for r in expert_results if r.get("status") == "done"
    ])

    report_prompt = f"""{pm_system}

## 用户原始任务
{state['input_text']}

## 专家分析结果（共 {len(expert_results)} 条）
{final_results_text}

## 工作指令
{synthesizer_prompt}

请生成最终报告。"""

    content, tokens = await _call_llm(
        state.get("db"),
        state["pm_provider_id"],
        state["pm_model_name"],
        report_prompt,
        temperature=state.get("pm_temperature", 0.3),
    )

    content = _content_blocks_to_str(content)

    writer({"type": "pm_report", "content": content})

    await _ws_broadcast(team_id, "expert_status", {
        "expertName": leader.get("member_name", "PM"),
        "expertRole": "PM/组长",
        "status": "done", "round": -1,
        "runId": state.get("run_id"),
    })
    await _ws_broadcast(team_id, "expert_progress", {
        "status": "completed", "runId": state.get("run_id"),
        "output": content[:500],
    })

    return {
        "final_report": content,
        "total_tokens": tokens,
        "discussion": [{
            "round": -1,
            "expertName": leader.get("member_name", "PM"),
            "expertRole": "PM/组长(报告)",
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }],
    }


# ─── 路由函数 ──────────────────────────────────────────

def fan_out_experts(state: ExpertTeamState) -> list[Send]:
    """pm_analyze → expert_execute: 动态 fan-out（Send API）

    Send payload = assignment + 上下文字段（team_id, run_id, db 等）。
    LangGraph Send 将 payload 作为 state 传入目标节点。
    """
    assignments = state.get("assignments", [])
    if not assignments:
        # 无分配 → 直接跳到 pm_evaluate（passthrough 保留完整 state）
        return [Send("passthrough_evaluate", state)]
    # 提取上下文字段，合并到每个 assignment
    ctx = {
        "team_id": state["team_id"],
        "run_id": state["run_id"],
        "max_rounds": state["max_rounds"],
        "current_round": state.get("current_round", 1),
        "max_debate_rounds": state.get("max_debate_rounds", 1),
        "current_debate_round": state.get("current_debate_round", 0),
        "db": state["db"],
        "experts_data": state["experts_data"],
        "leader_data": state["leader_data"],
        "pm_provider_id": state["pm_provider_id"],
        "pm_model_name": state["pm_model_name"],
        "pm_temperature": state.get("pm_temperature", 0.3),
        "discussion": state.get("discussion", []),
        "feedback_map": state.get("feedback_map", {}),
        "input_text": state["input_text"],
        "total_tokens": state.get("total_tokens", 0),
    }
    return [
        Send("expert_execute", {**ctx, **assignment})
        for assignment in assignments
    ]


def route_after_evaluate(state: ExpertTeamState) -> str:
    """pm_evaluate → pass: pm_report / fail: pm_analyze（Loop）"""
    evaluation = state.get("pm_evaluation", {})
    current_round = state.get("current_round", 1)
    max_rounds = state.get("max_rounds", 3)

    if evaluation.get("overall_pass", False):
        return "pm_report"

    if current_round >= max_rounds:
        logger.warning(f"达到最大轮次 {max_rounds}，强制生成报告")
        return "pm_report"

    return "pm_analyze"


def increment_round(state: ExpertTeamState) -> dict:
    """返工时 current_round + 1"""
    return {"current_round": state.get("current_round", 1) + 1}


def passthrough_evaluate(state: ExpertTeamState) -> dict:
    """无分配时的透传节点 — 保留完整 state，直接流向 pm_evaluate"""
    return {}


# ─── 图构建 ────────────────────────────────────────────

def build_expert_team_graph(enable_interrupt: bool = False) -> CompiledGraph:
    """构建专家团 LangGraph 图

    Args:
        enable_interrupt: 是否启用 interrupt（human-in-the-loop）

    Returns:
        编译后的 CompiledGraph
    """
    from langgraph.checkpoint.memory import MemorySaver

    graph = StateGraph(ExpertTeamState)

    # 注册节点
    graph.add_node("pm_analyze", pm_analyze)
    graph.add_node("expert_execute", expert_execute)
    graph.add_node("passthrough_evaluate", passthrough_evaluate)
    graph.add_node("debate_round", debate_round)  # P1: 辩论轮
    graph.add_node("pm_evaluate", pm_evaluate)
    graph.add_node("pm_report", pm_report)
    graph.add_node("increment_round", increment_round)

    # 边：START → pm_analyze
    graph.add_edge(START, "pm_analyze")

    # 条件边：pm_analyze → [Send("expert_execute", ...)] (动态 fan-out)
    graph.add_conditional_edges("pm_analyze", fan_out_experts, ["expert_execute", "passthrough_evaluate"])

    # 边：expert_execute → debate_round（所有专家完成后，先辩论再评估）
    graph.add_edge("expert_execute", "debate_round")
    # 边：passthrough_evaluate → pm_evaluate（无分配时透传，跳过辩论）
    graph.add_edge("passthrough_evaluate", "pm_evaluate")
    # 边：debate_round → pm_evaluate（辩论后评估）
    graph.add_edge("debate_round", "pm_evaluate")

    # 条件边：pm_evaluate → pm_report (pass) / increment_round → pm_analyze (fail)
    graph.add_conditional_edges("pm_evaluate", route_after_evaluate, {
        "pm_report": "pm_report",
        "pm_analyze": "increment_round",
    })

    # 边：increment_round → pm_analyze
    graph.add_edge("increment_round", "pm_analyze")

    # 边：pm_report → END
    graph.add_edge("pm_report", END)

    # 编译
    checkpointer = MemorySaver() if enable_interrupt else None
    compile_kwargs = {}
    if checkpointer:
        compile_kwargs["checkpointer"] = checkpointer

    return graph.compile(**compile_kwargs)
