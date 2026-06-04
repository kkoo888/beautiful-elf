"""统一响应格式 — ApiResult / ApiPageResult 泛型信封

设计原则：
  - 所有 endpoint 通过 response_model=ApiResult[XxxOut] 声明类型
  - FastAPI 自动将 XxxOut 的 snake_case 字段转为 camelCase
  - Service 层永远用 model_dump()（snake_case），不用关心 camelCase
  - 前端收到的 JSON 格式不变：{"code": "SUCCESS", "data": ...}
"""

from __future__ import annotations
import uuid
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

from app.schemas.base import CamelModel

T = TypeVar("T")


# ── 泛型信封模型 ────────────────────────────────────────────

class ApiResult(CamelModel, Generic[T]):
    """统一 API 响应信封

    用法：
        @router.get("/{id}", response_model=ApiResult[ConversationOut])
        async def get_item(...) -> ApiResult[ConversationOut]:
            item = await service.get(db, id)
            return ApiResult(data=item)
    """
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: Optional[T] = None
    user_tip: str = ""
    request_id: str = ""


class ApiPageResult(CamelModel, Generic[T]):
    """分页响应信封

    用法：
        @router.get("", response_model=ApiPageResult[ConversationOut])
        async def list_items(...) -> ApiPageResult[ConversationOut]:
            items, total = await service.list(db, page, page_size)
            return ApiPageResult(data=items, total=total, page=page, page_size=page_size)
    """
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: List[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    user_tip: str = ""
    request_id: str = ""


# ── 快捷构造函数 ────────────────────────────────────────────

def api_success(
    data: Any = None,
    message: str = "操作成功",
) -> ApiResult:
    """成功响应"""
    return ApiResult(data=data, message=message)


def api_paginated(
    data: list,
    total: int,
    page: int = 1,
    page_size: int = 20,
) -> ApiPageResult:
    """分页成功响应"""
    return ApiPageResult(
        data=data, total=total, page=page, page_size=page_size,
    )


def api_error(
    code: str,
    message: str = "操作失败",
    user_tip: str = "",
    request_id: str = "",
) -> ApiResult:
    """错误响应"""
    return ApiResult(
        code=code,
        message=message,
        user_tip=user_tip,
        request_id=request_id or str(uuid.uuid4()),
    )
