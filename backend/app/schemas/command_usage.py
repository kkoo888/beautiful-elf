"""命令使用统计 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.schemas.base import CamelModel


class CommandUsageOut(CamelModel):
    id: int
    command_id: int
    use_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
