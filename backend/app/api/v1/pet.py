"""宠物属性 API — RESTful 规范"""
import os
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.pet_service import PetService
from app.schemas.pet import PetAttributeUpdate, PetInteractionCreate, PetAttributeOut, ModelScanRequest, ModelSwitchRequest
from app.schemas.response import ApiResult, ApiPageResult

router = APIRouter()

# 截图目录（对齐 image_gallery 的 IMAGE_DIR 模式）
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads", "pet-screenshots")


def _get_service() -> PetService:
    return PetService()


@router.get("", response_model=ApiResult[PetAttributeOut])
async def list_pets(
    db: AsyncSession = Depends(get_db),
    service: PetService = Depends(_get_service),
) -> ApiResult[PetAttributeOut]:
    """获取宠物属性"""
    item = await service.get_attributes(db)
    return ApiResult(data=item)


@router.put("", response_model=ApiResult[PetAttributeOut])
async def update_pet(
    data: PetAttributeUpdate,
    db: AsyncSession = Depends(get_db),
    service: PetService = Depends(_get_service),
) -> ApiResult[PetAttributeOut]:
    """更新宠物属性"""
    item = await service.update_attributes(db, data)
    return ApiResult(data=item)


@router.post("/interactions")
async def create_interaction(
    data: PetInteractionCreate,
    db: AsyncSession = Depends(get_db),
    service: PetService = Depends(_get_service),
):
    """宠物互动（喂食/清洁/聊天/玩耍）"""
    result = await service.interact(db, data)
    return ApiResult(data=result)


@router.post("/models/scan")
async def scan_models(
    data: ModelScanRequest,
    service: PetService = Depends(_get_service),
):
    """扫描目录下的 3D 模型文件"""
    result = service.scan_models(data.dir_path)
    return ApiResult(data=result)


@router.post("/models/switch")
async def switch_model(
    data: ModelSwitchRequest,
    db: AsyncSession = Depends(get_db),
    service: PetService = Depends(_get_service),
):
    """切换宠物模型"""
    result = await service.switch_model(db, data.model_path)
    return ApiResult(data=result)


@router.get("/interactions", response_model=ApiPageResult)
async def list_interactions(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量", alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    service: PetService = Depends(_get_service),
) -> ApiPageResult:
    """查询互动记录（分页）"""
    items, total = await service.get_interactions(db, page, page_size)
    return ApiPageResult(data=items, total=total, page=page, page_size=page_size)


@router.post("/screenshot/upload")
async def upload_screenshot(file: UploadFile = File(...)):
    """上传截图（对齐 image_gallery/upload-temp 模式）"""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    file_name = "latest.png"
    file_path = os.path.join(SCREENSHOT_DIR, file_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return ApiResult(data={"filePath": file_path, "fileName": file_name})


@router.get("/screenshot/latest")
async def serve_screenshot():
    """通过 HTTP 提供最新截图（对齐 image_gallery/files 模式）"""
    file_path = os.path.join(SCREENSHOT_DIR, "latest.png")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="截图不存在")
    resp = FileResponse(file_path, media_type="image/png")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp
