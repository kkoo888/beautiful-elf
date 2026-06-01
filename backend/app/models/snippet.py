"""代码片段模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, UniqueConstraint, Index
from app.models.base import BaseModel


class Snippet(BaseModel):
    __tablename__ = "snippet"

    title = Column(String(256), nullable=False, comment="片段标题")
    content = Column(Text, nullable=False, comment="代码内容")
    language = Column(String(64), default="", comment="编程语言")
    use_count = Column(Integer, nullable=False, default=0, comment="使用次数")

    __table_args__ = (
        Index("idx_snippet_language", "language"),
        Index("idx_snippet_use_count", "use_count"),
        Index("idx_snippet_is_deleted", "is_deleted"),
    )


class SnippetTag(BaseModel):
    __tablename__ = "snippet_tag"

    snippet_id = Column(BigInteger, nullable=False, comment="片段 ID")
    tag = Column(String(64), nullable=False, comment="标签名称")

    __table_args__ = (
        UniqueConstraint("snippet_id", "tag", name="uk_snippet_tag"),
        Index("idx_snippet_tag_tag", "tag"),
    )
