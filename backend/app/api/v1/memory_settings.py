"""记忆设置 API — 管理记忆模块的模型配置"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repository.memory_setting_repo import MemorySettingRepository
from app.services.llm_provider_service import LLMProviderService
from app.schemas.response import ApiResult

router = APIRouter()

_repo = MemorySettingRepository()
_provider_service = LLMProviderService()

MEMORY_TASK_MODEL_KEY = "memory_task_model"


class UpdateModelRequest(BaseModel):
    provider_id: int = Field(alias="providerId")
    model_name: str = Field(alias="modelName")


@router.get("/models", response_model=ApiResult)
async def list_available_models(
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取所有启用供应商下的启用模型列表"""
    providers = await _provider_service.list_enabled_providers(db)
    models = []
    for p in providers:
        for m in p.models:
            if m.is_enabled == 1:
                models.append({
                    "providerName": p.name,
                    "providerId": p.id,
                    "modelName": m.model_name,
                    "displayName": m.display_name or m.model_name,
                })
    return ApiResult(data=models)


@router.get("", response_model=ApiResult)
async def get_memory_model_setting(
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """获取当前记忆任务使用的模型"""
    provider_id, model_name = await _repo.get_model_setting(db, MEMORY_TASK_MODEL_KEY)
    return ApiResult(data={"providerId": provider_id, "modelName": model_name})


@router.put("", response_model=ApiResult)
async def update_memory_model_setting(
    data: UpdateModelRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """更新记忆任务使用的模型"""
    setting = await _repo.find_by_key(db, MEMORY_TASK_MODEL_KEY)
    if setting:
        await _repo.update_model_setting(db, MEMORY_TASK_MODEL_KEY, data.provider_id, data.model_name)
    else:
        await _repo.create_with_model(db, MEMORY_TASK_MODEL_KEY, data.provider_id, data.model_name)

    from app.tasks.memory_tasks import invalidate_memory_manager
    invalidate_memory_manager()

    return ApiResult(message="模型已更新", data={"providerId": data.provider_id, "modelName": data.model_name})
