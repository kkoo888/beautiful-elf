"""宠物属性 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.pet_service import PetService
from app.schemas.pet import PetAttributeUpdate, PetInteractionCreate
from app.schemas.response import success, page_success

router = APIRouter()
_service = PetService()


@router.get("")
async def get_pet_attributes(db: AsyncSession = Depends(get_db)):
    return success(await _service.get_attributes(db))


@router.put("")
async def update_pet_attributes(data: PetAttributeUpdate, db: AsyncSession = Depends(get_db)):
    return success(await _service.update_attributes(db, data))


@router.post("/interact")
async def pet_interact(data: PetInteractionCreate, db: AsyncSession = Depends(get_db)):
    return success(await _service.interact(db, data))


@router.get("/interactions")
async def list_interactions(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """查询互动记录（分页）"""
    items, total = await _service.get_interactions(db, page, page_size)
    return page_success(items, total, page, page_size)
