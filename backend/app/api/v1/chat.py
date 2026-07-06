"""AI 对话 API — 非流式端点

流式对话已全部迁移到 WebSocket (/ws/chat)。
本文件仅保留工具统计、状态历史等辅助端点。

已废弃（前端不再调用）:
  - POST /conversations/{id}/chat — 原 SSE 流式对话
  - POST /conversations/{id}/chat/resume — 原 SSE 审批恢复
"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.agent_service import agent_service
from app.schemas.response import ApiResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


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
