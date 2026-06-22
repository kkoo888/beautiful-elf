"""定时任务控制 API — 查询状态 / 启停"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repository.memory_setting_repo import MemorySettingRepository
from app.schemas.response import ApiResult
from app.tasks.scheduler import get_all_tasks_status, set_task_enabled

router = APIRouter()

_repo = MemorySettingRepository()


class SchedulerToggleRequest(BaseModel):
    enabled: bool


@router.get("", response_model=ApiResult)
async def list_tasks():
    """获取所有定时任务状态"""
    tasks = get_all_tasks_status()
    return ApiResult(data=tasks)


@router.put("/{task_name}/toggle", response_model=ApiResult)
async def toggle_task(
    task_name: str,
    data: SchedulerToggleRequest,
    db: AsyncSession = Depends(get_db),
):
    """启停单个定时任务"""
    ok = set_task_enabled(task_name, data.enabled)
    if not ok:
        return ApiResult(code="SCHEDULER_TASK_NOT_FOUND", message=f"任务 {task_name} 不存在")
    await _repo.upsert_by_key(db, task_name, 1 if data.enabled else 0)
    state = "已启用" if data.enabled else "已暂停"
    return ApiResult(message=state, data={"name": task_name, "enabled": data.enabled})
