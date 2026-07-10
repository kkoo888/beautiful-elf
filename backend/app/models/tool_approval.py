"""工具审批白名单 — 按命令+路径粒度控制自动放行

设计思路：
  - 每条记录 = 一个 (tool_name, path_pattern, command_pattern) 组合
  - 用户「始终允许」后写入此表
  - 下次同工具+同路径+同命令命中时自动放行，不弹窗
  - 超出工作区的操作一律弹窗，不进白名单
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Index
from app.models.base import BaseModel


class ToolApprovalWhitelist(BaseModel):
    """工具审批白名单"""
    __tablename__ = "tool_approval_whitelist"

    user_id = Column(BigInteger, nullable=False, default=0, comment="用户 ID")
    tool_name = Column(String(128), nullable=False, default="", comment="工具名称: exec_command / write_file / apply_patch")
    path_pattern = Column(String(512), nullable=False, default="", comment="路径模式: 精确路径或前缀 (e.g. /home/work/project)")
    command_pattern = Column(String(1024), nullable=False, default="", comment="命令模式: 精确命令或正则 (e.g. git status)")
    risk_level = Column(String(16), nullable=False, default="low", comment="风险等级: low / medium / high")
    note = Column(Text, nullable=False, default="", comment="用户备注（为什么允许）")
    hit_count = Column(Integer, nullable=False, default=0, comment="命中次数")

    __table_args__ = (
        Index("idx_taw_user_tool", "user_id", "tool_name"),
        Index("idx_taw_user_path", "user_id", "path_pattern"),
        Index("idx_taw_is_deleted", "is_deleted"),
    )
