"""命令使用统计 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CommandUsageOut(BaseModel):
    id: int
    command_id: int
    use_count: int
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
