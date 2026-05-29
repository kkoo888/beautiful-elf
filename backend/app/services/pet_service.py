"""宠物属性 Service"""
from typing import List, Tuple
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.pet_repo import PetRepository
from app.schemas.pet import PetAttributeUpdate, PetInteractionCreate
from app.core.exceptions import RecordNotFoundError

# 互动类型映射
INTERACTION_TYPE_NAMES = {
    0: "feed",
    1: "clean",
    2: "chat",
    3: "play",
}

INTERACTION_EFFECT_DESC = {
    0: "饥饿度 +20",
    1: "清洁度 +20",
    2: "心情 +15, 亲密 +5",
    3: "心情 +25, 经验 +10",
}


class PetService:
    def __init__(self):
        self.repo = PetRepository()

    async def get_attributes(self, db: AsyncSession) -> dict:
        """获取宠物属性（自动初始化）"""
        pet = await self.repo.get_singleton(db)
        if not pet:
            pet = await self.repo.create_singleton(db)

        # 离线衰减计算
        now = datetime.now()
        hours_offline = (now - pet.last_active_at).total_seconds() / 3600
        if hours_offline > 1:
            decay = int(hours_offline)
            updates = {}
            new_hunger = max(pet.hunger - decay * 5, 10)
            new_clean = max(pet.clean - decay * 3, 10)
            new_mood = max(pet.mood - decay * 2, 10)
            if new_hunger != pet.hunger:
                updates["hunger"] = new_hunger
            if new_clean != pet.clean:
                updates["clean"] = new_clean
            if new_mood != pet.mood:
                updates["mood"] = new_mood
            # 健康值：饥饿+清洁双低时联动衰减
            if pet.hunger < 30 and pet.clean < 40:
                updates["health"] = max(pet.health - decay * 2, 10)
            if updates:
                updates["last_active_at"] = now
                pet = await self.repo.update(db, updates)

        return self._to_dict(pet)

    async def update_attributes(self, db: AsyncSession, data: PetAttributeUpdate) -> dict:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            pet = await self.repo.get_singleton(db)
            return self._to_dict(pet)
        update_data["last_active_at"] = datetime.now()
        pet = await self.repo.update(db, update_data)
        return self._to_dict(pet)

    async def interact(self, db: AsyncSession, data: PetInteractionCreate) -> dict:
        """宠物互动（喂食/清洁/聊天/玩耍）"""
        pet = await self.repo.get_singleton(db)
        if not pet:
            pet = await self.repo.create_singleton(db)

        # 计算互动效果
        effect = {}
        if data.interaction_type == 0:  # 喂食
            effect["hunger"] = min(pet.hunger + 20, 100)
        elif data.interaction_type == 1:  # 清洁
            effect["clean"] = min(pet.clean + 20, 100)
        elif data.interaction_type == 2:  # 聊天
            effect["mood"] = min(pet.mood + 15, 100)
            effect["intimacy"] = pet.intimacy + 5
        elif data.interaction_type == 3:  # 玩耍
            effect["mood"] = min(pet.mood + 25, 100)
            effect["exp"] = pet.exp + 10

        # 更新属性
        updates = {"last_active_at": datetime.now()}
        updates.update(effect)
        pet = await self.repo.update(db, updates)

        # 记录互动
        await self.repo.create_interaction(db, {
            "pet_attribute_id": pet.id,
            "interaction_type": data.interaction_type,
            "effect_json": effect,
        })

        return {"pet": self._to_dict(pet), "effect": effect}

    async def get_interactions(
        self, db: AsyncSession, page: int = 1, page_size: int = 20
    ) -> Tuple[List[dict], int]:
        """查询互动记录（分页）"""
        offset = (page - 1) * page_size
        items = await self.repo.get_interactions(db, offset=offset, limit=page_size)
        total = await self.repo.count_interactions(db)

        result = []
        for item in items:
            result.append({
                "id": item.id,
                "pet_attribute_id": item.pet_attribute_id,
                "interaction_type": item.interaction_type,
                "interaction_type_name": INTERACTION_TYPE_NAMES.get(item.interaction_type, "unknown"),
                "effect_desc": INTERACTION_EFFECT_DESC.get(item.interaction_type, ""),
                "effect_json": item.effect_json,
                "created_at": str(item.created_at) if item.created_at else None,
            })

        return result, total

    # 支持的 3D 模型格式
    MODEL_EXTENSIONS = {".pmx", ".vmd", ".glb", ".gltf", ".fbx", ".obj"}

    def scan_models(self, dir_path: str) -> dict:
        """扫描目录下的 3D 模型文件（递归两层）
        
        结构示例：
          模型目录/
            初音未来/
              miku.pmx
            雷电将军/
              raiden.pmx
        """
        target = Path(dir_path)
        if not target.exists():
            from app.core.exceptions import AppError
            raise AppError(
                code="PET_DIR_NOT_FOUND",
                message=f"目录不存在: {dir_path}",
                status_code=404,
            )
        if not target.is_dir():
            from app.core.exceptions import AppError
            raise AppError(
                code="PET_NOT_A_DIR",
                message=f"不是有效目录: {dir_path}",
                status_code=400,
            )

        models = []

        # 扫描当前目录的文件
        for f in sorted(target.iterdir()):
            if f.is_file() and f.suffix.lower() in self.MODEL_EXTENSIONS:
                models.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                })

        # 扫描子目录下的文件（第二层）
        for sub in sorted(target.iterdir()):
            if sub.is_dir():
                for f in sorted(sub.iterdir()):
                    if f.is_file() and f.suffix.lower() in self.MODEL_EXTENSIONS:
                        models.append({
                            "name": f"{sub.name} / {f.name}",
                            "path": str(f),
                            "size": f.stat().st_size,
                        })

        return {
            "dir_path": str(target),
            "models": models,
        }

    @staticmethod
    def _to_dict(pet) -> dict:
        return {
            "id": pet.id,
            "hunger": pet.hunger,
            "clean": pet.clean,
            "mood": pet.mood,
            "health": pet.health,
            "intimacy": pet.intimacy,
            "level": pet.level,
            "exp": pet.exp,
            "last_active_at": str(pet.last_active_at) if pet.last_active_at else None,
            "created_at": str(pet.created_at) if pet.created_at else None,
            "updated_at": str(pet.updated_at) if pet.updated_at else None,
        }
