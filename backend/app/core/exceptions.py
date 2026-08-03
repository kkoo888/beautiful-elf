"""
统一异常处理 - 提供清晰的错误类型和处理机制
"""
from typing import Optional, Any, Dict
from fastapi import HTTPException


class AppException(Exception):
    """
    应用基础异常
    """
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.user_tip = message
        super().__init__(message)


class NotFoundException(AppException):
    """资源未找到"""
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)}
        )


class ValidationException(AppException):
    """验证错误"""
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Validation error: {field} - {message}",
            code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field, "validation_message": message}
        )


class AuthenticationException(AppException):
    """认证错误"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationException(AppException):
    """授权错误"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403
        )


class ConflictException(AppException):
    """冲突错误"""
    def __init__(self, resource: str, message: str):
        super().__init__(
            message=f"Conflict: {resource} - {message}",
            code="CONFLICT",
            status_code=409,
            details={"resource": resource}
        )


class ExternalServiceException(AppException):
    """外部服务错误"""
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error: {service} - {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service}
        )


class RateLimitException(AppException):
    """速率限制"""
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after}
        )


def app_exception_handler(request, exc: AppException):
    """异常处理器"""
    from fastapi.responses import JSONResponse
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


# ── 兼容别名（main.py 和其他模块使用的名称）──
AppError = AppException


class StorageError(AppException):
    """存储操作错误"""
    def __init__(self, message: str = "存储操作失败"):
        super().__init__(message=message, code="STORAGE_ERROR", status_code=500)


class RecordNotFoundError(AppException):
    """记录未找到"""
    def __init__(self, message: str = "记录不存在"):
        super().__init__(message=message, code="NOT_FOUND", status_code=404)


class DuplicateEntryError(AppException):
    """重复记录"""
    def __init__(self, message: str = "记录已存在"):
        super().__init__(message=message, code="DUPLICATE_ENTRY", status_code=409)


class AuthUnauthorizedError(AppException):
    """认证错误"""
    def __init__(self, message: str = "认证失败", user_tip: str = "请先登录"):
        super().__init__(message=message, code="AUTH_UNAUTHORIZED", status_code=401)
        self.user_tip = user_tip


class SkillError(AppException):
    """技能操作错误"""
    def __init__(self, message: str = "技能操作失败"):
        super().__init__(message=message, code="SKILL_ERROR", status_code=400)
