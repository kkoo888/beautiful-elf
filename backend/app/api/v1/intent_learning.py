"""意图学习 API — 路由层

职责：参数校验 + 调用 service + 返回统一格式响应
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_pagination
from app.services.intent_learning_service import intent_learning_service
from app.schemas.intent_learning import (
    IntentCorrectionOut, IntentCorrectionCreate,
    BehaviorPatternOut,
    SkillSuggestionOut,
)
from app.schemas.skill import SkillOut
from app.schemas.response import ApiResult, ApiPageResult, api_error
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ── 纠正历史 ─────────────────────────────────────────────

@router.get("/corrections", response_model=ApiPageResult[IntentCorrectionOut])
async def list_corrections(
    pagination: PaginationParams = Depends(get_pagination),
    user_id: int = Query(default=0, description="用户 ID 筛选"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[IntentCorrectionOut]:
    """获取纠正历史列表"""
    items, total = await intent_learning_service.list_corrections(
        db, page=pagination.page, page_size=pagination.page_size, user_id=user_id,
    )
    return ApiPageResult(data=items, total=total)


@router.post("/corrections", response_model=ApiResult[IntentCorrectionOut])
async def create_correction(
    data: IntentCorrectionCreate,
    user_id: int = Query(default=0, description="用户 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[IntentCorrectionOut]:
    """创建纠正记录"""
    try:
        item = await intent_learning_service.create_correction(db, data, user_id=user_id)
        return ApiResult(data=item)
    except Exception as e:
        logger.error(f"创建纠正记录失败: {e}", exc_info=True)
        return api_error("INTENT_LEARNING_INTERNAL_ERROR", str(e), "创建失败，请稍后重试")


# ── 行为模式 ─────────────────────────────────────────────

@router.get("/patterns", response_model=ApiPageResult[BehaviorPatternOut])
async def list_patterns(
    pagination: PaginationParams = Depends(get_pagination),
    user_id: int = Query(default=0, description="用户 ID 筛选"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[BehaviorPatternOut]:
    """获取行为模式列表"""
    items, total = await intent_learning_service.list_patterns(
        db, page=pagination.page, page_size=pagination.page_size, user_id=user_id,
    )
    return ApiPageResult(data=items, total=total)


# ── 技能建议 ─────────────────────────────────────────────

@router.get("/suggestions", response_model=ApiPageResult[SkillSuggestionOut])
async def list_suggestions(
    pagination: PaginationParams = Depends(get_pagination),
    user_id: int = Query(default=0, description="用户 ID 筛选"),
    status: int | None = Query(default=None, description="状态筛选: 0=待处理 1=已接受 2=已忽略"),
    db: AsyncSession = Depends(get_db),
) -> ApiPageResult[SkillSuggestionOut]:
    """获取技能建议列表"""
    items, total = await intent_learning_service.list_suggestions(
        db, page=pagination.page, page_size=pagination.page_size,
        user_id=user_id, status=status,
    )
    return ApiPageResult(data=items, total=total)


@router.post("/suggestions/{suggestion_id}/accept", response_model=ApiResult[SkillOut])
async def accept_suggestion(
    suggestion_id: int = Path(..., description="建议 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[SkillOut]:
    """接受建议 → 自动创建技能"""
    try:
        skill = await intent_learning_service.accept_suggestion(db, suggestion_id)
        return ApiResult(data=skill, message="技能创建成功")
    except Exception as e:
        logger.error(f"接受建议失败: {e}", exc_info=True)
        return api_error("INTENT_LEARNING_NOT_FOUND", str(e), "请检查建议 ID")


@router.post("/suggestions/{suggestion_id}/ignore", response_model=ApiResult[SkillSuggestionOut])
async def ignore_suggestion(
    suggestion_id: int = Path(..., description="建议 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult[SkillSuggestionOut]:
    """忽略建议"""
    try:
        item = await intent_learning_service.ignore_suggestion(db, suggestion_id)
        return ApiResult(data=item, message="已忽略")
    except Exception as e:
        logger.error(f"忽略建议失败: {e}", exc_info=True)
        return api_error("INTENT_LEARNING_NOT_FOUND", str(e), "请检查建议 ID")


# ── 行为分析 ─────────────────────────────────────────────

@router.post("/analyze")
async def analyze_behavior(
    user_id: int = Query(default=0, description="用户 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """手动触发行为分析

    Phase 1: SQL 聚合提取高频动作 + 时间规律 + 动作序列
    Phase 2: 启发式规则识别行为模式
    Phase 3: LLM 生成技能建议（仅在发现新模式时）
    """
    try:
        from app.services.behavior_analyzer import behavior_analyzer
        from app.services.llm_provider_service import LLMProviderService
        from app.agent.llm_service import llm_service

        # 获取默认供应商的 LLM（与图片画廊一致）
        llm = None
        try:
            provider_service = LLMProviderService()
            provider = await provider_service.get_default_provider(db)
            if provider:
                model_name = ""
                if provider.models:
                    enabled_models = [m for m in provider.models if m.is_enabled == 1]
                    if enabled_models:
                        model_name = enabled_models[0].model_name
                if model_name:
                    llm = await llm_service.get_chat_llm(
                        db, provider_id=provider.id, model_name=model_name, temperature=0.5,
                    )
        except Exception as e:
            logger.debug(f"[analyze] LLM 获取跳过（降级为纯规则）: {e}")

        result = await behavior_analyzer.analyze(db, user_id=user_id, llm=llm)
        auto_intents = result.get('auto_intents', 0)
        msg = f"分析完成: 发现 {result['patterns_found']} 个模式, {result['patterns_new']} 个新增, {result['suggestions_new']} 个新建议"
        if auto_intents > 0:
            msg += f", 自动创建 {auto_intents} 个意图"
        return ApiResult(data=result, message=msg)
    except Exception as e:
        logger.error(f"行为分析失败: {e}", exc_info=True)
        return api_error("INTENT_LEARNING_ANALYZE_ERROR", str(e), "分析失败，请稍后重试")


@router.post("/patterns/{pattern_id}/create-intent")
async def create_intent_from_pattern(
    pattern_id: int = Path(..., description="模式 ID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResult:
    """从行为模式手动创建意图"""
    try:
        result = await intent_learning_service.create_intent_from_pattern(db, pattern_id)
        if result:
            return ApiResult(data=result, message=f"意图创建成功: {result['intent_name']}")
        return api_error("INTENT_LEARNING_CREATE_FAILED", "创建失败", "请检查模式 ID")
    except Exception as e:
        logger.error(f"从模式创建意图失败: {e}", exc_info=True)
        return api_error("INTENT_LEARNING_NOT_FOUND", str(e), "请检查模式 ID")
