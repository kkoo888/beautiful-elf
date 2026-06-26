"""专家团流式执行 — 返回标准事件 dict，SSE/WS 共用

从 chat.py 的 _stream_expert_team 中抽取核心逻辑，
yield dict 事件而不是 SSE 字符串。
"""
import asyncio
import json
import time
import logging
from typing import AsyncIterator, Dict, Any, Optional

logger = logging.getLogger(__name__)


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
        from app.agent.stream_transformer import CustomEventTransformer, _HAS_STREAM_TRANSFORMER

        transformers = [CustomEventTransformer] if _HAS_STREAM_TRANSFORMER else []
        stream = await graph.astream_events(
            initial_state,
            version="v3",
            transformers=transformers,
        )

        # 通过 extensions 消费 custom 事件
        custom_iter = stream.extensions.get("custom_events") if _HAS_STREAM_TRANSFORMER else None
        if custom_iter:
            async for data in custom_iter:
                if isinstance(data, dict):
                    evt_type = data.get("type", "")

                    if evt_type == "pm_plan":
                        yield {"type": "progress", "step": "pm_plan", "status": "done", "message": "PM 任务规划完成", "content": data.get("content", "")}

                    elif evt_type == "expert_start":
                        yield {"type": "progress", "step": f"expert_{data.get('expertName', '')}", "status": "executing", "message": f"{data.get('expertName', '')} 正在分析...", "expertName": data.get("expertName", ""), "expertRole": data.get("expertRole", ""), "avatar": data.get("avatar", ""), "round": data.get("round", 0), "maxRounds": initial_state.get("max_rounds", 3)}

                    elif evt_type == "expert_done":
                        yield {"type": "progress", "step": f"expert_{data.get('expertName', '')}", "status": "done", "message": f"{data.get('expertName', '')} 分析完成", "elapsedMs": data.get("durationMs", 0), "expertName": data.get("expertName", ""), "expertRole": data.get("expertRole", ""), "avatar": data.get("avatar", ""), "round": data.get("round", 0), "maxRounds": initial_state.get("max_rounds", 3)}
                        # 输出专家内容
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
        else:
            # 降级: raw event 解析
            async for event in stream:
                if event.get("method") == "custom":
                    data = event.get("params", {}).get("data", {})
                    if isinstance(data, dict):
                        yield {"type": "progress", **data}

        # 获取最终状态
        elapsed = int((time.time() - t0) * 1000)
        yield {"type": "done", "tools_used": [], "duration_ms": elapsed}

    except Exception as e:
        logger.error(f"专家团执行失败: {e}", exc_info=True)
        yield {"type": "error", "message": f"专家团执行失败: {e}"}
