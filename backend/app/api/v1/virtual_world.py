"""虚拟世界 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.virtual_world_service import VirtualWorldService
from app.schemas.virtual_world import (
    VirtualWorldSceneCreate, VirtualWorldSceneUpdate, VirtualWorldSceneOut,
    VirtualWorldBlockCreate, VirtualWorldBlockOut,
    VirtualWorldSceneBlockCreate, VirtualWorldSceneBlockOut,
)
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()
_service = VirtualWorldService()


# ── Scene ──

@router.get("/scenes", response_model=ApiPageResult[VirtualWorldSceneOut])
async def list_scenes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[VirtualWorldSceneOut]:
    items, total = await _service.list_scenes(db, page, page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.post("/scenes", response_model=ApiResult[VirtualWorldSceneOut])
async def create_scene(
    data: VirtualWorldSceneCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[VirtualWorldSceneOut]:
    scene = await _service.create_scene(db, data)
    return ApiResult(data=scene)


@router.get("/scenes/{scene_id}", response_model=ApiResult[VirtualWorldSceneOut])
async def get_scene(scene_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[VirtualWorldSceneOut]:
    scene = await _service.get_scene(db, scene_id)
    return ApiResult(data=scene)


@router.put("/scenes/{scene_id}", response_model=ApiResult[VirtualWorldSceneOut])
async def update_scene(
    scene_id: int,
    data: VirtualWorldSceneUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[VirtualWorldSceneOut]:
    scene = await _service.update_scene(db, scene_id, data)
    return ApiResult(data=scene)


@router.delete("/scenes/{scene_id}", response_model=ApiResult)
async def delete_scene(scene_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete_scene(db, scene_id)
    return ApiResult(message="删除成功")


@router.post("/scenes/{scene_id}/activate", response_model=ApiResult[VirtualWorldSceneOut])
async def activate_scene(scene_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[VirtualWorldSceneOut]:
    scene = await _service.activate_scene(db, scene_id)
    return ApiResult(data=scene)


# ── Scene Blocks ──

@router.get("/scenes/{scene_id}/blocks", response_model=ApiResult[list[VirtualWorldSceneBlockOut]])
async def list_scene_blocks(scene_id: int, db: AsyncSession = Depends(get_db)) -> ApiResult[list[VirtualWorldSceneBlockOut]]:
    blocks = await _service.list_scene_blocks(db, scene_id)
    return ApiResult(data=blocks)


@router.post("/scenes/{scene_id}/blocks", response_model=ApiResult[VirtualWorldSceneBlockOut])
async def place_block(
    scene_id: int,
    data: VirtualWorldSceneBlockCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[VirtualWorldSceneBlockOut]:
    block = await _service.place_block(db, scene_id, data)
    return ApiResult(data=block)


@router.delete("/scenes/{scene_id}/blocks/{x}/{y}/{z}", response_model=ApiResult)
async def remove_block(
    scene_id: int, x: int, y: int, z: int,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    await _service.remove_block(db, scene_id, x, y, z)
    return ApiResult(message="方块已移除")


# ── Block Types ──

@router.get("/blocks", response_model=ApiPageResult[VirtualWorldBlockOut])
async def list_blocks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[VirtualWorldBlockOut]:
    offset = (page - 1) * page_size
    items, total = await _service.list_blocks(db, offset=offset, limit=page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.post("/blocks", response_model=ApiResult[VirtualWorldBlockOut])
async def create_block(
    data: VirtualWorldBlockCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResult[VirtualWorldBlockOut]:
    block = await _service.create_block(db, data)
    return ApiResult(data=block)


@router.delete("/blocks/{block_pk}", response_model=ApiResult)
async def delete_block(block_pk: int, db: AsyncSession = Depends(get_db)) -> ApiResult:
    await _service.delete_block(db, block_pk)
    return ApiResult(message="方块类型已删除")
