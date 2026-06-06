"""方案 A 迁移脚本: llm_provider.models JSON → llm_model 独立表

执行方式: python -m scripts.migrate_llm_models

功能:
  1. 创建 llm_model 表
  2. 从 llm_provider.models JSON 迁移数据到 llm_model
  3. 迁移完成后可选删除 llm_provider.models 列
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, AsyncSessionLocal
from app.models.llm_model import LLMModel
from app.models.llm_provider import LLMProvider
from sqlalchemy import text, select


async def migrate():
    async with engine.begin() as conn:
        # 1. 创建 llm_model 表（如果不存在）
        await conn.run_sync(LLMModel.metadata.create_all)
        print("✅ llm_model 表已创建/确认存在")

    async with AsyncSessionLocal() as db:
        # 2. 读取所有供应商的 models JSON
        result = await db.execute(
            select(LLMProvider).where(LLMProvider.is_deleted == 0)
        )
        providers = result.scalars().all()

        total_migrated = 0
        for provider in providers:
            # 检查 models 列是否存在（兼容新旧 schema）
            try:
                models_json = getattr(provider, 'models', None) or []
            except Exception:
                print(f"⚠️  供应商 {provider.id}({provider.name}) 无 models 列，跳过")
                continue

            if not models_json:
                continue

            # 检查是否已迁移（避免重复）
            existing = await db.execute(
                select(LLMModel).where(
                    LLMModel.provider_id == provider.id,
                    LLMModel.is_deleted == 0,
                )
            )
            if existing.scalars().first():
                print(f"⏭  供应商 {provider.id}({provider.name}) 已有模型数据，跳过")
                continue

            # 迁移每个模型
            for i, m in enumerate(models_json):
                if isinstance(m, dict):
                    model_name = m.get("id") or m.get("name") or m.get("model_name", "")
                    display_name = m.get("name") or m.get("display_name") or model_name
                    context_length = m.get("contextLength") or m.get("context_length") or 4096
                    caps = {}
                    if m.get("supportsVision") or m.get("supports_vision"):
                        caps["vision"] = True
                    if m.get("supportsTools") or m.get("supports_tools"):
                        caps["tools"] = True
                elif isinstance(m, str):
                    model_name = m
                    display_name = m
                    context_length = 4096
                    caps = {}
                else:
                    continue

                llm_model = LLMModel(
                    provider_id=provider.id,
                    model_name=model_name,
                    display_name=display_name,
                    context_length=context_length,
                    max_tokens=4096,
                    temperature=70,
                    capabilities=caps,
                    is_enabled=1,
                    sort_order=i,
                )
                db.add(llm_model)
                total_migrated += 1

            print(f"✅ 供应商 {provider.id}({provider.name}): 迁移 {len(models_json)} 个模型")

        await db.commit()
        print(f"\n🎉 迁移完成！共迁移 {total_migrated} 个模型")


if __name__ == "__main__":
    asyncio.run(migrate())
