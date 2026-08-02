"""
验证工具 - 提供常用验证函数和装饰器
减少重复的验证代码
"""
import re
from typing import Any, Optional, Callable
from functools import wraps
from .exceptions import ValidationException


def validate_email(email: str) -> str:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationException("email", "Invalid email format")
    return email.lower()


def validate_string(
    value: str,
    field_name: str,
    min_length: int = 0,
    max_length: int = 1000,
    pattern: Optional[str] = None
) -> str:
    """验证字符串"""
    if not isinstance(value, str):
        raise ValidationException(field_name, "Must be a string")
    
    value = value.strip()
    
    if len(value) < min_length:
        raise ValidationException(field_name, f"Minimum length is {min_length}")
    
    if len(value) > max_length:
        raise ValidationException(field_name, f"Maximum length is {max_length}")
    
    if pattern and not re.match(pattern, value):
        raise ValidationException(field_name, "Invalid format")
    
    return value


def validate_number(
    value: Any,
    field_name: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> float:
    """验证数字"""
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValidationException(field_name, "Must be a number")
    
    if min_value is not None and num < min_value:
        raise ValidationException(field_name, f"Minimum value is {min_value}")
    
    if max_value is not None and num > max_value:
        raise ValidationException(field_name, f"Maximum value is {max_value}")
    
    return num


def validate_enum(value: Any, field_name: str, valid_values: list) -> Any:
    """验证枚举值"""
    if value not in valid_values:
        raise ValidationException(
            field_name,
            f"Must be one of: {', '.join(str(v) for v in valid_values)}"
        )
    return value


def validate_required(value: Any, field_name: str) -> Any:
    """验证必填字段"""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationException(field_name, "This field is required")
    return value


def validate_params(**validators):
    """
    参数验证装饰器
    
    使用示例：
    @validate_params(
        email=validate_email,
        age=lambda x: validate_number(x, "age", min_value=0, max_value=150)
    )
    async def create_user(email: str, age: int):
        pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 验证参数
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    kwargs[param_name] = validator(kwargs[param_name])
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
