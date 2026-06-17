"""Markdown 记忆文件 Service — 业务编排层

职责:
  - Markdown 记忆 CRUD
  - 提炼记忆（Observations）CRUD + 结构化提取
  - 与 Qdrant 向量同步
  - daily log 自动创建

遵循规范:
  - 分层架构: service 调用 repository
  - 统一异常: RecordNotFoundError

Hindsight 借鉴:
  - 结构化提取（非自由文本）
  - 多对多关联（observation ↔ source daily log）
  - Mission + Directives 模型
  - 新鲜度趋势标注
  - 证据溯源
"""
import json
from typing import List, Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.markdown_memory_repo import MarkdownMemoryRepository
from app.repository.observation_repo import ObservationRepository
from app.schemas.memory_v2 import (
    MarkdownMemoryCreate, MarkdownMemoryOut, MarkdownMemoryListOut,
    ObservationOut, ObservationSourceOut, DistillResult,
)
from app.core.exceptions import RecordNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class MarkdownMemoryService:
    """Markdown 记忆文件业务服务"""

    def __init__(self):
        self.repo = MarkdownMemoryRepository()
        self.obs_repo = ObservationRepository()
        self._memory_manager = None

    def set_memory_manager(self, manager):
        """注入 MemoryManager 实例（应用启动时调用）"""
        self._memory_manager = manager

    # ── Markdown 记忆 CRUD ──────────────────────────────

    async def list_memories(
        self, db: AsyncSession, user_id: int = 0,
        page: int = 1, page_size: int = 20,
        memory_type: Optional[str] = None,
    ) -> Tuple[List[MarkdownMemoryListOut], int]:
        """获取记忆列表"""
        offset = (page - 1) * page_size
        items = await self.repo.find_all(db, offset=offset, limit=page_size,
                                          user_id=user_id, memory_type=memory_type)
        total = await self.repo.count(db, user_id=user_id, memory_type=memory_type)
        return [self._to_list_out(i) for i in items], total

    async def get_memory(self, db: AsyncSession, memory_id: int) -> MarkdownMemoryOut:
        """获取记忆详情"""
        item = await self.repo.find_by_id(db, memory_id)
        if not item:
            raise RecordNotFoundError("记忆文件不存在")
        return self._to_out(item)

    async def get_by_title(self, db: AsyncSession, user_id: int, title: str) -> Optional[MarkdownMemoryOut]:
        """按标题查找"""
        item = await self.repo.find_by_title(db, user_id, title)
        if not item:
            return None
        return self._to_out(item)

    async def upsert_memory(
        self, db: AsyncSession, user_id: int, data: MarkdownMemoryCreate
    ) -> MarkdownMemoryOut:
        """创建或更新记忆文件"""
        item = await self.repo.upsert(
            db, user_id=user_id,
            title=data.title, content=data.content,
            memory_type=data.memory_type,
        )
        if self._memory_manager:
            try:
                await self._sync_to_vector(item.id, user_id, data.title, data.content)
            except Exception as e:
                logger.warning(f"[markdown_memory] 向量同步失败: {e}")
        return self._to_out(item)

    async def append_daily_log(
        self, db: AsyncSession, user_id: int, content: str
    ) -> MarkdownMemoryOut:
        """追加到今日 daily log"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        existing = await self.repo.find_by_title(db, user_id, today)
        if existing:
            new_content = existing.content + "\n" + content
            item = await self.repo.upsert(db, user_id, today, new_content, "daily")
        else:
            header = f"# {today} 每日日志\n\n"
            item = await self.repo.upsert(db, user_id, today, header + content, "daily")
        return self._to_out(item)

    async def get_or_create_longterm(self, db: AsyncSession, user_id: int = 0) -> MarkdownMemoryOut:
        """获取或创建长期记忆文件"""
        existing = await self.repo.find_by_title(db, user_id, "MEMORY")
        if existing:
            return self._to_out(existing)
        default_content = "# 长期记忆\n\n> 由 Agent 自动提炼和用户手动维护\n\n"
        item = await self.repo.upsert(db, user_id, "MEMORY", default_content, "longterm")
        return self._to_out(item)

    async def update_longterm(
        self, db: AsyncSession, user_id: int, content: str
    ) -> MarkdownMemoryOut:
        """更新长期记忆内容"""
        item = await self.repo.upsert(db, user_id, "MEMORY", content, "longterm")
        return self._to_out(item)

    async def list_daily_logs(
        self, db: AsyncSession, user_id: int = 0, limit: int = 7
    ) -> List[MarkdownMemoryListOut]:
        """获取最近 N 天的 daily log 列表"""
        items = await self.repo.find_all(
            db, offset=0, limit=limit,
            user_id=user_id, memory_type="daily",
        )
        return [self._to_list_out(i) for i in items]

    async def delete_memory(self, db: AsyncSession, memory_id: int) -> bool:
        """软删除记忆"""
        return await self.repo.soft_delete(db, memory_id)

    # ── 提炼记忆（Observations）────────────────────────

    async def distill(
        self, db: AsyncSession, user_id: int = 0,
        days: int = 7, mission: str = "",
        directives: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
    ) -> DistillResult:
        """提炼记忆 — 结构化提取，写入 observation + source 表

        借鉴 Hindsight:
          - Mission: 告诉 LLM 提取什么、忽略什么
          - Directives: 硬规则约束
          - 结构化 JSON 输出（非自由文本）
          - 证据溯源（关联到具体 daily log）

        Returns:
            DistillResult（含 observations 列表 + 来源信息）
        """
        from app.services.llm_provider_service import LLMProviderService
        from app.agent.llm_service import llm_service
        from langchain_core.messages import HumanMessage, SystemMessage

        if not mission:
            mission = "提取技术决策、架构选型、踩坑经验、主人偏好。忽略寒暄和临时调试信息。"
        if categories is None:
            categories = ["decisions", "pitfalls", "preferences", "status"]
        if directives is None:
            directives = []

        # 1. 获取默认 LLM 供应商
        provider_service = LLMProviderService()
        provider = await provider_service.get_default_provider(db)
        if not provider:
            raise ValueError("请先在设置中配置默认 AI 供应商")

        model_name = ""
        if provider.models:
            enabled_models = [m for m in provider.models if m.is_enabled == 1]
            if enabled_models:
                model_name = enabled_models[0].model_name
        if not model_name:
            raise ValueError("没有可用的模型")

        # 2. 读取最近 N 天 daily log（含内容）
        daily_items = await self.repo.find_all(
            db, offset=0, limit=days,
            user_id=user_id, memory_type="daily",
        )
        if not daily_items:
            raise ValueError("最近没有每日日志，无法提炼")

        # 构建日志映射（title → id），用于后续关联
        log_id_map = {item.title: item.id for item in daily_items}
        source_titles = [item.title for item in daily_items]

        # 拼接日志内容
        logs_text = ""
        for item in daily_items:
            logs_text += f"\n\n--- {item.title} ---\n{item.content}"

        # 3. 读取已有 observations（去重用）
        existing_obs = await self.obs_repo.find_all(db, user_id=user_id, limit=100)
        existing_text = ""
        if existing_obs:
            existing_text = "\n".join(f"- [{o.category}] {o.content[:100]}" for o in existing_obs)

        # 4. 构建分类描述
        category_map = {
            "decisions": "🔑 关键决策：技术选型、架构变更、重要结论",
            "pitfalls": "🐛 踩坑经验：bug 根因、避坑方法、失败教训",
            "preferences": "👤 主人偏好：工作习惯、代码风格、沟通偏好",
            "status": "📦 项目状态：里程碑、进度、待办",
        }
        category_desc = "\n".join(f"- {category_map[c]}" for c in categories if c in category_map)

        # 5. 构建 Directives 描述
        directives_desc = ""
        if directives:
            directives_desc = "\n## 硬规则（必须遵守）\n" + "\n".join(f"- {d}" for d in directives)

        # 6. 构建 Prompt — 要求结构化 JSON 输出
        system_prompt = f"""你是一个记忆提炼专家。从每日日志中提炼值得长期记住的信息。

