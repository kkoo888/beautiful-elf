"""Seed 脚本 — 新增 Agnes AI 供应商

Agnes AI 官方文档: https://agnes-ai.com/doc/overview
  - Base URL: https://apihub.agnes-ai.com/v1
  - 认证方式: Bearer Token（从 platform.agnes-ai.com 获取 API Key）
  - 协议: 完全兼容 OpenAI SDK
  - 默认模型: agnes-2.0-flash

用法:
  cd backend && python -m scripts.seed_agnes
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import AsyncSessionLocal
from app.repository.llm_provider_repo import LLMProviderRepository
from app.repository.llm_model_repo import LLMModelRepository


AGNES_PROVIDER = {
    "name": "Agnes AI",
    "provider_type": "openai",  # Agnes 兼容 OpenAI 协议
    "base_url": "https://apihub.agnes-ai.com/v1",
    "api_key": "",  # 用户需在设置页面填入自己的 API Key
    "is_enabled": 1,
    "is_default": 0,
    "description": "Agnes AI — 全栈多模态 AI 平台，兼容 OpenAI 协议。注册: platform.agnes-ai.com",
}

AGNES_MODELS = [
    {
        "model_name": "agnes-2.0-flash",
        "display_name": "Agnes 2.0 Flash",
        "context_length": 128000,
        "max_tokens": 4096,
        "temperature": 0.7,
        "capabilities": {"vision": True, "tools": True, "streaming": True},
        "is_enabled": 1,
        "sort_order": 0,
        "remark": "Agnes 旗舰文本模型，支持工具调用和多模态",
    },
]


async def seed():
    provider_repo = LLMProviderRepository()
    model_repo = LLMModelRepository()

    async with AsyncSessionLocal() as db:
        # 检查是否已存在
        existing = await provider_repo.find_all(db, filters={"name": "Agnes AI"})
        if existing:
            print(f"⚠️  Agnes AI 供应商已存在 (id={existing[0].id})，跳过")
            return

        # 创建供应商
        provider = await provider_repo.create(db, AGNES_PROVIDER)
        print(f"✅ Agnes AI 供应商已创建 (id={provider.id})")

        # 创建模型
        for model_data in AGNES_MODELS:
            model_data["provider_id"] = provider.id
            model = await model_repo.create(db, model_data)
            print(f"   📦 模型 {model.display_name} 已创建 (id={model.id})")

        await db.commit()
        print("\n🎉 Agnes AI 供应商初始化完成！")
        print("   请在设置页面填入 API Key: platform.agnes-ai.com")


if __name__ == "__main__":
    asyncio.run(seed())
