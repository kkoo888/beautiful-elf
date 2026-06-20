"""Goal 模式节点工厂 — evaluator、status_updater、replanner"""
from typing import Dict, Any
import time
import json
import re

from langchain_core.messages import HumanMessage, AIMessage

from app.core.logging import get_logger
from app.agent.state import AgentState, _content_blocks_to_str
from app.agent.utils.common import _content_to_str
from app.agent.utils.goal_helpers import (
    LoopDetector, _get_loop_detector, _get_next_pending_subtask, _get_parallel_ready_tasks,
    _update_subtask_status, _build_goal_progress_text,
    _guardrail_check_subtask, _parse_goal_subtasks, _validate_dependencies,
)

logger = get_logger(__name__)


def _make_goal_evaluator(llm):
    """Goal 模式评估器 — 判断目标是否达成"""

    async def goal_evaluator(state: dict) -> dict:
        """评估当前结果是否达成目标"""
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()
        from app.core.logging import get_logger as _get_logger
        _logger = _get_logger(__name__)

        goal = state.get("goal_definition", "")
        final_answer = state.get("final_answer", "")
        iterations = state.get("goal_iterations", 0)
        max_iterations = state.get("goal_max_iterations", 5)
        tokens_used = state.get("goal_tokens_used", 0)
        token_budget = state.get("goal_token_budget", 50000)

        # Token 预算检查
        if tokens_used >= token_budget:
            writer({"step": "goal_eval", "status": "done", "message": "已达 Token 预算上限"})
            return {"goal_status": "budget_exceeded"}

        # 最大迭代检查
        if iterations >= max_iterations:
            writer({"step": "goal_eval", "status": "done", "message": "已达最大迭代次数"})
            return {"goal_status": "failed"}

        # 如果没有 final_answer，说明还没执行过
        if not final_answer:
            return {"goal_status": "in_progress", "goal_iterations": iterations + 1}

        # LLM 评估是否达成目标
        eval_prompt = f"""你是一个目标评估器。判断以下回答是否达成了用户的目标。

用户目标：{goal}

当前回答：{final_answer[:2000]}

评估说明：
1. 优先评估回答内容是否实质上回答了用户的问题
2. 如果回答中包含"基于已有知识"、"工具不可用时的降级回答"等说明，且内容合理准确，应视为有效回答
3. 工具调用失败时的降级回答（基于大模型知识）是可接受的
4. 只有当回答完全无关、空白或明显错误时才判定为未达成

请严格按 JSON 格式输出：
{{"achieved": true/false, "reason": "原因", "suggestion": "如果未达成，下一步建议"}}

只输出 JSON，不要其他文字。"""

        try:
            response = await llm.ainvoke(eval_prompt)
            content = _content_blocks_to_str(response.content if hasattr(response, 'content') else response)
            import re
            match = re.search(r'\{.*?\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                achieved = data.get("achieved", False)

                if achieved:
                    writer({"step": "goal_eval", "status": "done", "message": "目标已达成！"})
                    # Self-Healing: 标记反思成功
                    try:
                        from app.agent.self_healing import get_healing_memory
                        healing_memory = get_healing_memory()
                        for st in (state.get("goal_subtasks") or []):
                            if st.get("status") == "done":
                                await healing_memory.mark_successful(
                                    user_id=state.get("user_id", 0), subtask_id=st.get("id", 0))
                    except Exception:
                        pass
                    return {"goal_status": "achieved"}
                else:
                    history = list(state.get("goal_history", []))
                    history.append({
                        "iteration": iterations,
                        "result": final_answer[:500],
                        "evaluation": data.get("reason", ""),
                        "suggestion": data.get("suggestion", ""),
                    })
                    writer({"step": "goal_eval", "status": "done",
                            "message": f"目标未达成 (第{iterations+1}轮): {data.get('reason', '')[:50]}"})
                    return {
                        "goal_status": "in_progress",
                        "goal_iterations": iterations + 1,
                        "goal_history": history,
                        "goal_current_plan": data.get("suggestion", ""),
                    }
        except Exception as e:
            _logger.warning(f"[goal_evaluator] 评估失败: {e}")

        return {"goal_status": "in_progress", "goal_iterations": iterations + 1}

    return goal_evaluator

def _make_goal_status_updater(llm=None):
    """Goal 模式子任务状态更新器"""

    async def goal_status_updater_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer, get_config
        writer = get_stream_writer()

        iterations = state.get("goal_iterations", 0)

        # P1 fix: 使用 LangGraph 官方 thread_id 做状态隔离
        config = get_config()
        thread_id = config.get("configurable", {}).get("thread_id", str(state.get("conversation_id", "default")))
        loop_detector = _get_loop_detector(thread_id)

        if iterations == 0:
            loop_detector.reset()

        goal_subtasks = list(state.get("goal_subtasks") or [])
        if not goal_subtasks:
            return {}

        # ── P2 fix: iteration 0 = 规划阶段，跳过 guardrail，直接激活首个子任务 ──
        if iterations == 0:
            # P3 fix: 规划后校验依赖关系
            dep_issues = _validate_dependencies(goal_subtasks)
            if dep_issues:
                for issue in dep_issues:
                    logger.warning(f"[goal_status_updater] 依赖校验: {issue}")
                writer({"step": "goal_dep_warning", "status": "warning",
                        "message": f"依赖关系存在问题: {'; '.join(dep_issues[:3])}"})

            parallel_tasks = _get_parallel_ready_tasks(goal_subtasks)
            if parallel_tasks:
                for task in parallel_tasks:
                    goal_subtasks = _update_subtask_status(goal_subtasks, task["id"], "in_progress", 0)
                    writer({"step": "goal_task_start", "status": "executing",
                            "message": f"规划完成，开始执行: {task['title']}",
                            "taskId": task["id"], "taskTitle": task["title"]})
            writer({"step": "goal_subtasks", "status": "done",
                    "message": "规划阶段完成，子任务已激活", "subtasks": goal_subtasks})
            return {"goal_subtasks": goal_subtasks}

        final_answer = state.get("final_answer", "")
        answer_text = _content_to_str(final_answer) if final_answer else ""

        # ── Working Memory 累积器 ──
        goal_working_memory = list(state.get("goal_working_memory") or [])
        new_wm_entries = []

        # 找到当前执行的子任务（每次只处理一个，避免共享 answer 误判）
        in_progress_tasks = [st for st in goal_subtasks if st.get("status") == "in_progress"]
        current_subtask = None
        if in_progress_tasks:
            current_subtask = in_progress_tasks[0]
        else:
            # 没有 in_progress 的，找第一个依赖满足的 pending 任务
            done_ids = {t["id"] for t in goal_subtasks if t.get("status") == "done"}
            for st in goal_subtasks:
                if st.get("status") == "pending":
                    deps = st.get("dependencies", [])
                    if all(d in done_ids for d in deps):
                        current_subtask = st
                        break

        # ── Evaluator 反馈 + Guardrail 双层校验 ──
        if current_subtask:
            task_id = current_subtask["id"]
            evaluation = state.get("evaluation", {})
            eval_passed = evaluation.get("passed", True)
            eval_score = evaluation.get("score", 7)
            eval_reason = evaluation.get("reason", "")
            task_retry_count = current_subtask.get("retry_count", 0)

            # 层 1: Evaluator 质量检查（LLM-as-Judge）
            if not eval_passed and eval_score < 6 and task_retry_count < 2:
                # 质量不合格但可重试 → 不标记 failed，留待下轮重试
                writer({"step": "goal_task_retry", "status": "retrying",
                        "message": f"子任务「{current_subtask['title']}」质量不合格 ({eval_score}/10)，第 {task_retry_count + 1} 次重试",
                        "taskId": task_id, "reason": eval_reason, "retry": task_retry_count + 1})
                # 更新 retry_count，保持 in_progress 状态
                for i, t in enumerate(goal_subtasks):
                    if t.get("id") == task_id:
                        goal_subtasks[i]["retry_count"] = task_retry_count + 1
                        goal_subtasks[i]["last_eval_feedback"] = eval_reason
                        break
                logger.info(f"[goal_status_updater] 子任务 #{task_id} 质量不合格，重试 {task_retry_count + 1}/2")
            else:
                # 层 2: Guardrail 格式校验
                passed, reason = await _guardrail_check_subtask(answer_text, current_subtask["title"], llm=llm)
                if passed and (eval_passed or eval_score >= 6):
                    goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "done", 100)
                    loop_detector.record(task_id, "done")
                    new_wm_entries.append({
                        "task_id": task_id,
                        "title": current_subtask["title"],
                        "result_summary": (answer_text[:200] + "...") if len(answer_text) > 200 else answer_text,
                        "tools_used": list(state.get("current_tools_used", [])),
                        "success": True,
                    })
                    writer({"step": "goal_task_done", "status": "done",
                            "message": f"子任务完成: {current_subtask['title']}",
                            "taskId": task_id, "taskTitle": current_subtask["title"]})
                    logger.info(f"[goal_status_updater] 子任务 #{task_id} → done")
                else:
                    # Guardrail 失败 或 evaluator 失败且重试已耗尽
                    fail_reason = reason if not passed else f"质量不合格: {eval_reason}"
                    goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "failed", 0)
                    try:
                        from app.agent.self_healing import analyze_failure, get_healing_memory
                        reflection = analyze_failure(
                            subtask_title=current_subtask["title"], subtask_id=task_id,
                            failure_source="guardrail", answer_text=answer_text,
                            guardrail_reason=fail_reason,
                            user_id=state.get("user_id", 0),
                            goal_definition=state.get("goal_definition", ""),
                        )
                        await get_healing_memory().store(reflection, goal_id=str(state.get("conversation_id", 0)))
                        loop_detector.record(task_id, "failed")
                    except Exception as e:
                        logger.debug(f"[goal_status_updater] 自愈分析跳过: {e}")
                    writer({"step": "goal_task_failed", "status": "error",
                            "message": f"子任务失败: {current_subtask['title']} ({fail_reason})",
                            "taskId": task_id, "taskTitle": current_subtask["title"]})
                    new_wm_entries.append({
                        "task_id": task_id,
                        "title": current_subtask["title"],
                        "result_summary": f"失败: {fail_reason}",
                        "tools_used": [],
                        "success": False,
                    })

        # 批量标记可并行的子任务
        parallel_tasks = _get_parallel_ready_tasks(goal_subtasks)
        if parallel_tasks:
            for task in parallel_tasks:
                goal_subtasks = _update_subtask_status(goal_subtasks, task["id"], "in_progress", 0)
                writer({"step": "goal_task_start", "status": "executing",
                        "message": f"开始执行: {task['title']}",
                        "taskId": task["id"], "taskTitle": task["title"]})

        writer({"step": "goal_subtasks", "status": "done",
                "message": "子任务状态更新", "subtasks": goal_subtasks})

        # ── 合并 Working Memory ──
        goal_working_memory.extend(new_wm_entries)

        return {"goal_subtasks": goal_subtasks, "goal_working_memory": goal_working_memory}

    return goal_status_updater_node


