"""Markdown 记忆文件模型 — 存储可读的 Markdown 记忆

设计动机（借鉴 OpenClaw）:
  - Markdown 作为 source of truth，人类可读、可编辑、可 git 管理
  - 与 Qdrant 向量互补：Markdown 管可读性，向量管语义搜索
  - 支持 daily log（memory/YYYY-MM-DD.md）和长期记忆（MEMORY.md）两种类型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Index
from app.models.base import BaseModel


class MarkdownMemory(BaseModel):
    __tablename__ = "markdown_memory"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    title = Column(String(256), nullable=False, comment="文件标题（如 2026-06-06 或 MEMORY）")
    content = Column(Text, nullable=False, comment="Markdown 内容")
    memory_type = Column(String(32), nullable=False, default="daily",
                         comment="类型: daily=每日日志, longterm=长期记忆, curated=精选记忆")
    word_count = Column(Integer, nullable=False, default=0, comment="字数统计")
    qdrant_synced = Column(Integer, nullable=False, default=0,
                           comment="是否已同步到 Qdrant: 0=否 1=是")

    __table_args__ = (
        Index("idx_md_memory_user_type", "user_id", "memory_type"),
        Index("idx_md_memory_title", "title"),
        Index("idx_md_memory_is_deleted", "is_deleted"),
    )
