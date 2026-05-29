"""宠物属性 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.pet_service import PetService
from app.schemas.pet import PetAttributeUpdate, PetInteractionCreate
from app.schemas.response import success

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
