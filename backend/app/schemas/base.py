"""统一 CamelModel 基类 — snake_case → camelCase 自动映射"""
import re
from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    """snake_case → camelCase"""
    return re.sub(r'_([a-zA-Z])', lambda m: m.group(1).upper(), string)


class CamelModel(BaseModel):
    """所有 API Schema 继承此基类，自动将 snake_case 字段映射为 camelCase 输出"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
