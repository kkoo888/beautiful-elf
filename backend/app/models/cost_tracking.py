"""成本追踪模型 — 记录每次 LLM 调用的 token 用量和费用

设计动机:
  - 生产环境必须知道每次调用花了多少钱
  - 支持按用户/会话/模型/日期维度统计
  - 为后续预算控制和告警提供数据基础

P3C 规约:
  - 金额字段用 Decimal（不用 Float/Double，精度损失）
  - 非负数字段加 unsigned
"""
from sqlalchemy import Column, BigInteger, Integer, String, Numeric, Index
from app.models.base import BaseModel


class CostRecord(BaseModel):
    __tablename__ = "cost_record"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    conversation_id = Column(BigInteger, nullable=False, default=0, comment="会话 ID")
    provider_id = Column(Integer, nullable=False, default=0, comment="供应商 ID")
    model_name = Column(String(128), nullable=False, default="", comment="模型名称")
    prompt_tokens = Column(Integer, nullable=False, default=0, comment="输入 token 数")
    completion_tokens = Column(Integer, nullable=False, default=0, comment="输出 token 数")
    total_tokens = Column(Integer, nullable=False, default=0, comment="总 token 数")
    cost_usd = Column(Numeric(12, 6), nullable=False, default=0, comment="费用（美元）")
    cost_cny = Column(Numeric(12, 6), nullable=False, default=0, comment="费用（人民币）")
    call_type = Column(String(32), nullable=False, default="chat",
                       comment="调用类型: chat/evaluator/compression/rewrite/summary")
    duration_ms = Column(Integer, nullable=False, default=0, comment="耗时（毫秒）")
    is_stream = Column(Integer, nullable=False, default=0, comment="是否流式: 0=否 1=是")
    tier = Column(String(4), nullable=False, default="", comment="路由 tier: S/M/L/XL")
    route_class = Column(String(8), nullable=False, default="", comment="路由分类: R0/R1/R2/R3")

    __table_args__ = (
        Index("idx_cost_user", "user_id"),
        Index("idx_cost_conversation", "conversation_id"),
        Index("idx_cost_model", "model_name"),
        Index("idx_cost_call_type", "call_type"),
        Index("idx_cost_is_deleted", "is_deleted"),
        Index("idx_cost_created", "created_at"),
    )
