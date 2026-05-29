"""工作流模型"""
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, JSON, Index
from app.models.base import BaseModel


class Workflow(BaseModel):
    __tablename__ = "workflows"

    name = Column(String(256), nullable=False, comment="工作流名称")
    description = Column(String(1024), default="", comment="工作流描述")
    dag_json = Column(JSON, nullable=False, comment="DAG 定义")
    trigger_type = Column(Integer, nullable=False, default=0, comment="触发方式")
    cron_expr = Column(String(64), default="", comment="cron 表达式")
    event_trigger = Column(String(256), default="", comment="事件触发条件")
    enabled = Column(Integer, nullable=False, default=1, comment="是否启用")
    version = Column(Integer, nullable=False, default=1, comment="版本号")

    __table_args__ = (
        Index("idx_workflows_enabled", "deleted", "enabled"),
        Index("idx_workflows_trigger", "trigger_type"),
    )


class WorkflowRun(BaseModel):
    __tablename__ = "workflow_runs"

    workflow_id = Column(BigInteger, nullable=False, comment="工作流 ID")
    status = Column(Integer, nullable=False, default=0, comment="状态")
    trigger_type = Column(Integer, nullable=False, default=0, comment="触发方式")
    input_json = Column(JSON, default=None, comment="输入参数")
    output_json = Column(JSON, default=None, comment="输出结果")
    error_message = Column(String(2048), default="", comment="错误信息")
    started_at = Column(DateTime, default=None, comment="开始时间")
    finished_at = Column(DateTime, default=None, comment="完成时间")
    duration_ms = Column(Integer, default=0, comment="执行耗时")

    __table_args__ = (
        Index("idx_wf_runs_workflow", "workflow_id", "status"),
        Index("idx_wf_runs_status", "status"),
        Index("idx_wf_runs_created", "created_at"),
    )


class WorkflowStepRun(BaseModel):
    __tablename__ = "workflow_step_runs"

    run_id = Column(BigInteger, nullable=False, comment="运行记录 ID")
    step_name = Column(String(128), nullable=False, comment="节点名称")
    step_type = Column(String(64), nullable=False, comment="节点类型")
    status = Column(Integer, nullable=False, default=0, comment="状态")
    input_json = Column(JSON, default=None, comment="输入数据")
    output_json = Column(JSON, default=None, comment="输出数据")
    error_message = Column(String(2048), default="", comment="错误信息")
    started_at = Column(DateTime, default=None, comment="开始时间")
    finished_at = Column(DateTime, default=None, comment="完成时间")
    duration_ms = Column(Integer, default=0, comment="执行耗时")

    __table_args__ = (
        Index("idx_step_runs_run", "run_id", "step_name"),
        Index("idx_step_runs_status", "status"),
    )
