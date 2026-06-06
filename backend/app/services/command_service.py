"""命令面板 Service"""
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.command_repo import CommandRepository
from app.schemas.command import CommandCreate, CommandUpdate, CommandOut
from app.core.exceptions import RecordNotFoundError, DuplicateEntryError


class CommandService:
    def __init__(self):
        self.repo = CommandRepository()

    async def create_command(self, db: AsyncSession, data: CommandCreate) -> CommandOut:
        existing = await self.repo.find_by_name(db, data.name)
        if existing:
            raise DuplicateEntryError(f"命令 {data.name} 已存在")
        cmd = await self.repo.create(db, data.model_dump())
        return self._to_out(cmd)

    async def get_command_by_id(self, db: AsyncSession, cmd_id: int) -> CommandOut:
        cmd = await self.repo.find_by_id(db, cmd_id)
        if not cmd:
            raise RecordNotFoundError("命令不存在")
        return self._to_out(cmd)

    async def list_commands(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        module: Optional[str] = None,
    ) -> Tuple[List[CommandOut], int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, module=module)
        total = await self.repo.count(db)
        return [self._to_out(c) for c in items], total

    async def update_command(self, db: AsyncSession, cmd_id: int, data: CommandUpdate) -> CommandOut:
        existing = await self.repo.find_by_id(db, cmd_id)
        if not existing:
            raise RecordNotFoundError("命令不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._to_out(existing)
        cmd = await self.repo.update(db, cmd_id, update_data)
        return self._to_out(cmd)

    async def delete_command(self, db: AsyncSession, cmd_id: int) -> bool:
        existing = await self.repo.find_by_id(db, cmd_id)
        if not existing:
            raise RecordNotFoundError("命令不存在")
        return await self.repo.soft_delete(db, cmd_id)

    async def record_command_usage(self, db: AsyncSession, cmd_id: int) -> dict:
        """记录命令使用"""
        cmd = await self.repo.find_by_id(db, cmd_id)
        if not cmd:
            raise RecordNotFoundError("命令不存在")
        await self.repo.record_usage(db, cmd_id)
        return {"commandId": cmd_id, "recorded": True}

    @staticmethod
    def _to_out(cmd) -> CommandOut:
        """ORM → Pydantic 模型"""
        return CommandOut.model_validate(cmd)
