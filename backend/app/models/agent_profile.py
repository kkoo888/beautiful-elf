"""Agent 行为画像模型 — 借鉴 Hindsight CARA Disposition Profile

设计动机:
  - 每个 Agent 有一个可配置的行为画像
  - 三维性格参数: 怀疑性(S)、字面性(L)、共情性(E)
  - 偏见强度 β: 控制偏好对推理的影响
  - 画像影响 Reflect 时的推理风格和 Opinion 形成

Hindsight 论文参考:
  - Θ = (S, L, E, β)
  - S ∈ {1,...,5}  Skepticism; 1=trusting, 5=skeptical
  - L ∈ {1,...,5}  Literalism; 1=flexible, 5=literal
  - E ∈ {1,...,5}  Empathy;    1=detached, 5=empathetic
  - β ∈ [0,1]      Bias strength
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Float, Index
from app.models.base import BaseModel


class AgentProfile(BaseModel):
    __tablename__ = "agent_profile"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    name = Column(String(64), nullable=False, default="default", comment="画像名称")
    background = Column(Text, nullable=False, default="",
                        comment="Agent 背景描述（第一人称，随交互演化）")

    # 三维性格参数
    skepticism = Column(Integer, nullable=False, default=2,
                        comment="怀疑性 S(1-5): 1=信任, 5=怀疑")
    literalism = Column(Integer, nullable=False, default=3,
                        comment="字面性 L(1-5): 1=灵活, 5=字面")
    empathy = Column(Integer, nullable=False, default=4,
                     comment="共情性 E(1-5): 1=超脱, 5=共情")
    bias_strength = Column(Float, nullable=False, default=0.5,
                           comment="偏见强度 β(0-1): 0=客观, 1=强烈偏好")

    is_active = Column(Integer, nullable=False, default=1,
                       comment="是否为当前活跃画像（同一用户只能有一个 active）")

    __table_args__ = (
        Index("idx_profile_user", "user_id"),
        Index("idx_profile_active", "user_id", "is_active"),
        Index("idx_profile_is_deleted", "is_deleted"),
    )
