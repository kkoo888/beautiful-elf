"""技能管理 Schema"""
from typing import Optional, List, Any
from datetime import datetime
from pydantic import Field
from app.schemas.base import CamelModel


class SkillCreate(CamelModel):
    name: str = Field(..., max_length=128, description="技能名称")
    display_name: str = Field(default="", max_length=256, description="显示名称")
    description: str = Field(default="", max_length=1024, description="技能描述")
    version: str = Field(default="1.0.0", max_length=32, description="版本号")
    source: str = Field(default="", max_length=256, description="来源")
    trigger_words: List[str] = Field(default_factory=list, description="触发词列表")
    dependencies: List[str] = Field(default_factory=list, description="依赖技能列表")
    config: Optional[Any] = Field(default=None, description="技能配置")


class SkillUpdate(CamelModel):
    display_name: Optional[str] = Field(default=None, max_length=256, description="显示名称")
    description: Optional[str] = Field(default=None, max_length=1024, description="技能描述")
    version: Optional[str] = Field(default=None, max_length=32, description="版本号")
    source: Optional[str] = Field(default=None, max_length=256, description="来源")
    trigger_words: Optional[List[str]] = Field(default=None, description="触发词列表")
    dependencies: Optional[List[str]] = Field(default=None, description="依赖技能列表")
    is_enabled: Optional[int] = Field(default=None, description="是否启用: 1=是 0=否")
    config: Optional[Any] = Field(default=None, description="技能配置")


class SkillOut(CamelModel):
    id: int
    name: str
    display_name: str
    description: str
    version: str
    source: str
    trigger_words: Optional[List[str]] = []
    dependencies: Optional[List[str]] = []
    is_enabled: int
    config: Optional[Any]
    created_at: datetime
    updated_at: datetime


class SkillStatsOut(CamelModel):
    id: int
    skill_id: int
    call_count: int
    success_count: int
    fail_count: int
    avg_duration_ms: int
    last_called_at: Optional[datetime]


class SkillInstallResult(CamelModel):
    """技能安装结果（扫描通过时返回）"""
    id: int
    name: str
    display_name: str
    description: str
    version: str
    source: str
    trigger_words: Optional[List[str]] = []
    dependencies: Optional[List[str]] = []
    is_enabled: int
    config: Optional[Any]
    created_at: datetime
    updated_at: datetime


class ScanIssueOut(CamelModel):
    """扫描问题"""
    level: str
    category: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    snippet: Optional[str] = None


class ScanResultOut(CamelModel):
    """扫描结果"""
    file_count: int
    issues: List[ScanIssueOut] = []
    summary: dict = {}
    verdict: str = "safe"


class SkillScanWarning(CamelModel):
    """扫描有问题时的返回"""
    name: str
    display_name: str
    description: str
    version: str
    source: str
    trigger_words: Optional[List[str]] = []
    dependencies: Optional[List[str]] = []
    scan_result: ScanResultOut


class SkillConfirmInput(CamelModel):
    """用户确认强制安装"""
    name: str = Field(..., max_length=128, description="技能名称")
