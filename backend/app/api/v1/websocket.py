"""WebSocket 路由 — 支持 Agent 流式输出 + JWT 鉴权"""
import time
from collections import OrderedDict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import ws_manager
from app.core.security import _get_jwt_secret, JWT_ALGORITHM
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()

# 消息去重缓存（LRU，10 秒过期，最多 100 条）
_recent_msgs: OrderedDict[str, float] = OrderedDict()


async def _authenticate_ws(websocket: WebSocket, token: str | None) -> tuple[int | None, int]:
    """
    WebSocket JWT 鉴权。

    Returns:
        (user_id, close_code):
        - (0, 0): guest 模式
        - (user_id, 0): 认证成功
        - (None, 4001): token 过期
        - (None, 4003): token 无效
    """
    if not token:
        logger.info("WebSocket 无 token，以 guest 模式连接")
        return 0, 0

    import jwt as pyjwt
    try:
        payload = pyjwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        return None, 4001
    except Exception:
        return None, 4003

    user_id = payload.get("user_id") or payload.get("sub")
    if user_id is not None:
        try:
            return int(user_id), 0
        except (ValueError, TypeError):
            pass

    return None, 4003


@router.websocket("/ws")
@router.websocket("/ws/{channel}")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str = "default",
    token: str | None = Query(default=None, description="JWT 认证 token"),
):
    """
    WebSocket 连接端点

    鉴权方式: ?token=<jwt>
    鉴权失败: 返回 403 关闭连接
    鉴权成功: user_id 附加到 websocket.state

    /ws          → 默认 channel (default)
    /ws/{channel} → 指定 channel: chat, pet, notification, system 等
    """
    # 先 accept，再鉴权（未 accept 时不能 close/receive）
    await websocket.accept()

    # JWT 鉴权（无 token 时允许 guest 连接）
    user_id, close_code = await _authenticate_ws(websocket, token)
    if user_id is None:
        reason = "AUTH_EXPIRED" if close_code == 4001 else "AUTH_INVALID"
        await websocket.close(code=close_code, reason=reason)
        logger.warning(f"WebSocket 鉴权失败（{reason}）: channel={channel}")
        return

    # 鉴权通过，存储 user_id
    websocket.state.user_id = user_id
    logger.info(f"WebSocket 连接: channel={channel} user_id={user_id}")

    await ws_manager.connect(websocket, channel, _already_accepted=True)

    # 全局心跳 + 空闲超时
    import asyncio as _asyncio
    _idle_since = time.time()
    _hb_done = _asyncio.Event()

    async def _global_heartbeat():
        try:
            while not _hb_done.is_set():
                await _asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                if _hb_done.is_set():
                    break
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                if time.time() - _idle_since > settings.WS_IDLE_TIMEOUT:
                    try:
                        await websocket.close(code=4002, reason="IDLE_TIMEOUT")
                    except Exception:
                        pass
                    break
        except _asyncio.CancelledError:
            pass

    _hb_task = _asyncio.create_task(_global_heartbeat())

    try:
        while True:
            data = await websocket.receive_json()
            _idle_since = time.time()  # 收到消息，重置空闲计时

            # 心跳
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Agent 对话消息
            if data.get("type") == "chat" and channel == "chat":
                _idle_since = time.time()  # agent 处理期间重置空闲计时
                await _handle_agent_ws(websocket, data, user_id)
                _idle_since = time.time()  # agent 完成后也重置
                continue

            # 审批恢复消息
            if data.get("type") == "resume" and channel == "chat":
                _idle_since = time.time()
                await _handle_resume_ws(websocket, data, user_id)
                _idle_since = time.time()
                continue

            # 其他消息广播
            await ws_manager.broadcast(channel, data)

    except WebSocketDisconnect:
        pass
    except RuntimeError:
        # accept 后连接异常断开时 receive_json 抛出 RuntimeError
        logger.debug(f"WebSocket 运行时异常（连接已断）: channel={channel} user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket 未预期异常: {e}", exc_info=True)
    finally:
        _hb_done.set()
        _hb_task.cancel()
        ws_manager.disconnect(websocket, channel)
        logger.info(f"WebSocket 断开: channel={channel} user_id={user_id}")


