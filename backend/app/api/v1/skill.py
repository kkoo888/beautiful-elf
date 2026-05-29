"""技能管理 API"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.skill_service import SkillService
from app.schemas.skill import SkillCreate, SkillUpdate
from app.schemas.response import success as ok_response, page_success

router = APIRouter()
_service = SkillService()


@router.post("")
async def create_skill(data: SkillCreate, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.create(db, data))


@router.get("/{skill_id}")
async def get_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.get_by_id(db, skill_id))


@router.get("")
async def list_skills(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    enabled: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, enabled=enabled)
    return page_success(items, total, page, page_size)


@router.put("/{skill_id}")
async def update_skill(skill_id: int, data: SkillUpdate, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.update(db, skill_id, data))


@router.delete("/{skill_id}")
async def delete_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, skill_id)
    return ok_response(message="删除成功")


@router.patch("/{skill_id}/enable")
async def enable_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.enable(db, skill_id))


@router.patch("/{skill_id}/disable")
async def disable_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.disable(db, skill_id))


@router.get("/{skill_id}/stats")
async def get_skill_stats(skill_id: int, db: AsyncSession = Depends(get_db)):
    return ok_response(await _service.get_stats(db, skill_id))


@router.post("/{skill_id}/stats/record")
async def record_skill_call(
    skill_id: int,
    success_flag: bool = Query(..., alias="success"),
    duration_ms: int = Query(..., ge=0),
    db: AsyncSession = Depends(get_db),
):
    return ok_response(await _service.record_call(db, skill_id, success_flag, duration_ms))
