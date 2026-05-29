"""宠物属性 API — RESTful 规范"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.pet_service import PetService
from app.schemas.pet import PetAttributeUpdate, PetInteractionCreate, ModelScanRequest, ModelSwitchRequest
from app.schemas.response import ok, ok_page

router = APIRouter()
_service = PetService()


@router.get("")
async def list_pets(db: AsyncSession = Depends(get_db)):
    """获取宠物属性"""
    return ok(await _service.get_attributes(db))


@router.put("")
async def update_pet(data: PetAttributeUpdate, db: AsyncSession = Depends(get_db)):
    """更新宠物属性"""
    return ok(await _service.update_attributes(db, data))


@router.post("/interactions")
async def create_interaction(data: PetInteractionCreate, db: AsyncSession = Depends(get_db)):
    """宠物互动（喂食/清洁/聊天/玩耍）"""
    return ok(await _service.interact(db, data))


@router.post("/models/scan")
async def scan_models(data: ModelScanRequest):
    """扫描目录下的 3D 模型文件"""
    return ok(_service.scan_models(data.dir_path))


@router.post("/models/switch")
async def switch_model(data: ModelSwitchRequest, db: AsyncSession = Depends(get_db)):
    """切换宠物模型"""
    return ok(await _service.switch_model(db, data.model_path))


@router.get("/interactions")
async def list_interactions(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """查询互动记录（分页）"""
    items, total = await _service.get_interactions(db, page, page_size)
    return ok_page(items, total, page, page_size)