async def _handle_agent_ws(websocket: WebSocket, data: dict, user_id: int):
    """通过 WebSocket 流式处理 Agent 对话（v6.3: 队列缓冲 + 心跳 + 全事件支持）"""
    import asyncio
    from app.services.agent_service import agent_service

    content = data.get("content", "")
    conversation_id = data.get("conversationId", 0)
    provider_id = data.get("providerId")
    model_name = data.get("modelName", "")
    reasoning_depth = data.get("reasoningDepth", "balanced")
    goal_mode = data.get("goalMode", False)
    goal_definition = data.get("goalDefinition", "")
    team_mode = data.get("teamMode", "off")
    team_id = data.get("teamId")
    skill_id = data.get("skillId")
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("maxTokens", 2048)

    if not content:
        await websocket.send_json({"type": "chat_error", "message": "消息内容为空"})
        return

    # 防重：同一会话短时间内不重复处理相同消息
    _dedup_key = f"ws_chat:{conversation_id}:{hash(content)}"
    _now = time.time()
    if _dedup_key in _recent_msgs and _now - _recent_msgs[_dedup_key] < 10:
        logger.warning(f"[ws] 消息去重: conversation={conversation_id}")
        return
    _recent_msgs[_dedup_key] = _now
    while len(_recent_msgs) > 100:
        _recent_msgs.popitem(last=False)

    # 消息持久化：流开始前保存用户消息
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.chat_service import ChatService
        _chat_svc = ChatService()
        async with AsyncSessionLocal() as save_db:
            await _chat_svc.save_skill_messages(
                save_db, conversation_id=conversation_id,
                user_content=content, assistant_content="",
            )
            await save_db.commit()
    except Exception as e:
        logger.warning(f"[ws] 保存用户消息失败: {e}")

    # 懒初始化 Agent 引擎
    if not agent_service.is_ready:
        success = await agent_service._lazy_init(provider_id, model_name)
        if not success:
            await websocket.send_json({"type": "chat_error", "message": "Agent 引擎初始化失败"})
            return

    # ── 队列 + 后台任务 + 心跳 ──
    _queue: asyncio.Queue = asyncio.Queue(maxsize=settings.WS_QUEUE_MAXSIZE)
    _stream_done = asyncio.Event()
    _accumulated_content = ""

    async def _save_assistant_message(msg_content: str, token_count: int = 0):
        """done 时保存助手消息"""
        if not msg_content:
            return
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.chat_service import ChatService
            _chat_svc = ChatService()
            async with AsyncSessionLocal() as save_db:
                await _chat_svc.save_skill_messages(
                    save_db, conversation_id=conversation_id,
                    user_content="", assistant_content=msg_content,
                    token_count=token_count,
                )
                await save_db.commit()
        except Exception as e:
            logger.warning(f"[ws] 保存助手消息失败: {e}")

    async def _produce():
        """生产者：Agent 执行 → 事件写入队列"""
        nonlocal _accumulated_content
        try:
            # 专家团手动模式
            if team_mode == "manual" and team_id:
                from app.agent.expert_team_stream import stream_expert_team
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as db:
                    async for event in stream_expert_team(conversation_id, team_id, [{"role": "user", "content": content}], db):
                        if _stream_done.is_set():
                            break
                        event_type = event.get("type", "")
                        if event_type == "token":
                            _accumulated_content += event.get("content", "")
                            await _queue.put({"type": "chat_token", "content": event["content"]})
                        elif event_type == "progress":
                            progress = {k: v for k, v in event.items() if k != "type"}
                            await _queue.put({"type": "chat_progress", **progress})
                        elif event_type == "done":
                            await _save_assistant_message(_accumulated_content)
                            await _queue.put({"type": "chat_done", "tools_used": event.get("tools_used", []), "duration_ms": event.get("duration_ms", 0), "prompt_tokens": 0, "completion_tokens": 0, "goal_subtasks": [], "is_error": False})
                        elif event_type == "error":
                            await _queue.put({"type": "chat_error", "message": event["message"]})
                return

            # 普通 Agent 模式
            async for event in agent_service.chat_stream(
                conversation_id=conversation_id,
                user_id=user_id,
                messages=[{"role": "user", "content": content}],
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
                if _stream_done.is_set():
                    break
                event_type = event.get("type", "")

                if event_type == "token":
                    _accumulated_content += event.get("content", "")
                    await _queue.put({"type": "chat_token", "content": event["content"]})
                elif event_type == "thinking":
                    await _queue.put({"type": "chat_thinking", "content": event.get("content", "")})
                elif event_type == "tool_start":
                    await _queue.put({"type": "chat_tool_start", "tool": event["tool"], "args": event.get("args", {})})
                elif event_type == "tool_end":
                    await _queue.put({"type": "chat_tool_end", "tool": event["tool"], "output_preview": event.get("output_preview", "")})
                elif event_type == "tool_error":
                    await _queue.put({"type": "chat_tool_error", "tool": event["tool"], "output_preview": event.get("output_preview", "")})
                elif event_type == "progress":
                    progress = {k: v for k, v in event.items() if k != "type"}
                    await _queue.put({"type": "chat_progress", **progress})
                elif event_type == "goal_subtasks":
                    await _queue.put({"type": "chat_goal_subtasks", "subtasks": event.get("subtasks", [])})
                elif event_type == "goal_tool_update":
                    await _queue.put({"type": "chat_goal_tool_update", "task_id": event.get("task_id", 0), "tool": event.get("tool", ""), "tool_status": event.get("tool_status", ""), "args": event.get("args", {}), "output_preview": event.get("output_preview", "")})
                elif event_type == "intent_hit":
                    await _queue.put({"type": "chat_intent_hit", "intent": event["intent"], "score": event.get("score", 0)})
                elif event_type == "cost_update":
                    await _queue.put({"type": "chat_cost_update", "prompt_tokens": event["prompt_tokens"], "completion_tokens": event["completion_tokens"]})
                elif event_type == "approval_required":
                    await _queue.put({"type": "chat_approval_required", "tool": event.get("tool", ""), "args": event.get("args", {}), "message": event.get("message", "")})
                elif event_type == "done":
                    # 保存助手消息
                    await _save_assistant_message(_accumulated_content, event.get("prompt_tokens", 0) + event.get("completion_tokens", 0))
                    await _queue.put({"type": "chat_done", "tools_used": event.get("tools_used", []), "duration_ms": event.get("duration_ms", 0), "prompt_tokens": event.get("prompt_tokens", 0), "completion_tokens": event.get("completion_tokens", 0), "goal_subtasks": event.get("goal_subtasks", []), "is_error": event.get("is_error", False)})
                elif event_type == "error":
                    await _queue.put({"type": "chat_error", "message": event["message"]})

        except Exception as e:
            logger.error(f"WebSocket Agent 生产者失败: {e}", exc_info=True)
            await _queue.put({"type": "chat_error", "message": str(e)})
        finally:
            _stream_done.set()
            await _queue.put(None)  # 哨兵值

    async def _heartbeat():
        """心跳：每 WS_HEARTBEAT_INTERVAL 秒发送 ping，防止中间层超时断连"""
        try:
            while not _stream_done.is_set():
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                if not _stream_done.is_set():
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception:
                        break
        except asyncio.CancelledError:
            pass

    # 启动生产者和心跳
    producer_task = asyncio.create_task(_produce())
    heartbeat_task = asyncio.create_task(_heartbeat())

    try:
        await websocket.send_json({"type": "chat_start"})

        # 消费者：从队列读取事件并发送
        while True:
            item = await _queue.get()
            if item is None:
                break
            try:
                await websocket.send_json(item)
            except Exception:
                logger.warning("WebSocket 发送失败，客户端可能已断开")
                _stream_done.set()
                break

    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开")
        _stream_done.set()
    except (Exception, asyncio.CancelledError) as e:
        logger.error(f"WebSocket Agent 对话失败: {e}", exc_info=True)
        _stream_done.set()
        try:
            await websocket.send_json({"type": "chat_error", "message": str(e)})
        except Exception:
            pass
    finally:
        _stream_done.set()
        heartbeat_task.cancel()
        producer_task.cancel()
        try:
            await heartbeat_task
        except (asyncio.CancelledError, Exception):
            pass
        try:
            await producer_task
        except (asyncio.CancelledError, Exception):
            pass


async def _handle_resume_ws(websocket: WebSocket, data: dict, user_id: int):
    """审批恢复 — 通过 WebSocket（替代原 SSE 路径）"""
    import asyncio
    from app.services.agent_service import agent_service

    conversation_id = data.get("conversationId", 0)
    approved = data.get("approved", False)
    tool_name = data.get("toolName", "")
    tool_args = data.get("toolArgs")
    user_response = data.get("userResponse", "")

    # 保存用户审批消息
    try:
        from app.core.database import AsyncSessionLocal
        from app.services.chat_service import ChatService
        _chat_svc = ChatService()
        user_msg = user_response or f"[审批: {'批准' if approved else '拒绝'}] {tool_name}"
        async with AsyncSessionLocal() as save_db:
            await _chat_svc.save_skill_messages(
                save_db, conversation_id=conversation_id,
                user_content=user_msg, assistant_content="",
            )
            await save_db.commit()
    except Exception as e:
        logger.warning(f"[ws] 保存审批消息失败: {e}")

    _queue: asyncio.Queue = asyncio.Queue(maxsize=settings.WS_QUEUE_MAXSIZE)
    _stream_done = asyncio.Event()
    _accumulated_content = ""

    async def _save_assistant_message(msg_content: str, token_count: int = 0):
        if not msg_content:
            return
        try:
            from app.core.database import AsyncSessionLocal
            from app.services.chat_service import ChatService
            _chat_svc = ChatService()
            async with AsyncSessionLocal() as save_db:
                await _chat_svc.save_skill_messages(
                    save_db, conversation_id=conversation_id,
                    user_content="", assistant_content=msg_content,
                    token_count=token_count,
                )
                await save_db.commit()
        except Exception as e:
            logger.warning(f"[ws] 保存助手消息失败: {e}")

    async def _produce():
        nonlocal _accumulated_content
        try:
            async for event in agent_service.resume_stream(
                conversation_id=conversation_id,
                approved=approved,
                tool_name=tool_name,
                tool_args=tool_args,
                user_response=user_response,
            ):
                if _stream_done.is_set():
                    break
                event_type = event.get("type", "")

                if event_type == "token":
                    _accumulated_content += event.get("content", "")
                    await _queue.put({"type": "chat_token", "content": event["content"]})
                elif event_type == "thinking":
                    await _queue.put({"type": "chat_thinking", "content": event.get("content", "")})
                elif event_type == "tool_start":
                    await _queue.put({"type": "chat_tool_start", "tool": event["tool"], "args": event.get("args", {})})
                elif event_type == "tool_end":
                    await _queue.put({"type": "chat_tool_end", "tool": event["tool"], "output_preview": event.get("output_preview", "")})
                elif event_type == "tool_error":
                    await _queue.put({"type": "chat_tool_error", "tool": event["tool"], "output_preview": event.get("output_preview", "")})
                elif event_type == "progress":
                    progress = {k: v for k, v in event.items() if k != "type"}
                    await _queue.put({"type": "chat_progress", **progress})
                elif event_type == "done":
                    await _save_assistant_message(_accumulated_content, event.get("prompt_tokens", 0) + event.get("completion_tokens", 0))
                    await _queue.put({"type": "chat_done", "tools_used": event.get("tools_used", []), "duration_ms": event.get("duration_ms", 0), "prompt_tokens": event.get("prompt_tokens", 0), "completion_tokens": event.get("completion_tokens", 0), "goal_subtasks": event.get("goal_subtasks", []), "is_error": event.get("is_error", False)})
                elif event_type == "error":
                    await _queue.put({"type": "chat_error", "message": event["message"]})
        except Exception as e:
            logger.error(f"[ws] Resume 生产者失败: {e}", exc_info=True)
            await _queue.put({"type": "chat_error", "message": str(e)})
        finally:
            _stream_done.set()
            await _queue.put(None)

    producer_task = asyncio.create_task(_produce())

    try:
        while True:
            item = await _queue.get()
            if item is None:
                break
            try:
                await websocket.send_json(item)
            except Exception:
                _stream_done.set()
                break
    except WebSocketDisconnect:
        _stream_done.set()
    finally:
        _stream_done.set()
        producer_task.cancel()
        try:
            await producer_task
        except (asyncio.CancelledError, Exception):
            pass
