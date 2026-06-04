"""Ollama 管理 API — 模型列表、连接测试、配置查询"""
from fastapi import APIRouter

from app.services.ollama_service import OllamaClient, get_host, get_chat_model, get_embed_model
from app.schemas.response import ApiResult

router = APIRouter()


@router.get("/models", response_model=ApiResult)
async def list_models() -> ApiResult:
    """获取 Ollama 已安装的模型列表"""
    client = OllamaClient()
    result = await client.health_check()
    if result["status"] != "ok":
        return ApiResult(code="AI_TIMEOUT", message=f"Ollama 服务不可用: {result.get('message', '')}", user_tip="请检查 Ollama 服务是否启动")
    return ApiResult(data={
        "models": result["models"],
        "host": get_host(),
        "chatModel": get_chat_model(),
        "embedModel": get_embed_model(),
    })


@router.get("/test", response_model=ApiResult)
async def test_connection() -> ApiResult:
    """测试 Ollama 连接"""
    client = OllamaClient()
    result = await client.health_check()
    if result["status"] != "ok":
        return ApiResult(code="AI_TIMEOUT", message=f"连接失败: {result.get('message', '')}", user_tip="请检查 Ollama 服务地址配置")
    return ApiResult(data={
        "status": "connected",
        "host": result["host"],
        "models": result["models"],
    })


@router.get("/config", response_model=ApiResult)
async def get_ollama_config() -> ApiResult:
    """获取当前 Ollama 配置"""
    return ApiResult(data={
        "host": get_host(),
        "chatModel": get_chat_model(),
        "embedModel": get_embed_model(),
    })
