"""专家团工作流 Repository"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.expert_team import (
    ExpertTeam, Expert, TeamExpertBinding, ExpertTeamRun,
    ExpertSkill, ExpertRoleRun,
)


class ExpertTeamRepository:
    """专家团仓储"""

    def __init__(self):
        self.team_mapper = MySQLMapper(ExpertTeam)
        self.expert_mapper = MySQLMapper(Expert)
        self.binding_mapper = MySQLMapper(TeamExpertBinding)
        self.run_mapper = MySQLMapper(ExpertTeamRun)
        self.skill_bind_mapper = MySQLMapper(ExpertSkill)
        self.role_run_mapper = MySQLMapper(ExpertRoleRun)

    # ─── 专家团 ─────────────────────────────────────────

    async def find_team_by_id(self, db: AsyncSession, team_id: int) -> Optional[ExpertTeam]:
        return await self.team_mapper.find_by_id(db, team_id)

    async def find_all_teams(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        category: Optional[str] = None, enabled: Optional[int] = None,
    ) -> List[ExpertTeam]:
        filters = {}
        if category:
            filters["category"] = category
        if enabled is not None:
            filters["is_enabled"] = enabled
        return await self.team_mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count_teams(
        self, db: AsyncSession, category: Optional[str] = None, enabled: Optional[int] = None,
    ) -> int:
        filters = {}
        if category:
            filters["category"] = category
        if enabled is not None:
            filters["is_enabled"] = enabled
        return await self.team_mapper.count(db, filters=filters)

    async def create_team(self, db: AsyncSession, data: dict) -> ExpertTeam:
        return await self.team_mapper.create(db, data)

    async def update_team(self, db: AsyncSession, team_id: int, data: dict) -> Optional[ExpertTeam]:
        return await self.team_mapper.update(db, team_id, data)

    async def soft_delete_team(self, db: AsyncSession, team_id: int) -> bool:
        return await self.team_mapper.soft_delete(db, team_id)

    # ─── 专家（独立实体）────────────────────────────────

    async def find_expert_by_id(self, db: AsyncSession, expert_id: int) -> Optional[Expert]:
        return await self.expert_mapper.find_by_id(db, expert_id)

    async def find_experts_by_ids(self, db: AsyncSession, expert_ids: List[int]) -> List[Expert]:
        """批量查询多个专家"""
        if not expert_ids:
            return []
        stmt = (
            select(Expert)
            .where(Expert.id.in_(expert_ids), Expert.is_deleted == 0)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_all_experts(
        self, db: AsyncSession, offset: int = 0, limit: int = 20,
        enabled: Optional[int] = None,
    ) -> List[Expert]:
        filters = {}
        if enabled is not None:
            filters["is_enabled"] = enabled
        return await self.expert_mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count_experts(self, db: AsyncSession, enabled: Optional[int] = None) -> int:
        filters = {}
        if enabled is not None:
            filters["is_enabled"] = enabled
        return await self.expert_mapper.count(db, filters=filters)

    async def create_expert(self, db: AsyncSession, data: dict) -> Expert:
        return await self.expert_mapper.create(db, data)

    async def update_expert(self, db: AsyncSession, expert_id: int, data: dict) -> Optional[Expert]:
        return await self.expert_mapper.update(db, expert_id, data)

    async def soft_delete_expert(self, db: AsyncSession, expert_id: int) -> bool:
        return await self.expert_mapper.soft_delete(db, expert_id)

    # ─── 专家团-专家绑定 ─────────────────────────────────

    async def find_bindings_by_team(self, db: AsyncSession, team_id: int) -> List[TeamExpertBinding]:
        """查询团队的所有绑定关系"""
        stmt = (
            select(TeamExpertBinding)
            .where(TeamExpertBinding.team_id == team_id, TeamExpertBinding.is_deleted == 0)
            .order_by(TeamExpertBinding.sort_order.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_experts_by_team(self, db: AsyncSession, team_id: int) -> List[Expert]:
        """查询团队绑定的所有专家（通过 binding 表）"""
        stmt = (
            select(Expert)
            .join(TeamExpertBinding, Expert.id == TeamExpertBinding.expert_id)
            .where(
                TeamExpertBinding.team_id == team_id,
                TeamExpertBinding.is_deleted == 0,
                TeamExpertBinding.is_enabled == 1,
                Expert.is_deleted == 0,
            )
            .order_by(TeamExpertBinding.sort_order.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_binding(self, db: AsyncSession, team_id: int, expert_id: int) -> Optional[TeamExpertBinding]:
        """查询特定绑定关系"""
        stmt = select(TeamExpertBinding).where(
            TeamExpertBinding.team_id == team_id,
            TeamExpertBinding.expert_id == expert_id,
            TeamExpertBinding.is_deleted == 0,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_binding(self, db: AsyncSession, data: dict) -> TeamExpertBinding:
        return await self.binding_mapper.create(db, data)

    async def soft_delete_binding(self, db: AsyncSession, binding_id: int) -> bool:
        return await self.binding_mapper.soft_delete(db, binding_id)

    async def soft_delete_bindings_by_team(self, db: AsyncSession, team_id: int) -> None:
        """软删除团队的所有绑定关系"""
        bindings = await self.find_bindings_by_team(db, team_id)
        for b in bindings:
            await self.binding_mapper.soft_delete(db, b.id)

    async def replace_team_experts(self, db: AsyncSession, team_id: int, expert_ids: List[int]) -> None:
        """替换团队的所有专家绑定（先硬删除后创建，避免唯一索引冲突）"""
        from sqlalchemy import delete as sa_delete
        await db.execute(
            sa_delete(TeamExpertBinding).where(TeamExpertBinding.team_id == team_id)
        )
        now = datetime.now()
        for idx, expert_id in enumerate(expert_ids):
            await self.create_binding(db, {
                "team_id": team_id,
                "expert_id": expert_id,
                "sort_order": idx,
                "is_enabled": 1,
                "created_at": now,
                "updated_at": now,
            })

    # ─── 运行记录 ───────────────────────────────────────

    async def find_run_by_id(self, db: AsyncSession, run_id: int) -> Optional[ExpertTeamRun]:
        return await self.run_mapper.find_by_id(db, run_id)

    async def find_runs_by_team(
        self, db: AsyncSession, team_id: int, offset: int = 0, limit: int = 20,
    ) -> List[ExpertTeamRun]:
        return await self.run_mapper.find_all(
            db, filters={"team_id": team_id}, offset=offset, limit=limit,
        )

    async def count_runs_by_team(self, db: AsyncSession, team_id: int) -> int:
        return await self.run_mapper.count(db, filters={"team_id": team_id})

    async def find_all_runs(
        self, db: AsyncSession, offset: int = 0, limit: int = 20, status: Optional[int] = None,
    ) -> List[ExpertTeamRun]:
        filters = {}
        if status is not None:
            filters["run_status"] = status
        return await self.run_mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count_all_runs(self, db: AsyncSession, status: Optional[int] = None) -> int:
        filters = {}
        if status is not None:
            filters["run_status"] = status
        return await self.run_mapper.count(db, filters=filters)

    async def create_run(self, db: AsyncSession, data: dict) -> ExpertTeamRun:
        return await self.run_mapper.create(db, data)

    async def update_run(self, db: AsyncSession, run_id: int, data: dict) -> Optional[ExpertTeamRun]:
        return await self.run_mapper.update(db, run_id, data)

    # ─── 专家技能绑定 ───────────────────────────────────

    async def find_skills_by_expert(self, db: AsyncSession, expert_id: int) -> List[ExpertSkill]:
        """查询专家绑定的所有技能"""
        stmt = (
            select(ExpertSkill)
            .where(ExpertSkill.expert_id == expert_id, ExpertSkill.is_deleted == 0)
            .order_by(ExpertSkill.priority.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_skills_by_experts(self, db: AsyncSession, expert_ids: List[int]) -> List[ExpertSkill]:
        """批量查询多个专家的技能绑定（消除 N+1）"""
        if not expert_ids:
            return []
        stmt = (
            select(ExpertSkill)
            .where(ExpertSkill.expert_id.in_(expert_ids), ExpertSkill.is_deleted == 0)
            .order_by(ExpertSkill.priority.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_skill_bind_by_id(self, db: AsyncSession, bind_id: int) -> Optional[ExpertSkill]:
        return await self.skill_bind_mapper.find_by_id(db, bind_id)

    async def find_skill_bind(self, db: AsyncSession, expert_id: int, skill_id: int) -> Optional[ExpertSkill]:
        """查询特定专家-技能绑定"""
        stmt = select(ExpertSkill).where(
            ExpertSkill.expert_id == expert_id,
            ExpertSkill.skill_id == skill_id,
            ExpertSkill.is_deleted == 0,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_skill_bind(self, db: AsyncSession, data: dict) -> ExpertSkill:
        return await self.skill_bind_mapper.create(db, data)

    async def update_skill_bind(self, db: AsyncSession, bind_id: int, data: dict) -> Optional[ExpertSkill]:
        return await self.skill_bind_mapper.update(db, bind_id, data)

    async def soft_delete_skill_bind(self, db: AsyncSession, bind_id: int) -> bool:
        stmt = delete(ExpertSkill).where(ExpertSkill.id == bind_id)
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount > 0

    # ─── 角色执行记录 ───────────────────────────────────

    async def create_role_run(self, db: AsyncSession, data: dict) -> ExpertRoleRun:
        return await self.role_run_mapper.create(db, data)

    async def update_role_run(self, db: AsyncSession, role_run_id: int, data: dict) -> Optional[ExpertRoleRun]:
        return await self.role_run_mapper.update(db, role_run_id, data)

    async def find_role_runs_by_run(self, db: AsyncSession, run_id: int) -> List[ExpertRoleRun]:
        """查询某次运行的所有角色执行记录"""
        stmt = (
            select(ExpertRoleRun)
            .where(ExpertRoleRun.run_id == run_id, ExpertRoleRun.is_deleted == 0)
            .order_by(ExpertRoleRun.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_role_runs_by_expert(self, db: AsyncSession, expert_id: int, offset: int = 0, limit: int = 20) -> List[ExpertRoleRun]:
        """查询某专家的历史执行记录"""
        stmt = (
            select(ExpertRoleRun)
            .where(ExpertRoleRun.role_id == expert_id, ExpertRoleRun.is_deleted == 0)
            .order_by(ExpertRoleRun.created_at.desc())
            .offset(offset).limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
