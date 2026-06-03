"""技能管理 API — RESTful 规范"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.skill_service import SkillService
from app.schemas.skill import SkillCreate, SkillUpdate
from app.schemas.response import ok, ok_page, fail

router = APIRouter()
_service = SkillService()


@router.post("")
async def create_skill(data: SkillCreate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.create(db, data))


@router.post("/install")
async def install_skill(
    file: UploadFile = File(...),
    name: str = Form(...),
    display_name: str = Form(default=""),
    description: str = Form(default=""),
    version: str = Form(default="1.0.0"),
    source: str = Form(default="github"),
    trigger_words: str = Form(default=""),
    dependencies: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """安装技能：接收 zip → 解压 → 扫描 → 通过则安装，否则返回扫描报告"""
    zip_bytes = await file.read()
    tw = [w.strip() for w in trigger_words.split(",") if w.strip()] if trigger_words else []
    dep = [d.strip() for d in dependencies.split(",") if d.strip()] if dependencies else []

    result = await _service.install_from_zip(
        db, zip_bytes, name, display_name or name, description,
        version, source, tw, dep,
    )

    if not result.get("installed"):
        return fail(
            code="SKILL_SCAN_WARNING",
            message="技能安全扫描发现问题，请确认后继续",
            user_tip="请检查扫描报告，确认是否忽略风险继续安装",
        ) | {"data": result}

    return ok(result, message="技能安装成功")


@router.post("/confirm")
async def confirm_install(
    file: UploadFile = File(...),
    name: str = Form(...),
    display_name: str = Form(default=""),
    description: str = Form(default=""),
    version: str = Form(default="1.0.0"),
    source: str = Form(default="github"),
    trigger_words: str = Form(default=""),
    dependencies: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    """用户确认忽略风险后强制安装"""
    zip_bytes = await file.read()
    tw = [w.strip() for w in trigger_words.split(",") if w.strip()] if trigger_words else []
    dep = [d.strip() for d in dependencies.split(",") if d.strip()] if dependencies else []

    result = await _service.confirm_install(
        db, name, display_name or name, description,
        version, source, tw, dep, zip_bytes,
    )
    return ok(result, message="技能安装成功（已忽略风险）")


@router.post("/cleanup")
async def cleanup_skill(name: str = Query(...)):
    """取消安装时清理已解压的文件"""
    _service.cleanup_skill_dir(name)
    return ok(message="已清理")


@router.get("/{skill_id}")
async def get_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_by_id(db, skill_id))


@router.get("")
async def list_skills(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    enabled: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items, total = await _service.list(db, page, page_size, enabled=enabled)
    return ok_page(items, total, page, page_size)


@router.put("/{skill_id}")
async def update_skill(skill_id: int, data: SkillUpdate, db: AsyncSession = Depends(get_db)):
    return ok(await _service.update(db, skill_id, data))


@router.delete("/{skill_id}")
async def delete_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    await _service.delete(db, skill_id)
    return ok(message="删除成功")


@router.patch("/{skill_id}/enable")
async def enable_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.enable(db, skill_id))


@router.patch("/{skill_id}/disable")
async def disable_skill(skill_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.disable(db, skill_id))


@router.get("/{skill_id}/stats")
async def get_skill_stats(skill_id: int, db: AsyncSession = Depends(get_db)):
    return ok(await _service.get_stats(db, skill_id))


@router.post("/{skill_id}/stats/record")
async def record_skill_call(
    skill_id: int,
    success_flag: bool = Query(..., alias="success"),
    duration_ms: int = Query(..., ge=0, alias="durationMs"),
    db: AsyncSession = Depends(get_db),
):
    return ok(await _service.record_call(db, skill_id, success_flag, duration_ms))
