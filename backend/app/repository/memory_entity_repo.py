"""实体记忆 Repository — 按名称/别名匹配 + 图遍历邻居查询"""
from typing import List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory_entity import MemoryEntity
from app.models.memory_entity_relation import MemoryEntityRelation


class MemoryEntityRepository:
    """实体记忆 Repository"""

    async def find_by_names(
        self, db: AsyncSession, names: List[str], user_id: int = 0,
    ) -> List[MemoryEntity]:
        """按名称或别名模糊匹配实体

        对每个 name，检查 name 精确匹配 OR aliases 包含该 name（逗号分隔）。
        """
        if not names:
            return []

        or_conditions = []
        for name in names:
            lower_name = name.lower().strip()
            if not lower_name or len(lower_name) < 2:
                continue
            # 精确匹配 name
            or_conditions.append(MemoryEntity.name == name)
            # 别名包含（处理逗号分隔: "name," / ",name" / ",name,"）
            # v5.1 fix: 转义 SQL LIKE 通配符
            escaped = lower_name.replace("%", r"\%").replace("_", r"\_")
            or_conditions.append(MemoryEntity.aliases.like(f"%{escaped}%", escape="\\"))

        if not or_conditions:
            return []

        stmt = select(MemoryEntity).where(
            MemoryEntity.is_deleted == 0,
            or_(*or_conditions),
        )
        if user_id:
            stmt = stmt.where(MemoryEntity.user_id == user_id)
        stmt = stmt.limit(20)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def expand_neighbors(
        self, db: AsyncSession, entity_ids: List[int], user_id: int = 0, max_hops: int = 1,
    ) -> List[MemoryEntity]:
        """通过关系图扩展，找到所有邻居实体（含起始实体）

        Args:
            entity_ids: 起始实体 ID 列表
            user_id: 用户 ID（0=不限制）
            max_hops: 扩展跳数（默认 1 跳）
        """
        if not entity_ids:
            return []

        all_entity_ids = set(entity_ids)

        current_ids = list(entity_ids)
        for _ in range(max_hops):
            if not current_ids:
                break

            # 查找所有涉及 current_ids 的关系
            # v5.1 fix: 过滤已失效的关系（invalid_at IS NULL = 仍有效）
            stmt = select(MemoryEntityRelation).where(
                MemoryEntityRelation.is_deleted == 0,
                MemoryEntityRelation.invalid_at == None,  # noqa: E711
                or_(
                    MemoryEntityRelation.source_entity_id.in_(current_ids),
                    MemoryEntityRelation.target_entity_id.in_(current_ids),
                ),
            )
            if user_id:
                stmt = stmt.where(MemoryEntityRelation.user_id == user_id)

            result = await db.execute(stmt)
            relations = list(result.scalars().all())

            # 收集新的邻居 ID
            new_ids = set()
            for rel in relations:
                if rel.source_entity_id not in all_entity_ids:
                    new_ids.add(rel.source_entity_id)
                if rel.target_entity_id not in all_entity_ids:
                    new_ids.add(rel.target_entity_id)

            if not new_ids:
                break

            all_entity_ids.update(new_ids)
            current_ids = list(new_ids)

        # 获取所有发现的实体
        stmt = select(MemoryEntity).where(
            MemoryEntity.id.in_(list(all_entity_ids)),
            MemoryEntity.is_deleted == 0,
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
