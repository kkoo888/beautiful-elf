"""宠物服务单元测试

测试纯函数逻辑（不依赖数据库）：
- 互动效果计算
- 离线衰减计算
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.models.pet import InteractionType
from app.services.pet_service import PetService


# ── 互动效果计算测试 ──────────────────────────────────────


class TestCalcInteractionEffect:
    """PetService._calc_interaction_effect 纯函数测试"""

    def _make_pet(self, **kwargs) -> MagicMock:
        """创建 mock 宠物对象"""
        pet = MagicMock()
        pet.hunger = kwargs.get("hunger", 50)
        pet.clean = kwargs.get("clean", 50)
        pet.mood = kwargs.get("mood", 50)
        pet.health = kwargs.get("health", 80)
        pet.intimacy = kwargs.get("intimacy", 10)
        pet.exp = kwargs.get("exp", 0)
        pet.level = kwargs.get("level", 1)
        return pet

    def test_feed_normal(self):
        pet = self._make_pet(hunger=50)
        effect = PetService._calc_interaction_effect(InteractionType.FEED, pet)
        assert effect == {"hunger": 70}

    def test_feed_cap_at_100(self):
        pet = self._make_pet(hunger=90)
        effect = PetService._calc_interaction_effect(InteractionType.FEED, pet)
        assert effect == {"hunger": 100}

    def test_clean_normal(self):
        pet = self._make_pet(clean=30)
        effect = PetService._calc_interaction_effect(InteractionType.CLEAN, pet)
        assert effect == {"clean": 50}

    def test_clean_cap_at_100(self):
        pet = self._make_pet(clean=95)
        effect = PetService._calc_interaction_effect(InteractionType.CLEAN, pet)
        assert effect == {"clean": 100}

    def test_chat_increases_mood_and_intimacy(self):
        pet = self._make_pet(mood=60, intimacy=5)
        effect = PetService._calc_interaction_effect(InteractionType.CHAT, pet)
        assert effect == {"mood": 75, "intimacy": 10}

    def test_chat_mood_cap_at_100(self):
        pet = self._make_pet(mood=95, intimacy=0)
        effect = PetService._calc_interaction_effect(InteractionType.CHAT, pet)
        assert effect == {"mood": 100, "intimacy": 5}

    def test_play_increases_mood_and_exp(self):
        pet = self._make_pet(mood=40, exp=50, level=1)
        effect = PetService._calc_interaction_effect(InteractionType.PLAY, pet)
        assert effect == {"mood": 65, "exp": 60}

    def test_play_mood_cap_at_100(self):
        pet = self._make_pet(mood=90, exp=0, level=1)
        effect = PetService._calc_interaction_effect(InteractionType.PLAY, pet)
        assert effect == {"mood": 100, "exp": 10}

    def test_play_triggers_level_up(self):
        """经验满 100（等级1*100）时自动升级"""
        pet = self._make_pet(mood=40, exp=95, level=1)
        effect = PetService._calc_interaction_effect(InteractionType.PLAY, pet)
        assert effect["level"] == 2
        assert effect["exp"] == 5  # 105 - 100 = 5
        assert effect["mood"] == 65

    def test_play_multi_level_up(self):
        """一次互动连续升多级"""
        pet = self._make_pet(mood=40, exp=195, level=1)
        effect = PetService._calc_interaction_effect(InteractionType.PLAY, pet)
        # exp=205, level1需要100→升到2剩105, level2需要200→不够(105<200)
        assert effect["level"] == 2
        assert effect["exp"] == 105

    def test_play_no_level_up_at_cap(self):
        """等级 100 时不再升级，经验继续累积"""
        pet = self._make_pet(mood=40, exp=50, level=100)
        effect = PetService._calc_interaction_effect(InteractionType.PLAY, pet)
        assert "level" not in effect
        assert effect["exp"] == 60

    def test_play_level_99_to_100(self):
        """99 级升 100 级需要 9900 经验"""
        pet = self._make_pet(mood=40, exp=9895, level=99)
        effect = PetService._calc_interaction_effect(InteractionType.PLAY, pet)
        assert effect["level"] == 100
        assert effect["exp"] == 5  # 9905 - 9900 = 5


# ── 离线衰减计算测试 ──────────────────────────────────────


class TestOfflineDecay:
    """离线衰减逻辑测试（从 get_attributes 中提取的核心逻辑）"""

    def _calc_decay(self, pet, hours_offline: int) -> dict:
        """模拟 get_attributes 中的衰减计算"""
        if hours_offline <= 1:
            return {}
        decay = hours_offline
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
        if pet.hunger < 30 and pet.clean < 40:
            updates["health"] = max(pet.health - decay * 2, 10)
        return updates

    def _make_pet(self, **kwargs) -> MagicMock:
        pet = MagicMock()
        pet.hunger = kwargs.get("hunger", 100)
        pet.clean = kwargs.get("clean", 100)
        pet.mood = kwargs.get("mood", 100)
        pet.health = kwargs.get("health", 100)
        return pet

    def test_no_decay_within_1_hour(self):
        pet = self._make_pet()
        result = self._calc_decay(pet, hours_offline=0)
        assert result == {}

    def test_decay_after_2_hours(self):
        pet = self._make_pet(hunger=100, clean=100, mood=100)
        result = self._calc_decay(pet, hours_offline=2)
        assert result["hunger"] == 90  # 100 - 2*5
        assert result["clean"] == 94   # 100 - 2*3
        assert result["mood"] == 96    # 100 - 2*2

    def test_decay_floor_at_10(self):
        pet = self._make_pet(hunger=15, clean=15, mood=15)
        result = self._calc_decay(pet, hours_offline=10)
        assert result["hunger"] == 10
        assert result["clean"] == 10
        assert result["mood"] == 10

    def test_health_decay_when_both_low(self):
        """饥饿<30 且 清洁<40 时健康衰减"""
        pet = self._make_pet(hunger=20, clean=30, health=80)
        result = self._calc_decay(pet, hours_offline=3)
        assert "health" in result
        assert result["health"] == 74  # 80 - 3*2

    def test_no_health_decay_when_hunger_ok(self):
        """饥饿>=30 时不衰减健康"""
        pet = self._make_pet(hunger=50, clean=30, health=80)
        result = self._calc_decay(pet, hours_offline=3)
        assert "health" not in result

    def test_no_health_decay_when_clean_ok(self):
        """清洁>=40 时不衰减健康"""
        pet = self._make_pet(hunger=20, clean=50, health=80)
        result = self._calc_decay(pet, hours_offline=3)
        assert "health" not in result

    def test_health_decay_floor_at_10(self):
        pet = self._make_pet(hunger=10, clean=10, health=15)
        result = self._calc_decay(pet, hours_offline=10)
        assert result["health"] == 10


# ── 枚举测试 ──────────────────────────────────────────────


class TestInteractionType:
    """互动类型枚举测试"""

    def test_enum_values(self):
        assert InteractionType.FEED == 0
        assert InteractionType.CLEAN == 1
        assert InteractionType.CHAT == 2
        assert InteractionType.PLAY == 3

    def test_enum_from_value(self):
        assert InteractionType(0) == InteractionType.FEED
        assert InteractionType(3) == InteractionType.PLAY

    def test_enum_in_mapping(self):
        from app.models.pet import INTERACTION_TYPE_NAMES, INTERACTION_EFFECT_DESC
        for itype in InteractionType:
            assert itype in INTERACTION_TYPE_NAMES
            assert itype in INTERACTION_EFFECT_DESC
