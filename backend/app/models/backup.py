"""备份模型"""
from sqlalchemy import Column, BigInteger, Integer, String, Index
from app.models.base import BaseModel


class BackupRecord(BaseModel):
    __tablename__ = "backup_record"

    backup_type = Column(Integer, nullable=False, comment="备份类型")
    file_path = Column(String(512), nullable=False, comment="备份文件路径")
    file_size = Column(BigInteger, nullable=False, default=0, comment="文件大小")
    status = Column(Integer, nullable=False, default=0, comment="状态")
    error_message = Column(String(1024), default="", comment="失败原因")

    __table_args__ = (
        Index("idx_backup_record_type", "backup_type"),
        Index("idx_backup_record_status", "status"),
        Index("idx_backup_record_created_at", "created_at"),
    )
