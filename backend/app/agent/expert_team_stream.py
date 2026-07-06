"""专家团流式执行 — 返回标准事件 dict，SSE/WS 共用

从 chat.py 的 _stream_expert_team 中抽取核心逻辑，
yield dict 事件而不是 SSE 字符串。

v3: astream_events(version="v3") + StreamTransformer 捕获 custom 事件，
    同时消费 stream.messages 获取 LLM token + reasoning。
"""
import asyncio
import json
import time
import logging
from typing import AsyncIterator, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── StreamTransformer: 捕获 get_stream_writer() 的 custom 事件 ──
try:
    from langgraph.stream import ProtocolEvent, StreamChannel, StreamTransformer

    class CustomEventTransformer(StreamTransformer):
        """捕获节点内 get_stream_writer() 发射的 custom 事件"""
        required_stream_modes = ("custom",)

        def __init__(self, scope: tuple = ()):
            super().__init__(scope)
            self.events = StreamChannel("custom_events")

        def init(self) -> dict:
            return {"custom_events": self.events}

        def process(self, event: ProtocolEvent) -> bool:
            if event["method"] == "custom":
                self.events.push(event["params"]["data"])
            return True

    _HAS_STREAM_TRANSFORMER = True
except ImportError:
    _HAS_STREAM_TRANSFORMER = False


