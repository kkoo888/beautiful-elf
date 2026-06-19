"""Episode Schema — 对话 Episode 响应模型"""
from typing import List, Optional
from pydantic import Field
from app.schemas.base import CamelModel


class EpisodeOut(CamelModel):
    """Episode 响应"""
    id: int = Field(default=0)
    user_id: int = Field(default=0, alias="userId")
    conversation_id: int = Field(default=0, alias="conversationId")
    title: str = Field(default="")
    summary: str = Field(default="")
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    ended_at: Optional[str] = Field(default=None, alias="endedAt")
    message_count: int = Field(default=0, alias="messageCount")
    entity_ids: str = Field(default="", alias="entityIds")
    observation_ids: str = Field(default="", alias="observationIds")
    tags: List[str] = Field(default_factory=list)
    qdrant_point_id: str = Field(default="", alias="qdrantPointId")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class EpisodeSearchResult(CamelModel):
    """Episode 语义检索结果"""
    id: str = Field(default="")
    title: str = Field(default="")
    summary: str = Field(default="")
    score: float = Field(default=0.0)
    conversation_id: int = Field(default=0, alias="conversationId")
    started_at: str = Field(default="", alias="startedAt")
    ended_at: str = Field(default="", alias="endedAt")
    tags: List[str] = Field(default_factory=list)