def _make_goal_replanner(llm):
    """Goal 模式 Re-planner — 动态重规划 + 自愈反思

    核心能力：
      1. 失败时调用 LLM 重新生成计划（而非简单重试）
      2. 可跳过不可行任务、拆解失败任务为更小子任务
      3. 基于 Working Memory 的执行结果调整策略
      4. 成本预估 + Token 预算控制
    """

    async def goal_replanner_node(state: AgentState) -> dict:
        from langgraph.config import get_stream_writer
        writer = get_stream_writer()

        goal_def = state.get("goal_definition", "")
        goal_subtasks = list(state.get("goal_subtasks") or [])
        iterations = state.get("goal_iterations", 0)
        max_iterations = state.get("goal_max_iterations", 5)
        tokens_used = state.get("goal_tokens_used", 0)
        token_budget = state.get("goal_token_budget", 50000)
        goal_history = list(state.get("goal_history") or [])
        goal_working_memory = list(state.get("goal_working_memory") or [])

        done_count = sum(1 for t in goal_subtasks if t.get("status") == "done")
        failed_count = sum(1 for t in goal_subtasks if t.get("status") == "failed")
        total = len(goal_subtasks)

        # Token 预算 + 成本预估
        avg_tokens = tokens_used / max(done_count, 1) if done_count > 0 else 5000
        remaining_tasks = sum(1 for t in goal_subtasks if t.get("status") == "pending")
        estimated_remaining = int(avg_tokens * remaining_tasks)

        if tokens_used >= token_budget:
            writer({"step": "goal_replan", "status": "done", "message": "已达 Token 预算上限"})
            return {"goal_status": "budget_exceeded"}

        if iterations >= max_iterations:
            writer({"step": "goal_replan", "status": "done", "message": f"已达最大迭代次数 ({max_iterations})"})
            return {"goal_status": "failed"}

        # 全部完成
        if done_count == total and total > 0:
            writer({"step": "goal_replan", "status": "done", "message": f"所有子任务已完成 ({done_count}/{total})"})
            return {"goal_status": "achieved"}

        failed_tasks = [t for t in goal_subtasks if t.get("status") == "failed"]

        # ── 有失败任务 → 动态重规划（核心进化）──
        if failed_tasks and llm:
            try:
                # 1. 生成自愈反思
                from app.agent.self_healing import analyze_failure, get_healing_memory
                healing_memory = get_healing_memory()
                goal_id = str(state.get("conversation_id", 0))
                failure_summaries = []
                for ft in failed_tasks:
                    reflection = analyze_failure(
                        subtask_title=ft.get("title", ""), subtask_id=ft.get("id", 0),
                        failure_source="eval", error_message="子任务执行失败",
                        user_id=state.get("user_id", 0), goal_definition=goal_def,
                    )
                    reflection.retry_count = iterations
                    await healing_memory.store(reflection, goal_id=goal_id)
                    failure_summaries.append(f"- 任务{ft.get('id')}「{ft.get('title', '')}」: {reflection.what_not_to_do}")

                # 2. 调用 LLM 动态重规划
                from app.agent.structured_schemas import GoalReplanResult
                replan_llm = llm.with_structured_output(GoalReplanResult)

                done_tasks_text = "\n".join(
                    f"- 任务{t['id']}「{t['title']}" for t in goal_subtasks if t.get("status") == "done"
                )
                failed_text = "\n".join(failure_summaries)
                wm_text = "\n".join(
                    f"- 任务{w['task_id']}「{w['title']}」: {w['result_summary']}"
                    for w in goal_working_memory
                ) if goal_working_memory else "无"

                replan_prompt = f"""你需要重新规划执行计划。

## 原始目标
{goal_def}

## 已完成的任务
{done_tasks_text or "无"}

## 失败的任务（需要重新规划）
{failed_text}

## 执行经验
{wm_text}

## 要求
1. 分析失败原因
2. 对于失败的任务，可以选择：
   a) 用不同策略重试
   b) 拆解为更小的子任务
   c) 跳过（如果不可行且不影响最终目标）
3. 已完成的任务不要重复
4. 保持依赖关系合理
5. 子任务数量控制在 3-8 个"""

                replan_result = await replan_llm.ainvoke([HumanMessage(content=replan_prompt)])

                # 3. 合并重规划结果
                new_subtasks = []
                # 保留已完成的
                for t in goal_subtasks:
                    if t.get("status") == "done":
                        new_subtasks.append(t)
                # 添加重规划的（新 ID 从已有最大 ID + 1 开始）
                max_id = max((t.get("id", 0) for t in goal_subtasks), default=0)
                done_ids = {t["id"] for t in goal_subtasks if t.get("status") == "done"}
                for i, st in enumerate(replan_result.subtasks, start=1):
                    new_id = max_id + i
                    # P7 fix: 依赖重映射
                    # - 已完成任务的绝对 ID（在 done_ids 中）→ 保持原 ID
                    # - 重规划内部的相对 ID（1..N）→ 加 max_id 偏移
                    new_deps = []
                    for d in st.dependencies:
                        if d in done_ids:
                            # 引用已完成任务，保持原 ID
                            new_deps.append(d)
                        elif 1 <= d <= len(replan_result.subtasks):
                            # 引用重规划内部任务，加偏移
                            new_deps.append(max_id + d)
                        else:
                            # 无法识别的依赖，记录警告并保持原值
                            logger.warning(f"[goal_replanner] 无法识别的依赖: 任务{new_id}依赖{d}")
                            new_deps.append(d)
                    new_subtasks.append({
                        "id": new_id,
                        "title": st.title,
                        "description": st.description,
                        "status": "pending",
                        "progress": 0,
                        "retry_count": 0,
                        "dependencies": new_deps,
                    })

                writer({"step": "goal_replan", "status": "replanned",
                        "message": f"动态重规划: {replan_result.strategy_change[:80]}",
                        "analysis": replan_result.analysis,
                        "new_task_count": len(replan_result.subtasks)})
                logger.info(f"[goal_replanner] 动态重规划: {len(failed_tasks)} 个失败 → {len(replan_result.subtasks)} 个新任务")

                history_entry = {
                    "iteration": iterations,
                    "result": f"{done_count}/{total} done, {failed_count} failed",
                    "evaluation": replan_result.analysis[:200],
                    "suggestion": replan_result.strategy_change[:200],
                    "replanned": True,
                }

                return {
                    "goal_status": "in_progress",
                    "goal_iterations": iterations + 1,
                    "goal_subtasks": new_subtasks,
                    "goal_history": goal_history + [history_entry],
                    "goal_current_plan": replan_result.strategy_change[:500],
                }

            except Exception as e:
                logger.warning(f"[goal_replanner] 动态重规划失败，降级为简单重试: {e}")
                # 降级：重置失败任务为 pending
                for ft in failed_tasks:
                    retry_count = ft.get("retry_count", 0)
                    if retry_count < 2:
                        ft["status"] = "pending"
                        ft["retry_count"] = retry_count + 1
                        ft["progress"] = 0

        # ── 无失败 或 重规划降级 → 简单继续 ──
        pending_tasks = [t for t in goal_subtasks if t.get("status") == "pending"]
        in_progress_tasks = [t for t in goal_subtasks if t.get("status") == "in_progress"]
        if not pending_tasks and not in_progress_tasks and done_count < total:
            return {"goal_status": "failed", "goal_iterations": iterations + 1, "goal_subtasks": goal_subtasks}

        writer({"step": "goal_replan", "status": "done",
                "message": f"继续执行 ({done_count}/{total} 完成, 第{iterations+1}轮)"})
        return {
            "goal_status": "in_progress",
            "goal_iterations": iterations + 1,
            "goal_subtasks": goal_subtasks,
            "goal_history": goal_history + [{
                "iteration": iterations,
                "result": f"{done_count}/{total} done, {failed_count} failed",
                "evaluation": "需要继续执行",
                "suggestion": f"还有 {len(pending_tasks)} 个子任务待执行",
            }],
        }

    return goal_replanner_node



