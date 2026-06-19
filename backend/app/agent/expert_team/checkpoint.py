"""专家团执行检查点 — 断点恢复 + 人类介入

核心思想：
  每个关键步骤完成后保存 checkpoint 到 MySQL。
  支持：
  - 断点恢复：从上次中断的步骤继续执行
  - 人类介入：在关键节点暂停等待审核后继续
  - 执行回放：查看每步的输入输出
"""
import json
from typing import Optional, Any
from datetime import datetime
from enum import IntEnum
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class CheckpointStep(IntEnum):
    """检查点步骤"""
    INIT = 0              # 初始化
    PM_PLAN = 1           # PM 分配计划
    DEBATE = 2            # 辩论轮次
    EXPERT_EXECUTING = 3  # 专家执行中
    EXPERT_DONE = 4       # 专家完成
    GUARDRAIL = 5         # 质量校验
    PM_EVAL = 6           # PM 评估
    PM_REPORT = 7         # PM 汇总报告
    COMPLETED = 8         # 完成
    FAILED = 9            # 失败
    PAUSED = 10           # 暂停等待人类审核


class Checkpoint(BaseModel):
    """检查点数据"""
    run_id: int
    step: int
    step_name: str
    data: dict = Field(default_factory=dict)
    created_at: str = ""


class HumanReviewRequest(BaseModel):
    """人类审核请求"""
    run_id: int
    action: str = Field(..., description="approve/reject/modify")
    feedback: str = Field(default="", description="审核意见")
    modifications: dict = Field(default_factory=dict, description="修改内容")


async def save_checkpoint(
    db,
    run_id: int,
    step: int,
    step_name: str,
    data: dict = None,
) -> None:
    """保存检查点到 MySQL expert_team_run 的 checkpoint_json 字段

    如果 checkpoint_json 字段不存在，直接存到 progress_json。
    """
    try:
        from app.repository.expert_team_repo import ExpertTeamRepository
        repo = ExpertTeamRepository()

        checkpoint = {
            "step": step,
            "step_name": step_name,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }

        # 读取现有 checkpoints
        run = await repo.find_run_by_id(db, run_id)
        if not run:
            return

        existing = run.progress_json or []
        if isinstance(existing, str):
            try:
                existing = json.loads(existing)
            except (json.JSONDecodeError, TypeError):
                existing = []

        if not isinstance(existing, list):
            existing = []

        existing.append(checkpoint)

        await repo.update_run(db, run_id, {
            "progress_json": existing,
        })

    except Exception as e:
        logger.warning(f"保存检查点失败（非致命）: {e}")


async def load_latest_checkpoint(
    db,
    run_id: int,
) -> Optional[Checkpoint]:
    """加载最新的检查点"""
    try:
        from app.repository.expert_team_repo import ExpertTeamRepository
        repo = ExpertTeamRepository()

        run = await repo.find_run_by_id(db, run_id)
        if not run:
            return None

        progress = run.progress_json or []
        if isinstance(progress, str):
            try:
                progress = json.loads(progress)
            except (json.JSONDecodeError, TypeError):
                return None

        if not progress:
            return None

        latest = progress[-1]
        return Checkpoint(
            run_id=run_id,
            step=latest.get("step", 0),
            step_name=latest.get("step_name", ""),
            data=latest.get("data", {}),
            created_at=latest.get("timestamp", ""),
        )

    except Exception as e:
        logger.warning(f"加载检查点失败: {e}")
        return None


async def request_human_review(
    db,
    run_id: int,
    step_name: str,
    context: str,
    expert_results: list[dict] = None,
) -> None:
    """请求人类审核 — 暂停执行并通知前端

    将 run 状态设为 PAUSED，等待前端调用 resume 端点。
    """
    try:
        from app.repository.expert_team_repo import ExpertTeamRepository
        repo = ExpertTeamRepository()

        await save_checkpoint(db, run_id, CheckpointStep.PAUSED, step_name, {
            "context": context,
            "expert_results": expert_results or [],
            "awaiting_review": True,
        })

        # 更新 run 状态为暂停（status=5 表示暂停等待审核）
        await repo.update_run(db, run_id, {
            "run_status": 5,  # PAUSED
        })

        logger.info(f"专家团 run={run_id} 暂停等待人类审核: {step_name}")

    except Exception as e:
        logger.warning(f"请求人类审核失败: {e}")


async def resume_from_review(
    db,
    run_id: int,
    review: HumanReviewRequest,
) -> bool:
    """从人类审核恢复执行

    Returns:
        True 如果恢复成功
    """
    try:
        from app.repository.expert_team_repo import ExpertTeamRepository
        repo = ExpertTeamRepository()

        # 保存审核结果到 checkpoint
        await save_checkpoint(db, run_id, CheckpointStep.INIT, "human_review", {
            "action": review.action,
            "feedback": review.feedback,
            "modifications": review.modifications,
        })

        # 恢复运行状态
        if review.action == "reject":
            await repo.update_run(db, run_id, {
                "run_status": 4,  # CANCELLED
                "error_message": f"人类拒绝: {review.feedback}",
                "finished_at": datetime.now(),
            })
            return False

        # approve 或 modify → 恢复执行
        await repo.update_run(db, run_id, {
            "run_status": 1,  # RUNNING
        })
        return True

    except Exception as e:
        logger.error(f"恢复执行失败: {e}")
        return False
