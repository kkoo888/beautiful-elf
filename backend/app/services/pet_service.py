"""宠物属性 Service"""
from typing import List, Tuple
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, RecordNotFoundError
from app.models.pet import InteractionType, INTERACTION_TYPE_NAMES, INTERACTION_EFFECT_DESC
from app.repository.pet_repo import PetRepository
from app.repository.config_repo import ConfigRepository
from app.schemas.pet import PetAttributeUpdate, PetInteractionCreate, PetAttributeOut

# 加载器实际支持的 3D 模型格式（MMDLoader 仅支持 PMX，VMD 是动画格式不算模型）
# 未来加 GLTFLoader/FBXLoader 时再扩展
MODEL_EXTENSIONS = {".pmx"}
# 扫描时额外展示的格式（标记为“不支持加载”，避免用户困惑）
PREVIEW_EXTENSIONS = {".glb", ".gltf", ".fbx", ".obj"}


class PetService:
    def __init__(self):
        self.repo = PetRepository()
        self.config_repo = ConfigRepository()

    async def get_attributes(self, db: AsyncSession) -> PetAttributeOut:
        """获取宠物属性（自动初始化 + 离线衰减）"""
        pet = await self.repo.get_singleton(db)
        if not pet:
            pet = await self.repo.create_singleton(db)

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

        return self._to_out(pet)

    async def update_attributes(self, db: AsyncSession, data: PetAttributeUpdate) -> PetAttributeOut:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            pet = await self.repo.get_singleton(db)
            return self._to_out(pet)
        update_data["last_active_at"] = datetime.now()
        pet = await self.repo.update(db, update_data)
        return self._to_out(pet)

    async def interact(self, db: AsyncSession, data: PetInteractionCreate) -> dict:
        """宠物互动（喂食/清洁/聊天/玩耍）"""
        pet = await self.repo.get_singleton(db)
        if not pet:
            pet = await self.repo.create_singleton(db)

        effect = self._calc_interaction_effect(InteractionType(data.interaction_type), pet)

        updates = {"last_active_at": datetime.now()}
        updates.update(effect)
        pet = await self.repo.update(db, updates)

        await self.repo.create_interaction(db, {
            "pet_attribute_id": pet.id,
            "interaction_type": data.interaction_type,
            "effect_json": effect,
        })

        return {"pet": self._to_out(pet), "effect": effect}

    @staticmethod
    def _calc_interaction_effect(interaction_type: InteractionType, pet) -> dict:
        """计算互动效果（纯函数，便于单测）"""
        if interaction_type == InteractionType.FEED:
            return {"hunger": min(pet.hunger + 20, 100)}
        elif interaction_type == InteractionType.CLEAN:
            return {"clean": min(pet.clean + 20, 100)}
        elif interaction_type == InteractionType.CHAT:
            effect = {"mood": min(pet.mood + 15, 100), "intimacy": pet.intimacy + 5}
            # 健康恢复：饥饿>30 且 清洁>40 时，聊天可恢复健康
            if pet.hunger > 30 and pet.clean > 40:
                effect["health"] = min(pet.health + 5, 100)
            return effect
        elif interaction_type == InteractionType.PLAY:
            new_exp = pet.exp + 10
            new_level = pet.level
            # 升级判定：当前等级 * 100 为升级所需经验，等级上限 100
            while new_exp >= new_level * 100 and new_level < 100:
                new_exp -= new_level * 100
                new_level += 1
            result = {"mood": min(pet.mood + 25, 100), "exp": new_exp}
            if new_level != pet.level:
                result["level"] = new_level
            return result
        return {}

    async def get_interactions(
        self, db: AsyncSession, page: int = 1, page_size: int = 20
    ) -> Tuple[List[dict], int]:
        """查询互动记录（分页）"""
        offset = (page - 1) * page_size
        items = await self.repo.get_interactions(db, offset=offset, limit=page_size)
        total = await self.repo.count_interactions(db)

        result = []
        for item in items:
            itype = item.interaction_type
            result.append({
                "id": item.id,
                "petAttributeId": item.pet_attribute_id,
                "interactionType": itype,
                "interactionTypeName": INTERACTION_TYPE_NAMES.get(itype, "unknown"),
                "effectDesc": INTERACTION_EFFECT_DESC.get(itype, ""),
                "effectJson": item.effect_json,
                "createdAt": str(item.created_at) if item.created_at else None,
            })

        return result, total

    def scan_models(self, dir_path: str) -> dict:
        """扫描目录下的 3D 模型文件（递归两层）"""
        target = Path(dir_path)
        if not target.exists():
            raise AppError(
                code="PET_DIR_NOT_FOUND",
                message=f"目录不存在: {dir_path}",
                status_code=404,
            )
        if not target.is_dir():
            raise AppError(
                code="PET_NOT_A_DIR",
                message=f"不是有效目录: {dir_path}",
                status_code=400,
            )

        all_ext = MODEL_EXTENSIONS | PREVIEW_EXTENSIONS
        models = []

        def _add_file(f: Path, prefix: str = ""):
            if not f.is_file() or f.suffix.lower() not in all_ext:
                return
            ext = f.suffix.lower()
            loadable = ext in MODEL_EXTENSIONS
            display = f"{prefix}{f.name}" if prefix else f.name
            models.append({
                "name": display,
                "path": str(f),
                "size": f.stat().st_size,
                "loadable": loadable,
            })

        for f in sorted(target.iterdir()):
            _add_file(f)

        for sub in sorted(target.iterdir()):
            if sub.is_dir():
                for f in sorted(sub.iterdir()):
                    prefix = f"{sub.name} / " if f.stem != sub.name else ""
                    _add_file(f, prefix)

        return {"dir_path": str(target), "models": models}

    async def switch_model(self, db: AsyncSession, model_path: str) -> dict:
        """切换宠物模型，保存到 pet_settings JSON 中（统一数据源）"""
        p = Path(model_path)
        if not p.exists():
            raise AppError(
                code="PET_MODEL_NOT_FOUND",
                message=f"模型文件不存在: {model_path}",
                status_code=404,
            )

        import json
        existing = await self.config_repo.find_by_key(db, "pet_settings")
        if existing:
            try:
                settings = json.loads(existing.key_value)
            except (json.JSONDecodeError, TypeError):
                settings = {}
            settings["modelPath"] = model_path
            await self.config_repo.update_by_key(db, "pet_settings", {"key_value": json.dumps(settings, ensure_ascii=False)})
        else:
            await self.config_repo.create(db, {
                "settings_key": "pet_settings",
                "key_value": json.dumps({"modelPath": model_path}, ensure_ascii=False),
                "description": "宠物设置（JSON）",
            })

        return {"model_path": model_path}

    @staticmethod
    def _to_out(pet) -> PetAttributeOut:
        """ORM → Pydantic 模型"""
        return PetAttributeOut.model_validate(pet)
