"""Ollama 管理 API — 模型列表、连接测试、配置查询"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ollama_service import OllamaClient, get_host, get_chat_model, get_embed_model
from app.schemas.response import ok, fail

router = APIRouter()


@router.get("/models")
async def list_models():
    """获取 Ollama 已安装的模型列表"""
    client = OllamaClient()
    result = await client.health_check()
    if result["status"] != "ok":
        return fail("OLLAMA_UNAVAILABLE", f"Ollama 服务不可用: {result.get('message', '')}")
    return ok({
        "models": result["models"],
        "host": get_host(),
        "chat_model": get_chat_model(),
        "embed_model": get_embed_model(),
    })


@router.get("/test")
async def test_connection():
    """测试 Ollama 连接"""
    client = OllamaClient()
    result = await client.health_check()
    if result["status"] != "ok":
        return fail("OLLAMA_UNAVAILABLE", f"连接失败: {result.get('message', '')}")
    return ok({
        "status": "connected",
        "host": result["host"],
        "models": result["models"],
    })


@router.get("/config")
async def get_ollama_config():
    """获取当前 Ollama 配置"""
    return ok({
        "host": get_host(),
        "chat_model": get_chat_model(),
        "embed_model": get_embed_model(),
    })