## 提炼指令（Mission）
{mission}

## 分类
{category_desc}
{directives_desc}

## 输出要求

严格按以下 JSON 格式输出，不要输出任何其他内容：

```json
{{{{
  "observations": [
    {{{{
      "content": "提炼内容（Markdown 格式，保留关键细节）",
      "category": "decisions/pitfalls/preferences/status",
      "freshness": "new/stable/strengthening",
      "source_dates": ["2026-06-14", "2026-06-15"],
      "evidence_quotes": ["从日志中提取的关键引用1", "关键引用2"]
    }}}}
  ]
}}}}
```

## 规则
1. 每条提炼标注来源日期和关键引用（精确溯源）
2. 与已有提炼去重（见下方已有提炼列表）
3. freshness: new=首次出现, stable=多次出现, strengthening=越来越频繁
4. 忽略寒暄、重复内容、临时调试信息
5. 保留原始关键细节，不要过度抽象"""

        user_prompt = f"""## 已有提炼（去重用）
{existing_text if existing_text else "（暂无）"}

## 最近 {len(daily_items)} 天日志
{logs_text}

请提炼值得长期记住的信息，严格按 JSON 格式输出。"""

        # 7. 调用 LLM
        llm = await llm_service.get_chat_llm(
            db, provider_id=provider.id, model_name=model_name,
            temperature=0.3, max_tokens=4096,
        )
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        raw = response.content if isinstance(response.content, str) else str(response.content)

        # Token 日志
        tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens = response.usage_metadata.get("total_tokens", 0)
        logger.info(
            f"[distill] LLM 调用完成: {len(source_titles)} 天日志, "
            f"raw={len(raw)} 字, tokens={tokens}, model={model_name}"
        )

        # 8. 解析 JSON
        parsed = self._parse_distill_json(raw)
        obs_list = parsed.get("observations", [])
        if not obs_list:
            logger.warning(f"[distill] LLM 返回无效 JSON，raw 前 500 字: {raw[:500]}")
            raise ValueError("LLM 未返回有效的提炼结果，请重试（已记录原始输出到日志）")

        # 9. 写入 observation + source 表
        created_observations: List[ObservationOut] = []
        for obs_data in obs_list:
            content = obs_data.get("content", "").strip()
            if not content:
                continue

            category = obs_data.get("category", "decisions")
            if category not in categories:
                category = categories[0] if categories else "decisions"

            freshness = obs_data.get("freshness", "new")
            source_dates = obs_data.get("source_dates", [])
            evidence_quotes = obs_data.get("evidence_quotes", [])

            # 写入 observation
            obs = await self.obs_repo.create(db, {
                "user_id": user_id,
                "content": content,
                "category": category,
                "freshness": freshness,
                "source_days": len(source_dates),
            })

            # 写入关联 source
            sources_out: List[ObservationSourceOut] = []
            for i, date_str in enumerate(source_dates):
                log_id = log_id_map.get(date_str, 0)
                if not log_id:
                    continue
                quote = evidence_quotes[i] if i < len(evidence_quotes) else ""
                src = await self.obs_repo.create_source(db, {
                    "observation_id": obs.id,
                    "source_memory_id": log_id,
                    "evidence_quote": quote[:500],
                })
                sources_out.append(ObservationSourceOut(
                    source_id=src.id,
                    log_id=log_id,
                    log_title=date_str,
                    evidence_quote=quote[:500],
                ))

            created_observations.append(ObservationOut(
                id=obs.id,
                content=content,
                category=category,
                freshness=freshness,
                source_days=len(source_dates),
                proof_count=len(sources_out),
                sources=sources_out,
                created_at=str(obs.created_at) if obs.created_at else None,
                updated_at=str(obs.updated_at) if obs.updated_at else None,
            ))

        logger.info(f"[distill] 写入完成: {len(created_observations)} 条 observation")

        return DistillResult(
            observations=created_observations,
            source_days=len(source_titles),
            source_logs=source_titles,
            total_count=len(created_observations),
        )

    def _parse_distill_json(self, raw: str) -> dict:
        """解析 LLM 返回的 JSON（容错处理）"""
        # 尝试直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 尝试提取 ```json ... ``` 块
        import re
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找第一个 { 到最后一个 }
        first_brace = raw.find('{')
        last_brace = raw.rfind('}')
        if first_brace != -1 and last_brace > first_brace:
            try:
                return json.loads(raw[first_brace:last_brace + 1])
            except json.JSONDecodeError:
                pass

        logger.warning(f"[distill] JSON 解析失败，raw 前 200 字: {raw[:200]}")
        return {"observations": []}

    async def list_observations(
        self, db: AsyncSession, user_id: int = 0,
        category: Optional[str] = None,
        page: int = 1, page_size: int = 50,
    ) -> Tuple[List[ObservationOut], int]:
        """获取提炼记忆列表"""
        offset = (page - 1) * page_size
        items = await self.obs_repo.find_all(
            db, user_id=user_id, category=category,
            offset=offset, limit=page_size,
        )
        total = await self.obs_repo.count(db, user_id=user_id, category=category)

        result: List[ObservationOut] = []
        for obs in items:
            proof_count = await self.obs_repo.get_proof_count(db, obs.id)
            sources_raw = await self.obs_repo.get_source_with_daily_log(db, obs.id)
            sources = [
                ObservationSourceOut(
                    source_id=s["source_id"],
                    log_id=s["log_id"],
                    log_title=s["log_title"],
                    evidence_quote=s["evidence_quote"],
                )
                for s in sources_raw
            ]
            result.append(ObservationOut(
                id=obs.id,
                content=obs.content,
                category=obs.category,
                freshness=obs.freshness,
                source_days=obs.source_days,
                proof_count=proof_count,
                sources=sources,
                created_at=str(obs.created_at) if obs.created_at else None,
                updated_at=str(obs.updated_at) if obs.updated_at else None,
            ))

        return result, total

    async def get_observation(self, db: AsyncSession, obs_id: int) -> ObservationOut:
        """获取单条提炼记忆详情"""
        obs = await self.obs_repo.find_by_id(db, obs_id)
        if not obs:
            raise RecordNotFoundError("提炼记忆不存在")

        proof_count = await self.obs_repo.get_proof_count(db, obs.id)
        sources_raw = await self.obs_repo.get_source_with_daily_log(db, obs.id)
        sources = [
            ObservationSourceOut(
                source_id=s["source_id"],
                log_id=s["log_id"],
                log_title=s["log_title"],
                evidence_quote=s["evidence_quote"],
            )
            for s in sources_raw
        ]
        return ObservationOut(
            id=obs.id,
            content=obs.content,
            category=obs.category,
            freshness=obs.freshness,
            source_days=obs.source_days,
            proof_count=proof_count,
            sources=sources,
            created_at=str(obs.created_at) if obs.created_at else None,
            updated_at=str(obs.updated_at) if obs.updated_at else None,
        )

    async def update_observation(
        self, db: AsyncSession, obs_id: int,
        content: Optional[str] = None,
        category: Optional[str] = None,
        freshness: Optional[str] = None,
    ) -> ObservationOut:
        """更新单条提炼记忆"""
        obs = await self.obs_repo.find_by_id(db, obs_id)
        if not obs:
            raise RecordNotFoundError("提炼记忆不存在")

        update_data = {}
        if content is not None:
            update_data["content"] = content
        if category is not None:
            update_data["category"] = category
        if freshness is not None:
            update_data["freshness"] = freshness

        if update_data:
            await self.obs_repo.update(db, obs_id, update_data)

        return await self.get_observation(db, obs_id)

    async def delete_observation(self, db: AsyncSession, obs_id: int) -> bool:
        """软删除单条提炼记忆"""
        return await self.obs_repo.soft_delete(db, obs_id)

    async def create_observation_source(
        self, db: AsyncSession, observation_id: int, source_memory_id: int, evidence_quote: str = "",
    ) -> dict:
        """创建 observation 与 daily log 的关联"""
        src = await self.obs_repo.create_source(db, {
            "observation_id": observation_id,
            "source_memory_id": source_memory_id,
            "evidence_quote": evidence_quote[:500],
        })
        return {"id": src.id, "observation_id": observation_id, "source_memory_id": source_memory_id}

    async def delete_observation_source(self, db: AsyncSession, source_id: int) -> bool:
        """删除关联记录"""
        return await self.obs_repo.delete_source(db, source_id)

    async def get_category_stats(self, db: AsyncSession, user_id: int) -> dict:
        """获取分类统计"""
        return await self.obs_repo.count_by_category(db, user_id)

    # ── 向量同步 ────────────────────────────────────────

    async def _sync_to_vector(self, memory_id: int, user_id: int, title: str, content: str):
        """将 Markdown 内容同步到 Qdrant 向量"""
        if not self._memory_manager:
            return
        await self._memory_manager.save_memory(
            user_id=user_id,
            summary=f"[{title}] {content[:500]}",
            tags=[f"markdown:{title}"],
            importance=6,
        )
        await self.repo.mark_synced(None, memory_id)

    # ── 转换 ────────────────────────────────────────────

    @staticmethod
    def _to_out(item) -> MarkdownMemoryOut:
        return MarkdownMemoryOut(
            id=item.id,
            user_id=item.user_id,
            title=item.title,
            content=item.content,
            memory_type=item.memory_type,
            word_count=item.word_count,
            qdrant_synced=item.qdrant_synced,
        )

    @staticmethod
    def _to_list_out(item) -> MarkdownMemoryListOut:
        return MarkdownMemoryListOut(
            id=item.id,
            title=item.title,
            memory_type=item.memory_type,
            word_count=item.word_count,
            created_at=str(item.created_at) if item.created_at else None,
            updated_at=str(item.updated_at) if item.updated_at else None,
        )


# 全局单例
markdown_memory_service = MarkdownMemoryService()
