"""方案 A 迁移脚本: llm_provider.models JSON → llm_model 独立表

执行方式: cd backend && python -m scripts.migrate_llm_models

功能:
  1. 创建 llm_model 表
  2. 用原生 SQL 读取 llm_provider.models JSON（兼容已从 ORM 移除的字段）
  3. 迁移数据到 llm_model 表
"""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, AsyncSessionLocal
from app.models.llm_model import LLMModel
from sqlalchemy import text


async def migrate():
    async with engine.begin() as conn:
        # 1. 创建 llm_model 表（如果不存在）
        await conn.run_sync(LLMModel.metadata.create_all)
        print("✅ llm_model 表已创建/确认存在")

    async with AsyncSessionLocal() as db:
        # 2. 用原生 SQL 读取旧 models JSON（字段已从 ORM 移除，但数据库列可能还在）
        try:
            result = await db.execute(text(
                "SELECT id, name, models FROM llm_provider WHERE is_deleted = 0"
            ))
            rows = result.fetchall()
        except Exception as e:
            if "Unknown column" in str(e) or "doesn't exist" in str(e):
                print("⚠️  llm_provider.models 列已不存在，跳过迁移")
                print("   请在前端页面手动添加模型")
                return
            raise

        total_migrated = 0
        for row in rows:
            provider_id = row[0]
            provider_name = row[1]
            models_json = row[2]

            if not models_json:
                continue

            # 解析 JSON
            if isinstance(models_json, str):
                try:
                    models_list = json.loads(models_json)
                except json.JSONDecodeError:
                    print(f"⚠️  供应商 {provider_id}({provider_name}) models JSON 解析失败，跳过")
                    continue
            elif isinstance(models_json, list):
                models_list = models_json
            else:
                continue

            if not models_list:
                continue

            # 检查是否已迁移
            existing = await db.execute(text(
                "SELECT COUNT(*) FROM llm_model WHERE provider_id = :pid AND is_deleted = 0"
            ), {"pid": provider_id})
            if existing.scalar() > 0:
                print(f"⏭  供应商 {provider_id}({provider_name}) 已有模型数据，跳过")
                continue

            # 迁移每个模型
            for i, m in enumerate(models_list):
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

                await db.execute(text("""
                    INSERT INTO llm_model
                    (provider_id, model_name, display_name, context_length, max_tokens, temperature,
                     capabilities, is_enabled, sort_order, is_deleted, created_at, updated_at)
                    VALUES (:pid, :mname, :dname, :clen, 4096, 70, :caps, 1, :sort, 0, NOW(), NOW())
                """), {
                    "pid": provider_id,
                    "mname": model_name,
                    "dname": display_name,
                    "clen": context_length,
                    "caps": json.dumps(caps),
                    "sort": i,
                })
                total_migrated += 1

            print(f"✅ 供应商 {provider_id}({provider_name}): 迁移 {len(models_list)} 个模型")

        await db.commit()
        print(f"\n🎉 迁移完成！共迁移 {total_migrated} 个模型")

        if total_migrated == 0:
            print("   没有需要迁移的数据，如需添加模型请在前端页面操作")


if __name__ == "__main__":
    asyncio.run(migrate())
