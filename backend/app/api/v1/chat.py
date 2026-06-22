"""AI 对话 API — 流式 SSE 唯一路径

端点:
  - POST /chat — 流式对话（SSE + 心跳保活）
  - POST /chat/resume — 审批恢复（流式）
  - GET  /chat/tool-stats — 工具使用统计
"""
import asyncio
import json
from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.services.agent_service import agent_service
from app.services.chat_service import ChatService
from app.services.llm_provider_service import LLMProviderService
from app.schemas.chat import ChatRequest
from app.schemas.response import ApiResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()
_chat_service = ChatService()
_provider_service = LLMProviderService()


async def _resolve_provider_id(db: AsyncSession, provider_id: int | None) -> int | None:
    if provider_id is not None:
        return provider_id
    default_provider = await _provider_service.get_default_provider(db)
    return default_provider.id if default_provider else None


class ResumeRequest(BaseModel):
    """审批恢复请求"""
    approved: bool
    tool_name: str = ""
    tool_args: Optional[dict] = None
    user_response: str = ""


class ChatRequestExtended(ChatRequest):
    """扩展聊天请求 — 新增 reasoning_depth / skill_id / goal_mode"""
    reasoning_depth: Optional[str] = "balanced"
    skill_id: Optional[int] = Field(default=None, description="手动指定的技能 ID", alias="skillId")
    goal_mode: bool = Field(default=False, description="是否启用 Goal 模式")
    goal_definition: str = Field(default="", description="Goal 模式的目标描述")


@router.post("/conversations/{conversation_id}/chat")
async def chat(
    request: Request,
    conversation_id: int = Path(..., description="会话 ID"),
    data: ChatRequestExtended = ...,
    db: AsyncSession = Depends(get_db),
):
    """对话入口 — 流式 SSE（唯一路径）"""
    provider_id = await _resolve_provider_id(db, data.provider_id)
    if provider_id is None:
        return api_error("CONVERSATION_VALIDATION", "请先选择 AI 供应商", "请在设置中选择供应商和模型")

    messages = [{"role": m.role, "content": m.content} for m in data.messages]
    model_name = data.model_name or ""
    user_id = getattr(data, "user_id", 0) or 0
    reasoning_depth = getattr(data, "reasoning_depth", "balanced") or "balanced"
    team_mode = data.team_mode or "off"
    team_id = data.team_id
    skill_id = data.skill_id
    goal_mode = data.goal_mode or False
    goal_definition = data.goal_definition or ""
    temperature = data.temperature or 0
    max_tokens = data.max_tokens or 0

    # Goal 模式与 manual 专家团模式互斥
    if goal_mode and team_mode == "manual":
        return api_error("CONFLICT", "Goal 模式与手动专家团模式不能同时启用", "请关闭其中一个模式")

    # manual 模式：直接执行专家团，不走 Agent 流程
    if team_mode == "manual" and team_id:
        return StreamingResponse(
            _stream_expert_team(conversation_id, team_id, messages, db),
            media_type="text/event-stream",
        )

    return StreamingResponse(
        _stream_response(conversation_id, user_id, messages, provider_id, model_name, reasoning_depth, team_mode, team_id, skill_id, goal_mode, goal_definition, temperature, max_tokens),
        media_type="text/event-stream",
    )


