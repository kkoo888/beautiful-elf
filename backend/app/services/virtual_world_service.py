"""虚拟世界 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repository.virtual_world_repo import (
    VirtualWorldSceneRepo, VirtualWorldBlockRepo, VirtualWorldSceneBlockRepo,
)
from app.schemas.virtual_world import (
    VirtualWorldSceneCreate, VirtualWorldSceneUpdate, VirtualWorldSceneOut,
    VirtualWorldBlockCreate, VirtualWorldBlockOut,
    VirtualWorldSceneBlockCreate, VirtualWorldSceneBlockOut,
)
from app.core.exceptions import RecordNotFoundError


class VirtualWorldService:
    def __init__(self):
        self.scene_repo = VirtualWorldSceneRepo()
        self.block_repo = VirtualWorldBlockRepo()
        self.scene_block_repo = VirtualWorldSceneBlockRepo()

    # ── Scene ──

    @staticmethod
    def _scene_out(s) -> VirtualWorldSceneOut:
        return VirtualWorldSceneOut.model_validate(s)

    async def create_scene(self, db: AsyncSession, data: VirtualWorldSceneCreate) -> VirtualWorldSceneOut:
        scene = await self.scene_repo.create(db, data.model_dump())
        return self._scene_out(scene)

    async def get_scene(self, db: AsyncSession, scene_id: int) -> VirtualWorldSceneOut:
        scene = await self.scene_repo.find_by_id(db, scene_id)
        if not scene:
            raise RecordNotFoundError("场景不存在")
        return self._scene_out(scene)

    async def list_scenes(self, db: AsyncSession, page: int = 1, page_size: int = 20) -> Tuple[List[VirtualWorldSceneOut], int]:
        offset = (page - 1) * page_size
        items = await self.scene_repo.find_all(db, offset=offset, limit=page_size)
        total = await self.scene_repo.count(db)
        return [self._scene_out(i) for i in items], total

    async def update_scene(self, db: AsyncSession, scene_id: int, data: VirtualWorldSceneUpdate) -> VirtualWorldSceneOut:
        scene = await self.scene_repo.find_by_id(db, scene_id)
        if not scene:
            raise RecordNotFoundError("场景不存在")
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            scene = await self.scene_repo.update(db, scene_id, update_data)
        return self._scene_out(scene)

    async def delete_scene(self, db: AsyncSession, scene_id: int) -> None:
        scene = await self.scene_repo.find_by_id(db, scene_id)
        if not scene:
            raise RecordNotFoundError("场景不存在")
        await self.scene_repo.soft_delete(db, scene_id)

    async def activate_scene(self, db: AsyncSession, scene_id: int) -> VirtualWorldSceneOut:
        scene = await self.scene_repo.find_by_id(db, scene_id)
        if not scene:
            raise RecordNotFoundError("场景不存在")
        await self.scene_repo.set_active(db, scene_id)
        return self._scene_out(await self.scene_repo.find_by_id(db, scene_id))

    # ── Block Types ──

    @staticmethod
    def _block_out(b) -> VirtualWorldBlockOut:
        return VirtualWorldBlockOut.model_validate(b)

    async def create_block(self, db: AsyncSession, data: VirtualWorldBlockCreate) -> VirtualWorldBlockOut:
        block = await self.block_repo.create(db, data.model_dump())
        return self._block_out(block)

    async def list_blocks(self, db: AsyncSession, offset: int = 0, limit: int = 100) -> Tuple[List[VirtualWorldBlockOut], int]:
        items = await self.block_repo.find_all(db, offset=offset, limit=limit)
        total = await self.block_repo.count(db)
        return [self._block_out(i) for i in items], total

    async def delete_block(self, db: AsyncSession, block_pk: int) -> None:
        block = await self.block_repo.find_by_id(db, block_pk)
        if not block:
            raise RecordNotFoundError("方块类型不存在")
        await self.block_repo.soft_delete(db, block_pk)

    # ── Scene Blocks ──

    @staticmethod
    def _scene_block_out(b) -> VirtualWorldSceneBlockOut:
        return VirtualWorldSceneBlockOut.model_validate(b)

    async def place_block(self, db: AsyncSession, scene_id: int, data: VirtualWorldSceneBlockCreate) -> VirtualWorldSceneBlockOut:
        scene = await self.scene_repo.find_by_id(db, scene_id)
        if not scene:
            raise RecordNotFoundError("场景不存在")
        # 检查位置是否已被占用
        existing = await self.scene_block_repo.find_by_position(db, scene_id, data.pos_x, data.pos_y, data.pos_z)
        if existing:
            # 移除旧方块
            await self.scene_block_repo.soft_delete(db, existing.id)
        block = await self.scene_block_repo.create(db, {**data.model_dump(), "scene_id": scene_id})
        return self._scene_block_out(block)

    async def remove_block(self, db: AsyncSession, scene_id: int, x: int, y: int, z: int) -> None:
        removed = await self.scene_block_repo.delete_by_position(db, scene_id, x, y, z)
        if not removed:
            raise RecordNotFoundError("该位置无方块")

    async def list_scene_blocks(self, db: AsyncSession, scene_id: int) -> List[VirtualWorldSceneBlockOut]:
        items = await self.scene_block_repo.find_by_scene(db, scene_id)
        return [self._scene_block_out(i) for i in items]
