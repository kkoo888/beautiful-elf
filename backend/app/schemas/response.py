"""统一响应格式 — 符合阿里巴巴 API 规范

所有 Service 层用 model_dump()（snake_case），ok/ok_page 自动转 camelCase。
"""
import re
from typing import Any, Optional, List
from pydantic import BaseModel
import uuid

from app.schemas.base import CamelModel


def _to_camel(s: str) -> str:
    return re.sub(r'_([a-zA-Z])', lambda m: m.group(1).upper(), s)


def _camelize_keys(obj):
    """递归将 dict 的 key 从 snake_case 转为 camelCase"""
    if isinstance(obj, dict):
        return {_to_camel(k): _camelize_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_camelize_keys(item) for item in obj]
    return obj


class ApiResponse(CamelModel):
    """统一 API 响应"""
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: Any = None
    user_tip: str = ""
    request_id: str = ""


class PageResponse(CamelModel):
    """分页响应（继承 ApiResponse，增加 meta）"""
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: Any = None
    meta: dict = {}
    user_tip: str = ""
    request_id: str = ""


def ok(data: Any = None, message: str = "操作成功") -> dict:
    """成功响应 — 自动将 data 中的 snake_case key 转为 camelCase"""
    return {"code": "SUCCESS", "message": message, "data": _camelize_keys(data)}


def ok_page(
    data: Any, total: int, page: int = 1, page_size: int = 20
) -> dict:
    """分页成功响应 — data 和 meta 自动转 camelCase"""
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": _camelize_keys(data),
        "meta": _camelize_keys({
            "total": total,
            "page": page,
            "page_size": page_size,
        }),
    }


def fail(
    code: str,
    message: str = "操作失败",
    user_tip: str = "",
    request_id: str = "",
) -> dict:
    """错误响应"""
    return {
        "code": code,
        "message": message,
        "userTip": user_tip,
        "data": None,
        "requestId": request_id or str(uuid.uuid4()),
    }


# 兼容旧代码的别名，后续删除
success = ok
page_success = ok_page