@router.post("/conversations/{conversation_id}/chat/resume")
async def chat_resume(
    conversation_id: int = Path(..., description="会话 ID"),
    data: ResumeRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    """
    审批恢复端点（interrupt/resume）— 按 LangGraph 官方规范实现。

    流程:
      1. Agent 遇到高风险工具 → interrupt() 暂停 → 前端弹出确认框
      2. 用户确认/拒绝 → 调用此端点
      3. 后端用 Command(resume=...) 恢复 Agent 执行
      4. 流式返回 Agent 后续执行结果

    LangGraph 官方模式:
      graph.astream(Command(resume=...), stream_mode=["messages","updates"], version="v2")
    """
    _full_content = []
    _queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    _stream_done = asyncio.Event()

    # 流开始前保存用户审批消息
    user_msg = data.user_response or f"[审批: {'批准' if data.approved else '拒绝'}] {data.tool_name}"
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as save_db:
            await _chat_service.save_skill_messages(
                save_db,
                conversation_id=conversation_id,
                user_content=user_msg,
                assistant_content="",
            )
            await save_db.commit()
    except Exception as e:
        logger.warning(f"保存审批消息失败: {e}")

    async def _save_assistant_message(content: str):
        """done 时保存助手回复"""
        if not content:
            return
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as save_db:
                await _chat_service.save_skill_messages(
                    save_db,
                    conversation_id=conversation_id,
                    user_content="",
                    assistant_content=content,
                )
                await save_db.commit()
        except Exception as e:
            logger.warning(f"保存助手消息失败: {e}")

    async def _heartbeat():
        try:
            while not _stream_done.is_set():
                await asyncio.sleep(SSE_HEARTBEAT_INTERVAL)
                if not _stream_done.is_set():
                    await _queue.put(": heartbeat\n\n")
        except asyncio.CancelledError:
            pass

    async def _produce():
        try:
            async for event in agent_service.resume_stream(
                conversation_id=conversation_id,
                approved=data.approved,
                tool_name=data.tool_name,
                tool_args=data.tool_args,
                user_response=data.user_response,
            ):
                event_type = event.get("type", "")
                if event_type == "token":
                    _full_content.append(event.get("content", ""))
                    await _queue.put(f"data: {json.dumps({'content': event['content'], 'done': False})}\n\n")
                elif event_type == "tool_start":
                    await _queue.put(f"data: {json.dumps({'tool_start': event['tool'], 'tool_args': event.get('args', {}), 'done': False})}\n\n")
                elif event_type == "tool_end":
                    await _queue.put(f"data: {json.dumps({'tool_end': event['tool'], 'output_preview': event.get('output_preview', ''), 'done': False})}\n\n")
                elif event_type == "tool_error":
                    await _queue.put(f"data: {json.dumps({'tool_error': event['tool'], 'output_preview': event.get('output_preview', ''), 'done': False})}\n\n")
                elif event_type == "progress":
                    progress = {k: v for k, v in event.items() if k != "type"}
                    await _queue.put(f"data: {json.dumps({'progress': progress, 'done': False})}\n\n")
                elif event_type == "done":
                    # done 时保存助手回复（数据完整）
                    await _save_assistant_message("".join(_full_content))
                    await _queue.put(f"data: {json.dumps({'content': '', 'done': True, 'tools_used': event.get('tools_used', []), 'duration_ms': event.get('duration_ms', 0)})}\n\n")
                elif event_type == "error":
                    await _queue.put(f"data: {json.dumps({'error': event['message'], 'done': True})}\n\n")
        except Exception as e:
            logger.error(f"Resume 流式对话失败: {e}", exc_info=True)
            await _queue.put(f"data: {json.dumps({'error': str(e), 'done': True})}\n\n")
        finally:
            _stream_done.set()
            await _queue.put(None)

    heartbeat_task = asyncio.create_task(_heartbeat())
    producer_task = asyncio.create_task(_produce())

    async def _sse_generator():
        try:
            while True:
                item = await _queue.get()
                if item is None:
                    break
                yield item
        finally:
            heartbeat_task.cancel()
            if not producer_task.done():
                producer_task.cancel()
                try:
                    await producer_task
                except (asyncio.CancelledError, Exception):
                    pass

    return StreamingResponse(_sse_generator(), media_type="text/event-stream")


@router.get("/chat/tool-stats")
async def tool_stats() -> ApiResult[dict]:
    """工具使用统计"""
    stats = agent_service.get_tool_stats()
    return ApiResult(data=stats)


# ── P2: Time Travel API ─────────────────────────────────

@router.get("/conversations/{conversation_id}/state-history")
async def state_history(conversation_id: int, limit: int = 10) -> ApiResult[list]:
    """获取图状态历史（Time Travel 调试）"""
    history = await agent_service.get_state_history(conversation_id, limit=limit)
    return ApiResult(data=history)


@router.post("/conversations/{conversation_id}/fork-state")
async def fork_state(conversation_id: int, checkpoint_id: str) -> ApiResult[bool]:
    """从指定 checkpoint 分叉状态（Time Travel fork）"""
    result = await agent_service.fork_state(conversation_id, checkpoint_id)
    return ApiResult(data=result)


SSE_HEARTBEAT_INTERVAL = 15  # 心跳间隔（秒），小于 nginx 默认 60s proxy_read_timeout


async def _stream_expert_team(conversation_id: int, team_id: int, messages: list, db: AsyncSession):
    """手动专家团模式 — LangGraph 图 + Send API 并行 + get_stream_writer 直接 yield（无 Queue）

    架构:
      LangGraph StateGraph → pm_analyze → [Send(expert)] → pm_evaluate → pm_report
      节点内 get_stream_writer() 推送事件 → astream_events(custom) → SSE 直达前端

    反压机制:
      Python generator 自带反压 — 消费者停止读取时，generator 在 yield 处暂停，
      图执行自动暂停。无 Queue，无堆积，无内存泄漏。
    """
    from app.agent.expert_team_graph import build_expert_team_graph, ExpertTeamState
    from app.services.expert_team_service import ExpertTeamService

    user_content = messages[-1]["content"] if messages else ""

    # 加载专家团配置
    service = ExpertTeamService()
    team = await service.repo.find_team_by_id(db, team_id)
    if not team:
        yield f"data: {json.dumps({'error': '专家团不存在', 'done': True})}\n\n"
        return

    leader = None
    if team.leader_id:
        leader = await service.repo.find_expert_by_id(db, team.leader_id)
    if not leader:
        yield f"data: {json.dumps({'error': '专家团未设置组长', 'done': True})}\n\n"
        return

    experts = await service.repo.find_experts_by_team(db, team_id)
    enabled_experts = [e for e in experts if e.is_enabled == 1 and e.id != leader.id]
    if not enabled_experts:
        yield f"data: {json.dumps({'error': '专家团没有可用的专家成员', 'done': True})}\n\n"
        return

    # 序列化专家信息
    experts_data = [service._to_out_expert(e).model_dump() for e in enabled_experts]
    leader_data = service._to_out_expert(leader).model_dump()

    # 模型配置
    from app.services.llm_provider_service import LLMProviderService
    provider_service = LLMProviderService()
    default_provider = await provider_service.get_default_provider(db)
    default_provider_id = default_provider.id if default_provider else 0
    default_model_name = ""
    if default_provider and default_provider.models:
        enabled_models = [m for m in default_provider.models if m.is_enabled == 1]
        if enabled_models:
            default_model_name = enabled_models[0].model_name

    pm_provider_id = leader.provider_id or default_provider_id
    pm_model_name = leader.model_name or default_model_name
    pm_temperature = leader.temperature or 0.3

    # 创建运行记录
    run = await service.repo.create_run(db, {
        "team_id": team_id,
        "run_status": 1,
        "trigger_type": 0,
        "input_text": user_content,
    })

    # 构建初始状态
    initial_state: ExpertTeamState = {
        "input_text": user_content,
        "team_id": team_id,
        "run_id": run.id,
        "max_rounds": team.max_rounds or 3,
        "current_round": 1,
        "db": db,
        "experts_data": experts_data,
        "leader_data": leader_data,
        "pm_provider_id": pm_provider_id,
        "pm_model_name": pm_model_name,
        "pm_temperature": pm_temperature,
        "expert_results": [],
        "discussion": [],
        "total_tokens": 0,
        "feedback_map": {},
    }

    # 推送开始事件
    yield f"data: {json.dumps({'progress': {'step': 'expert_team', 'status': 'running', 'message': '正在执行专家团...'}, 'done': False})}\n\n"

    # 构建并执行图
    graph = build_expert_team_graph()
    t0 = __import__("time").time()
    NL = "\n"

    # 心跳保活：用 asyncio.Queue 合并心跳和图事件
    _hb_queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _graph_done = asyncio.Event()

    async def _heartbeat_producer():
        """心跳协程 — 定期发送 SSE 注释保活"""
        try:
            while not _graph_done.is_set():
                await asyncio.sleep(SSE_HEARTBEAT_INTERVAL)
                if not _graph_done.is_set():
                    await _hb_queue.put(": heartbeat\n\n")
        except asyncio.CancelledError:
            pass

    async def _graph_producer():
        """图事件生产者 — 从 astream_events 读取 custom 事件放入队列"""
        try:
            async for event in graph.astream_events(initial_state, version="v3"):
                method = event.get("method", "")
                if method == "custom":
                    await _hb_queue.put(event)
        finally:
            _graph_done.set()
            await _hb_queue.put(None)  # 哨兵值

    heartbeat_task = asyncio.create_task(_heartbeat_producer())
    graph_task = asyncio.create_task(_graph_producer())

    try:
        while True:
            item = await _hb_queue.get()
            if item is None:
                break
            # 心跳注释行（字符串）
            if isinstance(item, str):
                yield item
                continue

            # 图事件（dict）
            event = item
            data = event.get("params", {}).get("data", {}) if isinstance(event.get("params"), dict) else {}

            evt_type = data.get("type", "")


            if evt_type == "pm_plan":
                content = data.get("content", "")
                header = f"**◆ PM** 分析完成:{NL}"
                yield f"data: {json.dumps({'content': header, 'done': False})}{NL}{NL}"
                yield f"data: {json.dumps({'content': content + NL + NL, 'done': False})}{NL}{NL}"
                yield f"data: {json.dumps({'progress': {'step': 'pm_plan', 'status': 'done', 'message': 'PM 任务规划完成'}, 'done': False})}{NL}{NL}"

            elif evt_type == "expert_start":
                name = data.get("expertName", "")
                round_num = data.get("round", 0)
                avatar = data.get("avatar", "🤖")
                role = data.get("expertRole", "")
                subtask = data.get("subtask", "")
                prefix = "" if (avatar and avatar.startswith(("data:", "http"))) else (f"{avatar} " if avatar else "")
                msg = f"**{prefix}{name}** ({role}){NL}{subtask}{NL}{NL}"
                yield f"data: {json.dumps({'content': msg, 'done': False})}{NL}{NL}"
                _exp_progress = {'step': f'expert_{name}', 'status': 'executing', 'message': f'{name}({role}) 正在分析...', 'expertName': name, 'expertRole': role, 'avatar': avatar, 'round': round_num, 'maxRounds': initial_state.get('max_rounds', 3)}
                yield f"data: {json.dumps({'progress': _exp_progress, 'done': False})}{NL}{NL}"

            elif evt_type == "expert_done":
                name = data.get("expertName", "")
                duration = data.get("durationMs", 0)
                round_num = data.get("round", 0)
                avatar = data.get("avatar", "🤖")
                role = data.get("expertRole", "")
                expert_content = data.get("content", "")
                prefix = "" if (avatar and avatar.startswith(("data:", "http"))) else (f"{avatar} " if avatar else "")
                header = f"**{prefix}{name}** ({role}) · {duration}ms{NL}"
                yield f"data: {json.dumps({'content': header, 'done': False})}{NL}{NL}"
                if expert_content:
                    yield f"data: {json.dumps({'content': expert_content + NL + NL, 'done': False})}{NL}{NL}"
                _exp_progress = {'step': f'expert_{name}', 'status': 'done', 'message': f'{name}({role}) 分析完成', 'elapsedMs': duration, 'expertName': name, 'expertRole': role, 'avatar': avatar, 'round': round_num, 'maxRounds': initial_state.get('max_rounds', 3)}
                yield f"data: {json.dumps({'progress': _exp_progress, 'done': False})}{NL}{NL}"

            elif evt_type == "pm_eval":
                evaluation = data.get("evaluation", {})
                overall_pass = evaluation.get("overall_pass", False)
                reason = evaluation.get("reason", "")
                status_text = "✅ 达标" if overall_pass else "⚠️ 未达标，将返工"
                yield f"data: {json.dumps({'content': f'**◆ PM 评估:** {status_text}{NL}{reason}{NL}{NL}', 'done': False})}{NL}{NL}"
                yield f"data: {json.dumps({'progress': {'step': 'pm_eval', 'status': 'done', 'message': f'PM 评估: {status_text}'}, 'done': False})}{NL}{NL}"

            elif evt_type == "pm_report":
                content = data.get("content", "")
                header = f"---{NL}**◆ 最终报告:**{NL}{NL}"
                yield f"data: {json.dumps({'content': header, 'done': False})}{NL}{NL}"
                yield f"data: {json.dumps({'content': content, 'done': False})}{NL}{NL}"
                yield f"data: {json.dumps({'progress': {'step': 'expert_team', 'status': 'done', 'message': '专家团执行完成'}, 'done': False})}{NL}{NL}"

        # 获取最终状态
        elapsed = int((__import__("time").time() - t0) * 1000)
        yield f"data: {json.dumps({'content': '', 'done': True, 'duration_ms': elapsed})}\n\n"

    except Exception as e:
        logger.error(f"专家团执行失败: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': f'专家团执行失败: {e}', 'done': True})}\n\n"
    finally:
        heartbeat_task.cancel()
        if not graph_task.done():
            graph_task.cancel()
            try:
                await graph_task
            except (asyncio.CancelledError, Exception):
                pass

async def _stream_response(
    conversation_id: int, user_id: int, messages: list,
    provider_id: int, model_name: str, reasoning_depth: str = "balanced",
    team_mode: str = "off", team_id: int | None = None, skill_id: int | None = None,
    goal_mode: bool = False, goal_definition: str = "",
    temperature: float = 0, max_tokens: int = 0,
):
    """SSE 流式响应 — 带心跳保活 + 消息持久化

    消息保存策略（业内标准）:
      - 用户消息：流开始前保存（确保不丢）
      - 助手回复：done 事件时保存（数据完整 + 携带 token 统计）
      - 流中断/报错：助手回复不保存（前端本地有 token，刷新后丢失是预期行为）
      - SSE 断开时：立即取消 producer_task，释放 Agent 资源
        （每次对话都从 initial_state 全新执行，无需保留 producer）

    心跳机制（业内规范）:
      - 发送 SSE 注释行 ': heartbeat\\n\\n'，不触发前端 onmessage
      - 间隔 15s（< nginx 60s proxy_read_timeout）
      - 用 asyncio.Queue 合并心跳和业务事件到同一个生成器
    """
    _full_content = []
    _queue: asyncio.Queue = asyncio.Queue(maxsize=200)  # 防止 SSE 断开后无限堆积
    _stream_done = asyncio.Event()

    # 流开始前保存用户消息（独立事务，确保不丢）
    user_content = messages[-1]["content"] if messages else ""
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as save_db:
            await _chat_service.save_skill_messages(
                save_db,
                conversation_id=conversation_id,
                user_content=user_content,
                assistant_content="",  # 仅保存用户消息
            )
            await save_db.commit()
    except Exception as e:
        logger.warning(f"保存用户消息失败: {e}")

    async def _heartbeat():
        """心跳协程 — 定期发送 SSE 注释保活"""
        try:
            while not _stream_done.is_set():
                await asyncio.sleep(SSE_HEARTBEAT_INTERVAL)
                if not _stream_done.is_set():
                    await _queue.put(": heartbeat\n\n")
        except asyncio.CancelledError:
            pass

    async def _save_assistant_message(content: str, token_count: int):
        """done 时保存助手回复（独立事务）"""
        if not content:
            return
        try:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as save_db:
                await _chat_service.save_skill_messages(
                    save_db,
                    conversation_id=conversation_id,
                    user_content="",  # 仅保存助手回复
                    assistant_content=content,
                    token_count=token_count,
                )
                await save_db.commit()
        except Exception as e:
            logger.warning(f"保存助手消息失败: {e}")

    async def _produce():
        """业务事件生产者 — 从 agent_service 读取事件放入队列"""
        try:
            async for event in agent_service.chat_stream(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=messages,
                provider_id=provider_id,
                model_name=model_name,
                reasoning_depth=reasoning_depth,
                team_mode=team_mode,
                team_id=team_id,
                skill_id=skill_id,
                goal_mode=goal_mode,
                goal_definition=goal_definition,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                event_type = event.get("type", "")
                if event_type == "token":
                    _full_content.append(event.get("content", ""))
                    await _queue.put(f"data: {json.dumps({'content': event['content'], 'done': False})}\n\n")
                elif event_type == "tool_start":
                    await _queue.put(f"data: {json.dumps({'tool_start': event['tool'], 'tool_args': event.get('args', {}), 'done': False})}\n\n")
                elif event_type == "tool_end":
                    await _queue.put(f"data: {json.dumps({'tool_end': event['tool'], 'output_preview': event.get('output_preview', ''), 'done': False})}\n\n")
                elif event_type == "tool_error":
                    await _queue.put(f"data: {json.dumps({'tool_error': event['tool'], 'output_preview': event.get('output_preview', ''), 'done': False})}\n\n")
                elif event_type == "intent_hit":
                    await _queue.put(f"data: {json.dumps({'intent_hit': event['intent'], 'intent_score': event.get('score', 0), 'done': False})}\n\n")
                elif event_type == "cost_update":
                    await _queue.put(f"data: {json.dumps({'cost': {'prompt_tokens': event['prompt_tokens'], 'completion_tokens': event['completion_tokens']}, 'done': False})}\n\n")
                elif event_type == "approval_required":
                    await _queue.put(f"data: {json.dumps({'approval_required': {'tool': event.get('tool', ''), 'args': event.get('args', {}), 'message': event.get('message', '')}, 'done': False})}\n\n")
                elif event_type == "progress":
                    # Agent 执行进展事件（AG-UI 协议兼容）
                    progress = {k: v for k, v in event.items() if k != "type"}
                    await _queue.put(f"data: {json.dumps({'progress': progress, 'done': False})}\n\n")
                elif event_type == "goal_subtasks":
                    # Goal 模式子任务更新事件
                    await _queue.put(f"data: {json.dumps({'goal_subtasks': event.get('subtasks', []), 'done': False})}\n\n")
                elif event_type == "done":
                    prompt_tokens = event.get("prompt_tokens", 0)
                    completion_tokens = event.get("completion_tokens", 0)
                    total_tokens = prompt_tokens + completion_tokens
                    goal_subtasks = event.get("goal_subtasks", [])
                    # done 时保存助手回复（数据完整）
                    await _save_assistant_message("".join(_full_content), total_tokens)
                    await _queue.put(f"data: {json.dumps({'content': '', 'done': True, 'tools_used': event.get('tools_used', []), 'duration_ms': event.get('duration_ms', 0), 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'goal_subtasks': goal_subtasks})}\n\n")
                elif event_type == "error":
                    await _queue.put(f"data: {json.dumps({'error': event['message'], 'done': True})}\n\n")
        except Exception as e:
            logger.error(f"流式对话失败: {e}", exc_info=True)
            await _queue.put(f"data: {json.dumps({'error': str(e), 'done': True})}\n\n")
        finally:
            _stream_done.set()
            await _queue.put(None)  # 哨兵值，通知消费者结束

    # 启动心跳和生产者协程
    heartbeat_task = asyncio.create_task(_heartbeat())
    producer_task = asyncio.create_task(_produce())

    try:
        # 消费者循环 — 从队列读取事件并 yield
        while True:
            item = await _queue.get()
            if item is None:
                break
            yield item
    finally:
        heartbeat_task.cancel()
        # SSE 断开时取消 producer_task，释放 Agent 资源。
        # 每次对话都从 initial_state 全新执行，无需保留 producer 继续运行。
        # 取消后 producer_task 在下一个 await 点抛出 CancelledError 并退出。
        if not producer_task.done():
            producer_task.cancel()
            try:
                await producer_task
            except (asyncio.CancelledError, Exception):
                pass
