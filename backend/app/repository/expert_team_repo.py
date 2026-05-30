"""专家团工作流 Repository"""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.base import MySQLMapper
from app.models.expert_team import ExpertTeam, ExpertTeamMember, ExpertTeamRun


class ExpertTeamRepository:
    """专家团仓储"""

    def __init__(self):
        self.team_mapper = MySQLMapper(ExpertTeam)
        self.member_mapper = MySQLMapper(ExpertTeamMember)
        self.run_mapper = MySQLMapper(ExpertTeamRun)

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
            filters["enabled"] = enabled
        return await self.team_mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count_teams(
        self, db: AsyncSession, category: Optional[str] = None, enabled: Optional[int] = None,
    ) -> int:
        filters = {}
        if category:
            filters["category"] = category
        if enabled is not None:
            filters["enabled"] = enabled
        return await self.team_mapper.count(db, filters=filters)

    async def create_team(self, db: AsyncSession, data: dict) -> ExpertTeam:
        return await self.team_mapper.create(db, data)

    async def update_team(self, db: AsyncSession, team_id: int, data: dict) -> Optional[ExpertTeam]:
        return await self.team_mapper.update(db, team_id, data)

    async def soft_delete_team(self, db: AsyncSession, team_id: int) -> bool:
        return await self.team_mapper.soft_delete(db, team_id)

    # ─── 专家成员 ───────────────────────────────────────

    async def find_members_by_team(self, db: AsyncSession, team_id: int) -> List[ExpertTeamMember]:
        stmt = (
            select(ExpertTeamMember)
            .where(ExpertTeamMember.team_id == team_id, ExpertTeamMember.deleted == 0)
            .order_by(ExpertTeamMember.sort_order.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_members_by_teams(self, db: AsyncSession, team_ids: List[int]) -> List[ExpertTeamMember]:
        """批量查询多个团队的成员（消除 N+1）"""
        if not team_ids:
            return []
        stmt = (
            select(ExpertTeamMember)
            .where(ExpertTeamMember.team_id.in_(team_ids), ExpertTeamMember.deleted == 0)
            .order_by(ExpertTeamMember.sort_order.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def find_member_by_id(self, db: AsyncSession, member_id: int) -> Optional[ExpertTeamMember]:
        return await self.member_mapper.find_by_id(db, member_id)

    async def create_member(self, db: AsyncSession, data: dict) -> ExpertTeamMember:
        return await self.member_mapper.create(db, data)

    async def update_member(self, db: AsyncSession, member_id: int, data: dict) -> Optional[ExpertTeamMember]:
        return await self.member_mapper.update(db, member_id, data)

    async def soft_delete_member(self, db: AsyncSession, member_id: int) -> bool:
        return await self.member_mapper.soft_delete(db, member_id)

    async def soft_delete_members_by_team(self, db: AsyncSession, team_id: int) -> None:
        """软删除专家团下所有成员"""
        members = await self.find_members_by_team(db, team_id)
        for m in members:
            await self.member_mapper.soft_delete(db, m.id)

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
            filters["status"] = status
        return await self.run_mapper.find_all(db, filters=filters, offset=offset, limit=limit)

    async def count_all_runs(self, db: AsyncSession, status: Optional[int] = None) -> int:
        filters = {}
        if status is not None:
            filters["status"] = status
        return await self.run_mapper.count(db, filters=filters)

    async def create_run(self, db: AsyncSession, data: dict) -> ExpertTeamRun:
        return await self.run_mapper.create(db, data)

    async def update_run(self, db: AsyncSession, run_id: int, data: dict) -> Optional[ExpertTeamRun]:
        return await self.run_mapper.update(db, run_id, data)
