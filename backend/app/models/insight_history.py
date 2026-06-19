"""Insight 演化历史模型 — 审计追踪

设计动机:
  - 每次 Insight 变更（reinforce/weaken/contradict/supersede/merge）记录一条历史
  - 支持演化时间线回溯
  - 支持冲突审计

参考:
  - Hindsight CARA: 背景合并 / 冲突解决
  - GraphMem (2026): temporal precedence 自动替代
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Index
from app.models.base import BaseModel


class MemoryInsightHistory(BaseModel):
    __tablename__ = "memory_insight_history"

    insight_id = Column(BigInteger, nullable=False, comment="关联 Insight ID")
    action = Column(String(16), nullable=False,
                    comment="created/reinforced/weakened/contradicted/superseded/merged")
    old_confidence = Column(Integer, nullable=False, default=0, comment="变更前置信度")
    new_confidence = Column(Integer, nullable=False, default=0, comment="变更后置信度")
    reason = Column(Text, nullable=False, default="", comment="变更原因")
    trigger_obs_ids = Column(String(500), nullable=False, default="",
                              comment="触发的 observation ID（逗号分隔）")

    __table_args__ = (
        Index("idx_history_insight", "insight_id"),
        Index("idx_history_action", "action"),
        Index("idx_history_is_deleted", "is_deleted"),
    )
