"""虚拟世界 Repository"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.mappers.base import MySQLMapper
from app.models.virtual_world import VirtualWorldScene, VirtualWorldBlock, VirtualWorldSceneBlock


class VirtualWorldSceneRepo:
    def __init__(self):
        self.mapper = MySQLMapper(VirtualWorldScene)

    async def find_by_id(self, db: AsyncSession, scene_id: int) -> Optional[VirtualWorldScene]:
        return await self.mapper.find_by_id(db, scene_id)

    async def find_active(self, db: AsyncSession) -> Optional[VirtualWorldScene]:
        return await self.mapper.find_one(db, is_active=1)

    async def find_all(self, db: AsyncSession, offset: int = 0, limit: int = 20) -> List[VirtualWorldScene]:
        return await self.mapper.find_all(db, offset=offset, limit=limit)

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict) -> VirtualWorldScene:
        return await self.mapper.create(db, data)

    async def update(self, db: AsyncSession, scene_id: int, data: dict) -> Optional[VirtualWorldScene]:
        return await self.mapper.update(db, scene_id, data)

    async def soft_delete(self, db: AsyncSession, scene_id: int) -> bool:
        return await self.mapper.soft_delete(db, scene_id)

    async def set_active(self, db: AsyncSession, scene_id: int) -> None:
        """设置指定场景为激活，其他场景取消激活"""
        all_scenes = await self.mapper.find_all(db, offset=0, limit=1000)
        for s in all_scenes:
            if s.id == scene_id and s.is_active != 1:
                await self.mapper.update(db, s.id, {"is_active": 1})
            elif s.id != scene_id and s.is_active == 1:
                await self.mapper.update(db, s.id, {"is_active": 0})


class VirtualWorldBlockRepo:
    def __init__(self):
        self.mapper = MySQLMapper(VirtualWorldBlock)

    async def find_by_id(self, db: AsyncSession, block_id: int) -> Optional[VirtualWorldBlock]:
        return await self.mapper.find_by_id(db, block_id)

    async def find_by_block_id(self, db: AsyncSession, block_id: str) -> Optional[VirtualWorldBlock]:
        return await self.mapper.find_one(db, block_id=block_id)

    async def find_all(self, db: AsyncSession, offset: int = 0, limit: int = 100) -> List[VirtualWorldBlock]:
        return await self.mapper.find_all(db, offset=offset, limit=limit)

    async def count(self, db: AsyncSession) -> int:
        return await self.mapper.count(db)

    async def create(self, db: AsyncSession, data: dict) -> VirtualWorldBlock:
        return await self.mapper.create(db, data)

    async def soft_delete(self, db: AsyncSession, block_id: int) -> bool:
        return await self.mapper.soft_delete(db, block_id)


class VirtualWorldSceneBlockRepo:
    def __init__(self):
        self.mapper = MySQLMapper(VirtualWorldSceneBlock)

    async def find_by_scene(self, db: AsyncSession, scene_id: int) -> List[VirtualWorldSceneBlock]:
        return await self.mapper.find_all(db, filters={"scene_id": scene_id}, offset=0, limit=10000)

    async def find_by_position(self, db: AsyncSession, scene_id: int, x: int, y: int, z: int) -> Optional[VirtualWorldSceneBlock]:
        return await self.mapper.find_one(db, scene_id=scene_id, pos_x=x, pos_y=y, pos_z=z)

    async def create(self, db: AsyncSession, data: dict) -> VirtualWorldSceneBlock:
        return await self.mapper.create(db, data)

    async def soft_delete(self, db: AsyncSession, block_pk: int) -> bool:
        return await self.mapper.soft_delete(db, block_pk)

    async def delete_by_position(self, db: AsyncSession, scene_id: int, x: int, y: int, z: int) -> bool:
        block = await self.find_by_position(db, scene_id, x, y, z)
        if block:
            return await self.mapper.soft_delete(db, block.id)
        return False
