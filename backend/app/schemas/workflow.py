"""工作流 Schema — 统一 CamelModel"""
from typing import List, Optional, Dict, Any
from pydantic import Field
from app.schemas.base import CamelModel


class WorkflowCreate(CamelModel):
    """创建工作流请求"""
    name: str = Field(..., min_length=1, max_length=256, description="工作流名称")
    description: str = Field(default="", max_length=1024, description="工作流描述")
    dag_json: Dict[str, Any] = Field(..., alias="dagJson", description="DAG 定义 (nodes + edges)")
    trigger_type: int = Field(default=0, alias="triggerType", description="触发方式 (0=手动, 1=cron, 2=事件)")
    cron_expr: str = Field(default="", alias="cronExpr", description="cron 表达式")
    event_trigger: str = Field(default="", alias="eventTrigger", description="事件触发条件")


class WorkflowUpdate(CamelModel):
    """更新工作流请求"""
    name: Optional[str] = Field(default=None, max_length=256, description="工作流名称")
    description: Optional[str] = Field(default=None, max_length=1024, description="工作流描述")
    dag_json: Optional[Dict[str, Any]] = Field(default=None, alias="dagJson", description="DAG 定义")
    trigger_type: Optional[int] = Field(default=None, alias="triggerType", description="触发方式")
    cron_expr: Optional[str] = Field(default=None, alias="cronExpr", description="cron 表达式")
    event_trigger: Optional[str] = Field(default=None, alias="eventTrigger", description="事件触发条件")


class WorkflowOut(CamelModel):
    """工作流响应"""
    id: int = Field(..., description="工作流 ID")
    name: str = Field(default="", description="工作流名称")
    description: str = Field(default="", description="工作流描述")
    dag_json: Dict[str, Any] = Field(default_factory=dict, alias="dagJson", description="DAG 定义")
    trigger_type: int = Field(default=0, alias="triggerType", description="触发方式")
    cron_expr: str = Field(default="", alias="cronExpr", description="cron 表达式")
    is_enabled: int = Field(default=1, alias="isEnabled", description="是否启用")
    version: int = Field(default=1, description="版本号")


class WorkflowStepRunOut(CamelModel):
    """工作流步骤运行记录"""
    id: int = Field(..., description="记录 ID")
    run_id: int = Field(..., alias="runId", description="运行记录 ID")
    step_name: str = Field(default="", alias="stepName", description="节点名称")
    step_type: str = Field(default="", alias="stepType", description="节点类型")
    status: int = Field(default=0, description="状态 (0=待运行, 1=运行中, 2=成功, 3=失败)")
    input_json: Optional[Dict[str, Any]] = Field(default=None, alias="inputJson", description="输入数据")
    output_json: Optional[Dict[str, Any]] = Field(default=None, alias="outputJson", description="输出数据")
    error_message: str = Field(default="", alias="errorMessage", description="错误信息")
    duration_ms: int = Field(default=0, alias="durationMs", description="执行耗时")


class WorkflowRunOut(CamelModel):
    """工作流运行记录"""
    id: int = Field(..., description="运行记录 ID")
    workflow_id: int = Field(..., alias="workflowId", description="工作流 ID")
    status: int = Field(default=0, description="状态 (0=待运行, 1=运行中, 2=成功, 3=失败)")
    trigger_type: int = Field(default=0, alias="triggerType", description="触发方式")
    input_json: Optional[Dict[str, Any]] = Field(default=None, alias="inputJson", description="输入参数")
    output_json: Optional[Dict[str, Any]] = Field(default=None, alias="outputJson", description="输出结果")
    error_message: str = Field(default="", alias="errorMessage", description="错误信息")
    duration_ms: int = Field(default=0, alias="durationMs", description="执行耗时")
    steps: List[WorkflowStepRunOut] = Field(default_factory=list, description="步骤运行记录")
