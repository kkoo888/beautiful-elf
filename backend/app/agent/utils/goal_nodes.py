"""Goal 模式节点工厂 — evaluator、status_updater、replanner"""
from typing import Dict
import asyncio
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


# ── Worker Subgraph 并行执行器 ──────────────────────────────

async def _execute_subtasks_via_workers(
    tasks: list,
    state: AgentState,
    writer=None,
) -> list:
    """为多个子任务 spawn worker subgraph 并行执行

    Args:
        tasks: 待执行的子任务列表 [{id, title, description, ...}]
        state: 当前 AgentState（用于读取 parent context）
        writer: 流式进度回调

    Returns:
        [{task_id, title, result_summary, tools_used, success}]
    """
    from app.agent.tool_registry import tool_registry

    llm = tool_registry._worker_llm
    if not llm:
        logger.warning("[worker_spawner] worker llm 未初始化，降级为串行")
        return []

    # 获取 worker 工具
    worker_tool_names = tool_registry._worker_tool_names or [
        "web_search", "execute_code", "read_file", "query_database", "web_fetch",
    ]
    tools = tool_registry.get_langchain_tools(worker_tool_names)

    # Parent context
    parent_system_prompt = tool_registry._parent_system_prompt
    parent_memory = tool_registry._parent_memory

    system_prompt = (
        "你是一个专注的子任务执行器。根据给定的任务，使用可用工具完成工作。\n\n"
        "## 输出要求（必须遵守）\n"
        "- 只返回最终分析结果，不要返回工具调用过程、Thought、Action、Observation\n"
        "- 用自然语言组织回答，使用 Markdown 格式（标题、列表、表格）\n"
        "- 如果任务要求对比/分析，直接输出对比结论，不要输出「我将搜索...」「正在执行...」\n"
        "- 回答长度不少于 200 字，确保内容完整\n"
    )

    async def _run_one_worker(task: dict) -> dict:
        """执行单个子任务的 worker"""
        task_id = task["id"]
        task_title = task.get("title", "")
        task_desc = task.get("description", task_title)

        try:
            from app.agent.worker_graph import build_worker_graph
            worker = build_worker_graph(
                llm=llm, tools=tools, system_prompt=system_prompt,
                max_iterations=5, depth=1,
            )

            initial_state = {
                "messages": [],
                "task": f"## 任务\n{task_title}\n\n## 描述\n{task_desc}",
                "context": "",
                "iteration": 0,
                "max_iterations": 5,
                "final_answer": None,
                "force_end": False,
                "parent_trace_id": f"goal-worker-{task_id}",
                "parent_system_prompt": parent_system_prompt,
                "parent_memory": parent_memory,
            }

            result = await asyncio.wait_for(
                worker.ainvoke(initial_state),
                timeout=300,
            )

            answer = result.get("final_answer") or ""
            if not answer:
                for msg in reversed(result.get("messages", [])):
                    content = getattr(msg, "content", "") if not isinstance(msg, dict) else msg.get("content", "")
                    if content:
                        answer = content if isinstance(content, str) else str(content)
                        break

            # 收集工具使用
            worker_tools = []
            for msg in result.get("messages", []):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                        if name:
                            worker_tools.append(name)

            if writer:
                writer({"step": "goal_worker", "status": "done",
                        "message": f"Worker 完成: {task_title}",
                        "taskId": task_id, "answerLen": len(answer)})

            return {
                "task_id": task_id,
                "title": task_title,
                "result_summary": (answer[:800] + "...") if len(answer) > 800 else answer,
                "tools_used": worker_tools,
                "success": True,
            }

        except asyncio.TimeoutError:
            logger.warning(f"[worker_spawner] 子任务 #{task_id} 超时")
            return {"task_id": task_id, "title": task_title, "result_summary": "执行超时", "tools_used": [], "success": False}
        except Exception as e:
            logger.error(f"[worker_spawner] 子任务 #{task_id} 失败: {e}")
            return {"task_id": task_id, "title": task_title, "result_summary": f"执行失败: {e}", "tools_used": [], "success": False}

    # 并行执行所有子任务
    if writer:
        writer({"step": "goal_workers", "status": "executing",
                "message": f"并行启动 {len(tasks)} 个 Worker",
                "taskIds": [t["id"] for t in tasks]})

    results = await asyncio.gather(*[_run_one_worker(t) for t in tasks])

    if writer:
        succeeded = sum(1 for r in results if r["success"])
        writer({"step": "goal_workers", "status": "done",
                "message": f"Worker 执行完成: {succeeded}/{len(tasks)} 成功"})

    return list(results)


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

        # Goal 模式：优先用 goal_working_memory 评估（Worker 结果），
        # 而非 final_answer（可能是规划阶段的短文本）
        goal_working_memory = state.get("goal_working_memory") or []
        if goal_working_memory:
            wm_texts = []
            for wm in goal_working_memory:
                summary = wm.get("result_summary", "")
                if summary:
                    wm_texts.append(summary)
            if wm_texts:
                final_answer = "\n\n".join(wm_texts)

        if not final_answer:
            return {"goal_status": "in_progress", "goal_iterations": iterations + 1}

        # 纯代码规则评估（零 LLM 调用）
        score = 7
        reasons = []

        # 规则 1: 长度
        ans_len = len(final_answer.strip())
        if ans_len < 10:
            score = 1; reasons.append("回答过短")
        elif ans_len < 50:
            score -= 2; reasons.append("回答较短")
        elif ans_len > 200:
            score += 1

        # 规则 2: 错误分类（接入 error_classifier，区分暂时性错误 vs 内容错误）
        from app.agent.error_classifier import classify_error, FailoverReason
        error_kws = ["抱歉", "不可用", "服务异常", "暂时无法", "出错"]
        err_count = sum(1 for kw in error_kws if kw in final_answer)

        # 先用 error_classifier 检测是否为暂时性错误（限流/超时/服务过载）
        _classified = classify_error(Exception(final_answer))
        if _classified.reason in (FailoverReason.rate_limit, FailoverReason.timeout, FailoverReason.overloaded):
            # 暂时性错误：不触发重试，等待后自动恢复
            writer({"step": "goal_eval", "status": "paused",
                    "message": f"检测到暂时性错误({_classified.reason.value})，暂停等待恢复"})
            return {
                "goal_status": "blocked",
                "goal_blocked_reason": f"暂时性错误: {_classified.reason.value}，等待恢复后重试",
                "error": final_answer[:200],
            }
        if _classified.reason == FailoverReason.billing:
            # 额度耗尽：直接终止
            writer({"step": "goal_eval", "status": "done", "message": "额度耗尽，终止目标"})
            return {"goal_status": "failed", "error": "额度耗尽"}

        if err_count >= 2: score -= 3; reasons.append("多个错误关键词")
        elif err_count >= 1: score -= 1

        # 规则 3: 结构化
        if any(m in final_answer for m in ["\n-", "\n*", "\n1.", "##", "**"]): score += 1

        # 规则 4: 不确定性标注
        if any(m in final_answer for m in ["可能", "也许", "据我了解", "不确定"]): score += 0.5

        score = max(1, min(10, int(score)))
        reason = "、".join(reasons) if reasons else "质量合格"

        # 检查子任务完成情况 — 所有子任务都 done 才算 achieved
        goal_subtasks = state.get("goal_subtasks") or []
        done_count = sum(1 for t in goal_subtasks if t.get("status") == "done")
        total_count = len(goal_subtasks)
        all_done = total_count > 0 and done_count == total_count

        if score >= 6 and all_done:
            writer({"step": "goal_eval", "status": "done", "message": f"目标已达成！({done_count}/{total_count} 子任务完成)"})
            try:
                from app.agent.self_healing import get_healing_memory
                healing_memory = get_healing_memory()
                for st in goal_subtasks:
                    if st.get("status") == "done":
                        await healing_memory.mark_successful(
                            user_id=state.get("user_id", 0), subtask_id=st.get("id", 0))
            except Exception:
                pass
            return {"goal_status": "achieved"}
        elif score >= 6 and not all_done:
            # 当前轮回答质量合格，但还有子任务未完成 → 继续
            writer({"step": "goal_eval", "status": "done",
                    "message": f"当前轮质量合格 ({score}/10)，但子任务未全部完成 ({done_count}/{total_count})，继续执行"})
            return {"goal_status": "in_progress", "goal_iterations": iterations + 1}
        else:
            history = list(state.get("goal_history", []))
            history.append({
                "iteration": iterations,
                "result": final_answer[:500],
                "evaluation": reason,
                "suggestion": "提高回答长度和结构化程度",
            })
            writer({"step": "goal_eval", "status": "done",
                    "message": f"目标未达成 (第{iterations+1}轮): {reason}"})
            return {
                "goal_status": "in_progress",
                "goal_iterations": iterations + 1,
                "goal_history": history,
                "goal_current_plan": "提高回答质量",
            }

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

            # ── Worker Subgraph: 并行子任务用 worker 执行 ──
            if len(parallel_tasks) > 1:
                # 标记为 in_progress
                for task in parallel_tasks:
                    goal_subtasks = _update_subtask_status(goal_subtasks, task["id"], "in_progress", 0)
                writer({"step": "goal_subtasks", "status": "done",
                        "message": "规划完成，启动并行 Worker", "subtasks": goal_subtasks})

                # 并行执行
                worker_results = await _execute_subtasks_via_workers(parallel_tasks, state, writer)

                # 收集结果
                goal_working_memory = list(state.get("goal_working_memory") or [])
                for wr in worker_results:
                    task_id = wr["task_id"]
                    if wr["success"]:
                        goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "done", 100)
                        goal_working_memory.append({
                            "task_id": task_id,
                            "title": wr["title"],
                            "result_summary": wr["result_summary"],
                            "tools_used": wr["tools_used"],
                            "success": True,
                        })
                    else:
                        goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "failed", 0)

                # 找下一个待执行的子任务
                next_task = _get_next_pending_subtask(goal_subtasks)
                next_task_id = next_task["id"] if next_task else 0

                writer({"step": "goal_subtasks", "status": "done",
                        "message": f"并行 Worker 完成，子任务已更新", "subtasks": goal_subtasks})
                return {
                    "goal_subtasks": goal_subtasks,
                    "goal_working_memory": goal_working_memory,
                    "goal_current_task_id": next_task_id,
                }

            # 单个任务：保持原有串行逻辑
            _first_task_id = 0
            if parallel_tasks:
                for task in parallel_tasks:
                    goal_subtasks = _update_subtask_status(goal_subtasks, task["id"], "in_progress", 0)
                    if not _first_task_id:
                        _first_task_id = task["id"]
                    writer({"step": "goal_task_start", "status": "executing",
                            "message": f"规划完成，开始执行: {task['title']}",
                            "taskId": task["id"], "taskTitle": task["title"]})
            writer({"step": "goal_subtasks", "status": "done",
                    "message": "规划阶段完成，子任务已激活", "subtasks": goal_subtasks})
            return {"goal_subtasks": goal_subtasks, "goal_current_task_id": _first_task_id}

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
            if eval_passed or eval_score >= 6:
                # 质量合格 → 走 guardrail 格式校验
                passed, reason = await _guardrail_check_subtask(answer_text, current_subtask["title"], llm=llm)
                if passed:
                    goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "done", 100)
                    loop_detector.record(task_id, "done")
                    new_wm_entries.append({
                        "task_id": task_id,
                        "title": current_subtask["title"],
                        "result_summary": (answer_text[:800] + "...") if len(answer_text) > 800 else answer_text,
                        "tools_used": list(state.get("current_tools_used", [])),
                        "success": True,
                    })
                    writer({"step": "goal_task_done", "status": "done",
                            "message": f"子任务完成: {current_subtask['title']}",
                            "taskId": task_id, "taskTitle": current_subtask["title"]})
                    logger.info(f"[goal_status_updater] 子任务 #{task_id} → done")
                else:
                    # Guardrail 格式校验失败
                    fail_reason = reason
                    # ── 失败隔离: 生成降级输出而非直接标记 failed ──
                    degraded_output = ""
                    try:
                        from app.agent.failure_isolation import generate_degraded_output
                        if llm:
                            degraded = await generate_degraded_output(
                                llm=llm,
                                failed_task_title=current_subtask["title"],
                                failed_task_reason=fail_reason,
                                context=answer_text[:500] if answer_text else "",
                                memory_context=str(state.get("goal_working_memory", ""))[:500],
                            )
                            degraded_output = degraded.content
                            writer({"step": "goal_task_degraded", "status": "degraded",
                                    "message": f"子任务降级: {current_subtask['title']} → {degraded.strategy}",
                                    "taskId": task_id, "confidence": degraded.confidence})
                    except Exception as e:
                        logger.debug(f"[goal_status_updater] 降级输出生成失败: {e}")

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
                        "result_summary": degraded_output if degraded_output else f"失败: {fail_reason}",
                        "tools_used": [],
                        "success": False,
                        "degraded": bool(degraded_output),
                    })

            elif not eval_passed and eval_score < 6 and task_retry_count < 2:
                # 质量不合格但可重试 → 不标记 failed，留待下轮重试
                writer({"step": "goal_task_retry", "status": "retrying",
                        "message": f"子任务「{current_subtask['title']}」质量不合格 ({eval_score}/10)，第 {task_retry_count + 1} 次重试",
                        "taskId": task_id, "reason": eval_reason, "retry": task_retry_count + 1})
                for i, t in enumerate(goal_subtasks):
                    if t.get("id") == task_id:
                        goal_subtasks[i]["retry_count"] = task_retry_count + 1
                        goal_subtasks[i]["last_eval_feedback"] = eval_reason
                        break
                logger.info(f"[goal_status_updater] 子任务 #{task_id} 质量不合格，重试 {task_retry_count + 1}/2")

            else:
                # 重试已耗尽（retry_count >= 2）→ 直接标记 failed，不走 guardrail 放行
                fail_reason = f"质量不合格 ({eval_score}/10)，已重试 {task_retry_count} 次: {eval_reason}"
                logger.warning(f"[goal_status_updater] 子任务 #{task_id} 重试耗尽，标记 failed")
                degraded_output = ""
                try:
                    from app.agent.failure_isolation import generate_degraded_output
                    if llm:
                        degraded = await generate_degraded_output(
                            llm=llm,
                            failed_task_title=current_subtask["title"],
                            failed_task_reason=fail_reason,
                            context=answer_text[:500] if answer_text else "",
                            memory_context=str(state.get("goal_working_memory", ""))[:500],
                        )
                        degraded_output = degraded.content
                        writer({"step": "goal_task_degraded", "status": "degraded",
                                "message": f"子任务降级: {current_subtask['title']} → {degraded.strategy}",
                                "taskId": task_id, "confidence": degraded.confidence})
                except Exception as e:
                    logger.debug(f"[goal_status_updater] 降级输出生成失败: {e}")

                goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "failed", 0)
                try:
                    from app.agent.self_healing import analyze_failure, get_healing_memory
                    reflection = analyze_failure(
                        subtask_title=current_subtask["title"], subtask_id=task_id,
                        failure_source="eval", answer_text=answer_text,
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
                    "result_summary": degraded_output if degraded_output else f"失败: {fail_reason}",
                    "tools_used": [],
                    "success": False,
                    "degraded": bool(degraded_output),
                })

        # 批量标记可并行的子任务
        parallel_tasks = _get_parallel_ready_tasks(goal_subtasks)
        _next_task_id = 0

        # ── Worker Subgraph: 多个并行子任务用 worker 执行 ──
        if len(parallel_tasks) > 1:
            for task in parallel_tasks:
                goal_subtasks = _update_subtask_status(goal_subtasks, task["id"], "in_progress", 0)

            worker_results = await _execute_subtasks_via_workers(parallel_tasks, state, writer)

            for wr in worker_results:
                task_id = wr["task_id"]
                if wr["success"]:
                    goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "done", 100)
                    new_wm_entries.append({
                        "task_id": task_id,
                        "title": wr["title"],
                        "result_summary": wr["result_summary"],
                        "tools_used": wr["tools_used"],
                        "success": True,
                    })
                else:
                    goal_subtasks = _update_subtask_status(goal_subtasks, task_id, "failed", 0)
                    new_wm_entries.append({
                        "task_id": task_id,
                        "title": wr["title"],
                        "result_summary": wr["result_summary"],
                        "tools_used": [],
                        "success": False,
                    })

            # 找下一个待执行的子任务
            next_task = _get_next_pending_subtask(goal_subtasks)
            _next_task_id = next_task["id"] if next_task else 0

        elif parallel_tasks:
            # 单个任务：保持原有串行逻辑
            for task in parallel_tasks:
                goal_subtasks = _update_subtask_status(goal_subtasks, task["id"], "in_progress", 0)
                if not _next_task_id:
                    _next_task_id = task["id"]
                writer({"step": "goal_task_start", "status": "executing",
                        "message": f"开始执行: {task['title']}",
                        "taskId": task["id"], "taskTitle": task["title"]})

        # 构建子任务工具关联（从 working memory 读取已完成任务的工具列表）
        _wm_tool_map = {}
        for wm in goal_working_memory:
            _wm_tool_map[wm.get("task_id", 0)] = wm.get("tools_used", [])
        # 当前进行中子任务的工具（从 state 读取）
        _current_tools = list(state.get("current_tools_used", []))
        # 为每个子任务附加 tools 字段
        _subtasks_with_tools = []
        for st in goal_subtasks:
            st_id = st.get("id", 0)
            if st.get("status") == "done" or st.get("status") == "failed":
                tools_list = _wm_tool_map.get(st_id, [])
            elif st.get("status") == "in_progress":
                tools_list = _current_tools
            else:
                tools_list = []
            _subtasks_with_tools.append({**st, "tools": [{"tool": t, "status": "done" if st.get("status") == "done" else ("error" if st.get("status") == "failed" else "running")} for t in tools_list]})
        writer({"step": "goal_subtasks", "status": "done",
                "message": "子任务状态更新", "subtasks": _subtasks_with_tools})

        # ── 合并 Working Memory ──
        goal_working_memory.extend(new_wm_entries)

        return {"goal_subtasks": goal_subtasks, "goal_working_memory": goal_working_memory, "goal_current_task_id": _next_task_id}

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

        # ── 错误分类：区分暂时性错误 vs 永久性错误 ──
        from app.agent.error_classifier import classify_error, FailoverReason
        _has_transient_error = False
        _has_permanent_error = False
        for ft in failed_tasks:
            _err_msg = ft.get("last_eval_feedback", "") or ft.get("result_summary", "")
            if _err_msg:
                _classified = classify_error(Exception(_err_msg))
                if _classified.reason in (FailoverReason.rate_limit, FailoverReason.timeout, FailoverReason.overloaded):
                    _has_transient_error = True
                elif _classified.reason in (FailoverReason.billing, FailoverReason.auth_permanent):
                    _has_permanent_error = True

        # 暂时性错误：不重规划，直接返回 in_progress（等下轮重试）
        if _has_transient_error and not _has_permanent_error:
            writer({"step": "goal_replan", "status": "waiting",
                    "message": "检测到暂时性错误（限流/超时），跳过重规划，等待下轮重试"})
            return {"goal_status": "in_progress", "goal_iterations": iterations + 1}

        # 永久性错误：直接终止
        if _has_permanent_error:
            writer({"step": "goal_replan", "status": "done", "message": "检测到永久性错误（额度耗尽/认证失败），终止"})
            return {"goal_status": "failed"}

        # ── 有失败任务 → Reflexion + 动态重规划（P2: 正式 Reflexion 模式）──
        if failed_tasks and llm:
            try:
                # 1. 生成 Reflexion 反思（不只是自愈，是正式的 "经验→反思→改进" 闭环）
                from app.agent.self_healing import analyze_failure, get_healing_memory
                from app.agent.root_cause_analyzer import analyze_root_cause, format_root_cause_for_prompt, store_root_cause
                healing_memory = get_healing_memory()
                goal_id = str(state.get("conversation_id", 0))
                failure_summaries = []
                root_cause_texts = []
                for ft in failed_tasks:
                    reflection = analyze_failure(
                        subtask_title=ft.get("title", ""), subtask_id=ft.get("id", 0),
                        failure_source="eval", error_message="子任务执行失败",
                        user_id=state.get("user_id", 0), goal_definition=goal_def,
                    )
                    reflection.retry_count = iterations
                    await healing_memory.store(reflection, goal_id=goal_id)
                    failure_summaries.append(f"- 任务{ft.get('id')}「{ft.get('title', '')}」: {reflection.what_not_to_do}")

                    # P0: 5-Why 根因分析
                    rca = await analyze_root_cause(
                        llm=llm,
                        symptom=f"子任务「{ft.get('title', '')}」执行失败",
                        failure_context={
                            "subtask": ft.get("title", ""),
                            "error": ft.get("last_eval_feedback", ""),
                        },
                        temperature=0.3,
                    )
                    if rca:
                        root_cause_texts.append(format_root_cause_for_prompt(rca))
                        await store_root_cause(rca, user_id=state.get("user_id", 0),
                                               conversation_id=state.get("conversation_id", 0), db=None)

                # 2. P2: Reflexion 反思（对标 Reflexion 论文：失败原因→成功策略→改进方向）
                rca_section = "\n\n## 根因分析（5-Why）\n" + "\n".join(root_cause_texts) if root_cause_texts else ""

                # 跨 Goal 经验召回: 从全局 Memory 中检索类似任务的历史经验
                cross_goal_experience = ""
                try:
                    from app.agent.expert_team.memory import recall_experience
                    global_exp = await recall_experience(
                        expert_id=0, subtask=goal_def[:200], top_k=3,
                    )
                    if global_exp:
                        cross_goal_experience = global_exp
                except Exception:
                    pass

                reflexion_prompt = f"""你是一个反思专家。分析以下失败案例，提炼经验教训。

## 原始目标
{goal_def}

## 失败案例
{chr(10).join(failure_summaries)}{rca_section}

## 执行历史
{chr(10).join(f'- 轮次{h.get("iteration", "?")}: {h.get("result", "")[:100]} | 评估: {h.get("evaluation", "")[:100]}' for h in goal_history)}

## Working Memory（已完成任务的结果）
{chr(10).join(f'- 任务{w["task_id"]}「{w["title"]}」: {w["result_summary"][:80]}' for w in goal_working_memory) if goal_working_memory else '无'}
{cross_goal_experience}

请输出：
1. **失败根因**：为什么这些任务失败了？（参考 5-Why 分析）
2. **成功策略**：如果重来，应该怎么做？（具体可执行的策略）
3. **避坑指南**：下次执行时必须避免什么？
4. **资源评估**：剩余资源是否足够完成目标？（Token 预算、迭代次数）

简洁输出，每点 2-3 句话。"""

                reflexion_content = await llm.ainvoke(reflexion_prompt)
                reflexion_text = _content_blocks_to_str(reflexion_content if hasattr(reflexion_content, 'content') else reflexion_content)
                logger.info(f"[goal_replanner] Reflexion 完成: {reflexion_text[:100]}")

                # 3. 调用 LLM 动态重规划（带 Reflexion 上下文）
                from app.agent.structured_schemas import GoalReplanResult
                replan_llm = llm.with_structured_output(GoalReplanResult)

                done_tasks_text = "\n".join(
                    f"- 任务{t['id']}「{t['title']}" for t in goal_subtasks if t.get("status") == "done"
                )
                failed_text = "\n".join(failure_summaries)
                wm_text = "\n".join(
                    f"- 任务{w['task_id']}「{w['title']}」: {w['result_summary'][:80]}"
                    + (" [降级输出]" if w.get('degraded') else "")
                    for w in goal_working_memory
                ) if goal_working_memory else "无"

                replan_prompt = f"""你需要基于反思结果重新规划执行计划。

## 原始目标
{goal_def}

## 已完成的任务
{done_tasks_text or "无"}

## 失败的任务（需要重新规划）
{failed_text}

## Reflexion 反思（必须参考）
{reflexion_text}

## Working Memory（执行经验）
{wm_text}

## 资源约束
- 已用 Token: {tokens_used}，预算: {token_budget}，剩余: {token_budget - tokens_used}
- 当前轮次: {iterations}，最大轮次: {max_iterations}
- 平均每任务消耗: {int(avg_tokens)} Token

## 要求
1. 基于 Reflexion 反思调整策略
2. 对于失败的任务，可以选择：
   a) 用不同策略重试（参考反思中的「成功策略」）
   b) 拆解为更小的子任务
   c) 跳过（如果不可行且不影响最终目标）
3. 已完成的任务不要重复
4. 保持依赖关系合理
5. 子任务数量控制在 3-8 个
6. 避免反思中指出的「避坑指南」
7. 考虑资源约束，优先完成高价值任务"""

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

                # 构建子任务工具关联
                _wm_tool_map = {}
                for wm in goal_working_memory:
                    _wm_tool_map[wm.get("task_id", 0)] = wm.get("tools_used", [])
                _subtasks_with_tools = []
                for st in new_subtasks:
                    st_id = st.get("id", 0)
                    tools_list = _wm_tool_map.get(st_id, [])
                    _subtasks_with_tools.append({**st, "tools": [{"tool": t, "status": "done" if st.get("status") == "done" else ("error" if st.get("status") == "failed" else "running")} for t in tools_list]})
                writer({"step": "goal_subtasks", "status": "done",
                        "message": "子任务重规划完成", "subtasks": _subtasks_with_tools})
                return {
                    "goal_status": "in_progress",
                    "goal_iterations": iterations + 1,
                    "goal_subtasks": new_subtasks,
                    "goal_history": goal_history + [history_entry],
                    "goal_current_plan": replan_result.strategy_change[:500],
                    "goal_current_task_id": 0,
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
                # 清除原始旧 pending（不在 failed_tasks 中的 pending 任务已无意义）
                failed_task_ids = {ft["id"] for ft in failed_tasks}
                goal_subtasks = [
                    t for t in goal_subtasks
                    if t.get("status") != "pending" or t.get("id") in failed_task_ids
                ]

        # ── 无失败 或 重规划降级 → 简单继续 ──
        pending_tasks = [t for t in goal_subtasks if t.get("status") == "pending"]
        in_progress_tasks = [t for t in goal_subtasks if t.get("status") == "in_progress"]
        if not pending_tasks and not in_progress_tasks and done_count < total:
            return {"goal_status": "failed", "goal_iterations": iterations + 1, "goal_subtasks": goal_subtasks}

        # 构建子任务工具关联
        _wm_tool_map = {}
        for wm in goal_working_memory:
            _wm_tool_map[wm.get("task_id", 0)] = wm.get("tools_used", [])
        _current_tools = list(state.get("current_tools_used", []))
        _subtasks_with_tools = []
        for st in goal_subtasks:
            st_id = st.get("id", 0)
            if st.get("status") == "done" or st.get("status") == "failed":
                tools_list = _wm_tool_map.get(st_id, [])
            elif st.get("status") == "in_progress":
                tools_list = _current_tools
            else:
                tools_list = []
            _subtasks_with_tools.append({**st, "tools": [{"tool": t, "status": "done" if st.get("status") == "done" else ("error" if st.get("status") == "failed" else "running")} for t in tools_list]})
        writer({"step": "goal_subtasks", "status": "done",
                "message": f"子任务状态更新", "subtasks": _subtasks_with_tools})
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



