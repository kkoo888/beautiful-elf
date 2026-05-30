"""统一响应格式 — 符合阿里巴巴 API 规范"""
from typing import Any, Optional, List
from pydantic import BaseModel
import uuid


class ApiResponse(BaseModel):
    """统一 API 响应"""
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: Any = None
    user_tip: str = ""
    request_id: str = ""


class PageResponse(BaseModel):
    """分页响应（继承 ApiResponse，增加 meta）"""
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: Any = None
    meta: dict = {}
    user_tip: str = ""
    request_id: str = ""


def ok(data: Any = None, message: str = "操作成功") -> dict:
    """成功响应"""
    return {"code": "SUCCESS", "message": message, "data": data}


def ok_page(
    data: Any, total: int, page: int = 1, page_size: int = 20
) -> dict:
    """分页成功响应"""
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
        },
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
        "user_tip": user_tip,
        "data": None,
        "request_id": request_id or str(uuid.uuid4()),
    }


# 兼容旧代码的别名，后续删除
success = ok
page_success = ok_page