async def stream_expert_team(
    conversation_id: int,
    team_id: int,
    messages: list,
    db,
) -> AsyncIterator[Dict[str, Any]]:
    """专家团流式执行 — 返回标准事件 dict

    Yields:
        dict: 事件字典，包含 type 字段
        - {"type": "progress", "step": "expert_team", "status": "running", ...}
        - {"type": "token", "content": "..."}
        - {"type": "progress", "step": "pm_plan", ...}
        - {"type": "progress", "step": "expert_xxx", ...}
        - {"type": "progress", "step": "pm_eval", ...}
        - {"type": "progress", "step": "expert_team", "status": "done", ...}
        - {"type": "done", "tools_used": [], "duration_ms": ...}
        - {"type": "error", "message": "..."}
    """
    from app.agent.expert_team_graph import build_expert_team_graph, ExpertTeamState
    from app.services.expert_team_service import ExpertTeamService

    user_content = messages[-1]["content"] if messages else ""

    # 加载专家团配置
    service = ExpertTeamService()
    team = await service.repo.find_team_by_id(db, team_id)
    if not team:
        yield {"type": "error", "message": "专家团不存在"}
        return

    leader = None
    if team.leader_id:
        leader = await service.repo.find_expert_by_id(db, team.leader_id)
    if not leader:
        yield {"type": "error", "message": "专家团未设置组长"}
        return

    experts = await service.repo.find_experts_by_team(db, team_id)
    enabled_experts = [e for e in experts if e.is_enabled == 1 and e.id != leader.id]
    if not enabled_experts:
        yield {"type": "error", "message": "专家团没有可用的专家成员"}
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
        "final_report": "",
        "total_tokens": 0,
        "feedback_map": {},
    }

    # 推送开始事件
    yield {"type": "progress", "step": "expert_team", "status": "running", "message": "正在执行专家团..."}

    # 构建并执行图
    graph = build_expert_team_graph()
    t0 = time.time()

    try:
        transformers = [CustomEventTransformer] if _HAS_STREAM_TRANSFORMER else []
        stream = await graph.astream_events(
            initial_state,
            version="v3",
            transformers=transformers,
        )

        # ── 并发消费 custom 事件 + 主流 ──
        custom_iter = stream.extensions.get("custom_events") if _HAS_STREAM_TRANSFORMER else None

        async def _consume_custom():
            """custom 事件 → progress/thinking 事件"""
            if not custom_iter:
                return
            async for data in custom_iter:
                if not isinstance(data, dict):
                    continue
                evt_type = data.get("type", "")

                if evt_type == "thinking":
                    yield {"type": "thinking", "content": data.get("content", "")}
                elif evt_type == "pm_plan":
                    yield {"type": "progress", "step": "pm_plan", "status": "done", "message": "PM 任务规划完成", "content": data.get("content", "")}
                elif evt_type == "expert_start":
                    yield {"type": "progress", "step": f"expert_{data.get('expertName', '')}", "status": "executing", "message": f"{data.get('expertName', '')} 正在分析...", "expertName": data.get("expertName", ""), "expertRole": data.get("expertRole", ""), "avatar": data.get("avatar", ""), "round": data.get("round", 0), "maxRounds": initial_state.get("max_rounds", 3)}
                elif evt_type == "expert_done":
                    yield {"type": "progress", "step": f"expert_{data.get('expertName', '')}", "status": "done", "message": f"{data.get('expertName', '')} 分析完成", "elapsedMs": data.get("durationMs", 0), "expertName": data.get("expertName", ""), "expertRole": data.get("expertRole", ""), "avatar": data.get("avatar", ""), "round": data.get("round", 0), "maxRounds": initial_state.get("max_rounds", 3)}
                    content = data.get("content", "")
                    if content:
                        yield {"type": "token", "content": content + "\n\n"}
                elif evt_type == "pm_eval":
                    evaluation = data.get("evaluation", {})
                    overall_pass = evaluation.get("overall_pass", False)
                    status_text = "✅ 达标" if overall_pass else "⚠️ 未达标，将返工"
                    yield {"type": "progress", "step": "pm_eval", "status": "done", "message": f"PM 评估: {status_text}"}
                elif evt_type == "pm_report":
                    yield {"type": "token", "content": data.get("content", "")}
                    yield {"type": "progress", "step": "expert_team", "status": "done", "message": "专家团执行完成"}

        async def _consume_main():
            """主流: messages 通道获取 LLM token + reasoning"""
            async for event in stream:
                method = event.get("method", "")
                params = event.get("params", {})
                data = params.get("data", {}) if isinstance(params, dict) else {}

                if method == "messages":
                    if not isinstance(data, (list, tuple)) or len(data) < 2:
                        continue
                    msg_chunk = data[0]

                    # AIMessageChunk: token + reasoning
                    if hasattr(msg_chunk, "content") and hasattr(msg_chunk, "type"):
                        if getattr(msg_chunk, "type", "") == "AIMessageChunk":
                            if msg_chunk.content:
                                token_text = msg_chunk.content if isinstance(msg_chunk.content, str) else str(msg_chunk.content)
                                yield {"type": "token", "content": token_text}
                            # reasoning from additional_kwargs
                            _ak = getattr(msg_chunk, "additional_kwargs", None)
                            if _ak and _ak.get("reasoning_content_delta"):
                                yield {"type": "thinking", "content": _ak["reasoning_content_delta"]}

                elif method == "custom" and not _HAS_STREAM_TRANSFORMER:
                    if isinstance(data, dict):
                        yield {"type": "progress", **data}

        # asyncio.merge 并发消费两路流
        _SENTINEL = object()
        _q: asyncio.Queue = asyncio.Queue(maxsize=500)

        async def _drain(aiter_fn, tag):
            try:
                async for item in aiter_fn():
                    await _q.put(item)
            except Exception as e:
                logger.warning(f"[expert_team] {tag} 消费异常: {e}")
            finally:
                await _q.put(_SENTINEL)

        n_consumers = 2 if custom_iter else 1
        tasks = [asyncio.create_task(_drain(_consume_main, "main"))]
        if custom_iter:
            tasks.append(asyncio.create_task(_drain(_consume_custom, "custom")))

        done_count = 0
        while done_count < n_consumers:
            item = await _q.get()
            if item is _SENTINEL:
                done_count += 1
                continue
            yield item

        for t in tasks:
            if not t.done():
                t.cancel()

        elapsed = int((time.time() - t0) * 1000)
        yield {"type": "done", "tools_used": [], "duration_ms": elapsed}

    except Exception as e:
        logger.error(f"专家团执行失败: {e}", exc_info=True)
        yield {"type": "error", "message": f"专家团执行失败: {e}"}
