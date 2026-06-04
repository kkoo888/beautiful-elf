"""技能管理 Service"""
import os
import io
import json
import shutil
import zipfile
from typing import List, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.skill_repo import SkillRepository
from app.schemas.skill import (
    SkillCreate, SkillUpdate, SkillOut, SkillStatsOut,
    ScanResultOut, ScanIssueOut,
)
from app.core.exceptions import RecordNotFoundError, DuplicateEntryError, SkillError
from app.services.skill_scanner import scan_skill_dir

# 技能磁盘存储根目录
SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "skills")


class SkillService:
    def __init__(self):
        self.repo = SkillRepository()

    @staticmethod
    def _serialize(item) -> dict:
        return SkillOut.model_validate(item).model_dump()

    @staticmethod
    def _serialize_stats(stats) -> dict:
        return SkillStatsOut.model_validate(stats).model_dump()

    async def create(self, db: AsyncSession, data: SkillCreate) -> dict:
        existing = await self.repo.find_by_name(db, data.name)
        if existing:
            raise DuplicateEntryError(f"技能名称 '{data.name}' 已存在")
        item = await self.repo.create(db, data.model_dump())
        return self._serialize(item)

    async def get_by_id(self, db: AsyncSession, id: int) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        return self._serialize(item)

    async def list(
        self, db: AsyncSession, page: int = 1, page_size: int = 20,
        enabled: Optional[int] = None,
    ) -> Tuple[list, int]:
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size, enabled=enabled)
        total = await self.repo.count(db, enabled=enabled)
        result = []
        for i in items:
            d = self._serialize(i)
            stats = await self.repo.get_stats(db, i.id)
            d["stats"] = self._serialize_stats(stats) if stats else {
                "callCount": 0, "successCount": 0, "failCount": 0,
                "avgDurationMs": 0, "lastCalledAt": None,
            }
            result.append(d)
        return result, total

    async def update(self, db: AsyncSession, id: int, data: SkillUpdate) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return self._serialize(item)
        updated = await self.repo.update(db, id, update_data)
        return self._serialize(updated)

    async def delete(self, db: AsyncSession, id: int) -> bool:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        return await self.repo.soft_delete(db, id)

    async def enable(self, db: AsyncSession, id: int) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        await self.repo.set_enabled(db, id, 1)
        updated = await self.repo.find_by_id(db, id)
        return self._serialize(updated)

    async def disable(self, db: AsyncSession, id: int) -> dict:
        item = await self.repo.find_by_id(db, id)
        if not item:
            raise RecordNotFoundError("技能不存在")
        await self.repo.set_enabled(db, id, 0)
        updated = await self.repo.find_by_id(db, id)
        return self._serialize(updated)

    async def record_call(
        self, db: AsyncSession, skill_id: int, success: bool, duration_ms: int,
    ) -> dict:
        stats = await self.repo.record_call(db, skill_id, success, duration_ms)
        return self._serialize_stats(stats)

    async def get_stats(self, db: AsyncSession, skill_id: int) -> dict:
        stats = await self.repo.get_stats(db, skill_id)
        if not stats:
            raise RecordNotFoundError("技能统计数据不存在")
        return self._serialize_stats(stats)

    # ─── 安装流程 ─────────────────────────────────

    @staticmethod
    def _extract_zip(zip_bytes: bytes, dest_dir: str) -> int:
        """解压 zip 到目标目录，返回文件数"""
        os.makedirs(dest_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # 安全检查：防止路径穿越
            for info in zf.infolist():
                if info.filename.startswith("/") or ".." in info.filename:
                    raise SkillError(f"zip 包含不安全路径: {info.filename}")
            zf.extractall(dest_dir)
            return len(zf.infolist())

    @staticmethod
    def _serialize_scan_result(scan_result) -> dict:
        return ScanResultOut(
            file_count=scan_result.file_count,
            issues=[
                ScanIssueOut(
                    level=i.level, category=i.category, message=i.message,
                    file=i.file, line=i.line, snippet=i.snippet,
                )
                for i in scan_result.issues
            ],
            summary=scan_result.summary,
            verdict=scan_result.verdict,
        ).model_dump()

    async def install_from_zip(
        self, db: AsyncSession, zip_bytes: bytes,
        name: str, display_name: str, description: str,
        version: str, source: str,
        trigger_words: list[str], dependencies: list[str],
    ) -> dict:
        """安装技能：解压 → 扫描 → 通过则存 DB，否则返回扫描报告"""
        # 检查名称是否已存在
        existing = await self.repo.find_by_name(db, name)
        if existing:
            raise DuplicateEntryError(f"技能名称 '{name}' 已存在")

        # 解压到磁盘
        skill_dir = os.path.join(SKILLS_DIR, name)
        try:
            self._extract_zip(zip_bytes, skill_dir)
        except SkillError:
            raise
        except Exception as e:
            raise SkillError(f"解压失败: {e}")

        # 安全扫描
        scan_result = scan_skill_dir(skill_dir)

        # 构造 config（存扫描结果，不存文件内容）
        config = {
            "scanResult": self._serialize_scan_result(scan_result),
            "installPath": skill_dir,
        }

        if scan_result.verdict == "danger":
            # 扫描不通过，清理磁盘，返回扫描报告让前端展示
            shutil.rmtree(skill_dir, ignore_errors=True)
            return {
                "installed": False,
                "scanResult": config["scanResult"],
                "name": name,
                "displayName": display_name,
                "description": description,
                "version": version,
                "source": source,
                "triggerWords": trigger_words,
                "dependencies": dependencies,
            }

        # 扫描通过（safe 或 caution），直接安装
        create_data = SkillCreate(
            name=name, display_name=display_name, description=description,
            version=version, source=skill_dir,
            trigger_words=trigger_words, dependencies=dependencies,
            config=config,
        )
        item = await self.repo.create(db, create_data.model_dump())
        result = self._serialize(item)
        result["installed"] = True
        result["scanResult"] = config["scanResult"]
        return result

    async def confirm_install(
        self, db: AsyncSession, name: str,
        display_name: str, description: str,
        version: str, source: str,
        trigger_words: list[str], dependencies: list[str],
        zip_bytes: bytes,
    ) -> dict:
        """用户确认忽略风险后强制安装"""
        existing = await self.repo.find_by_name(db, name)
        if existing:
            raise DuplicateEntryError(f"技能名称 '{name}' 已存在")

        # 解压到磁盘
        skill_dir = os.path.join(SKILLS_DIR, name)
        try:
            self._extract_zip(zip_bytes, skill_dir)
        except SkillError:
            raise
        except Exception as e:
            raise SkillError(f"解压失败: {e}")

        # 重新扫描（记录用）
        scan_result = scan_skill_dir(skill_dir)
        config = {
            "scanResult": self._serialize_scan_result(scan_result),
            "installPath": skill_dir,
            "userConfirmed": True,
        }

        create_data = SkillCreate(
            name=name, display_name=display_name, description=description,
            version=version, source=skill_dir,
            trigger_words=trigger_words, dependencies=dependencies,
            config=config,
        )
        item = await self.repo.create(db, create_data.model_dump())
        result = self._serialize(item)
        result["installed"] = True
        result["scanResult"] = config["scanResult"]
        return result

    @staticmethod
    def cleanup_skill_dir(name: str) -> bool:
        """清理已解压的技能目录（取消安装时调用）"""
        skill_dir = os.path.join(SKILLS_DIR, name)
        if os.path.exists(skill_dir):
            shutil.rmtree(skill_dir, ignore_errors=True)
            return True
        return False
