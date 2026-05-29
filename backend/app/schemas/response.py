"""统一响应格式"""
from typing import Any, Optional, List
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一 API 响应"""
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: Any = None
    request_id: str = ""


class PageResponse(BaseModel):
    """分页响应"""
    code: str = "SUCCESS"
    message: str = "操作成功"
    data: Any = None
    total: int = 0
    page: int = 1
    page_size: int = 20
    request_id: str = ""


def success(data: Any = None, message: str = "操作成功") -> dict:
    return {"code": "SUCCESS", "message": message, "data": data}


def page_success(
    data: Any, total: int, page: int = 1, page_size: int = 20
) -> dict:
    return {
        "code": "SUCCESS",
        "message": "操作成功",
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
