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
        self._episode_repo = None

    def set_memory_manager(self, manager):
        """注入 MemoryManager 实例（应用启动时调用）"""
        self._memory_manager = manager

    @property
    def episode_repo(self):
        if self._episode_repo is None:
            from app.repository.episode_repo import EpisodeRepository
            self._episode_repo = EpisodeRepository()
        return self._episode_repo

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
        """软删除记忆 + 同步删除 Qdrant 向量"""
        # 先查出记忆信息（用于 Qdrant 清理）
        from app.models.markdown_memory import MarkdownMemory
        from sqlalchemy import select
        stmt = select(MarkdownMemory).where(
            MarkdownMemory.id == memory_id,
            MarkdownMemory.is_deleted == 0,
        )
        result = await db.execute(stmt)
        item = result.scalar_one_or_none()

        deleted = await self.repo.soft_delete(db, memory_id)

        # 同步删除 Qdrant 中对应的向量
        if deleted and item and self._memory_manager:
            try:
                from app.mappers.qdrant_mapper import QdrantMapper
                from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchText
                qdrant = QdrantMapper()
                tag = f"markdown:{item.title}"
                search_filter = Filter(must=[
                    FieldCondition(key="tags", match=MatchText(text=tag)),
                    FieldCondition(key="user_id", match=MatchValue(value=item.user_id)),
                ])
                results = qdrant._client.scroll(
                    collection_name="memory_vectors",
                    scroll_filter=search_filter,
                    limit=5,
                    with_vectors=False,
                )
                points = results[0] if results else []
                if points:
                    point_ids = [p.id for p in points]
                    qdrant._client.delete(
                        collection_name="memory_vectors",
                        points_selector=point_ids,
                    )
            except Exception as e:
                logger.warning(f"delete_memory: Qdrant 同步删除失败(非致命): {e}")

        return deleted

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
            logger.info(f"[distill] LLM 未提炼出新内容，{len(source_titles)} 天日志无新增")
            return DistillResult(
                observations=[], source_days=days,
                source_logs=source_titles, total_count=0,
            )

        # 9. 写入 observation + source 表
        created_observations: List[ObservationOut] = []
        obs_orm_objects = []  # 保留 ORM 对象用于后续实体抽取和信念演化
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

            # P2-10: 时间感知 — 自动填充 valid_from
            earliest_date = min(source_dates) if source_dates else ""
            valid_from = f"{earliest_date}T00:00:00" if earliest_date else ""

            # 写入 observation
            obs = await self.obs_repo.create(db, {
                "user_id": user_id,
                "content": content,
                "category": category,
                "freshness": freshness,
                "source_days": len(source_dates),
                "valid_from": valid_from,
            })
            obs_orm_objects.append(obs)

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

            # P1-6: Observation 向量化 — 同步到 Qdrant
            try:
                await self._sync_observation_to_vector(
                    obs.id, user_id, content, category, freshness,
                )
            except Exception as e:
                logger.warning(f"[distill] observation 向量同步失败: {e}")

        logger.info(f"[distill] 写入完成: {len(created_observations)} 条 observation")

        # ── v5.0: distill 后置 —— 关联 observation 到经历 ──
        if obs_orm_objects and self._memory_manager:
            try:
                await self._link_observations_to_episodes(db, obs_orm_objects)
            except Exception as e:
                logger.warning(f"[distill] 经历关联失败(非致命): {e}")

        # ── 后置管道: 实体自动抽取 + 信念演化（借鉴 Hindsight TEMPR + CARA）──
        entity_stats = {"entities": 0, "relations": 0}
        reinforce_stats = {"reinforced": 0, "weakened": 0, "contradicted": 0}
        try:
            if obs_orm_objects:
                entity_stats = await self.extract_entities(db, obs_orm_objects, user_id)
                reinforce_stats = await self.reinforce_insights(db, obs_orm_objects, user_id)
        except Exception as e:
            logger.warning(f"[distill] 后置管道失败（不影响主流程）: {e}")

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

    # ── v5.1: Observation 新鲜度自动衰减 ────────────────────

    async def sweep_freshness(self, db: AsyncSession) -> dict:
        """扫描 observation 并自动更新 freshness 状态

        衰减规则（基于 updated_at 距今天数）:
          - new >14天 → stable
          - stable >60天无更新 → weakening
          - weakening >30天 → stale

        strengthening 不自动衰减（持续被强化的信念应保持活跃）。
        stale observation 同步更新 Qdrant payload，检索时降权 0.5。

        Returns:
            {"new_to_stable": int, "stable_to_weakening": int, "weakening_to_stale": int}
        """
        stats = {"new_to_stable": 0, "stable_to_weakening": 0, "weakening_to_stale": 0}

        # 1. new >14天 → stable
        stale_new = await self.obs_repo.find_stale_by_freshness(db, "new", 14)
        for obs in stale_new:
            await self.obs_repo.update(db, obs.id, {"freshness": "stable"})
            stats["new_to_stable"] += 1

        # 2. stable >60天无更新 → weakening
        stale_stable = await self.obs_repo.find_stale_by_freshness(db, "stable", 60)
        for obs in stale_stable:
            await self.obs_repo.update(db, obs.id, {"freshness": "weakening"})
            stats["stable_to_weakening"] += 1

        # 3. weakening >30天 → stale
        stale_weakening = await self.obs_repo.find_stale_by_freshness(db, "weakening", 30)
        for obs in stale_weakening:
            await self.obs_repo.update(db, obs.id, {"freshness": "stale"})
            stats["weakening_to_stale"] += 1

        # 4. 同步 stale 状态到 Qdrant payload（用于检索时降权）
        # v5.1 fix: 通过内容匹配找到对应的 Qdrant point_id（observation.id != Qdrant UUID）
        if self._memory_manager and stale_weakening:
            from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchText
            for obs in stale_weakening:
                try:
                    # 通过 observation 内容关键词 + type=user_memory + network=observation 查找对应 point
                    search_text = f"observation:{obs.category}"
                    content_snippet = (obs.content or "")[:100].strip()
                    if content_snippet:
                        search_text = content_snippet

                    obs_filter = Filter(must=[
                        FieldCondition(key="type", match=MatchValue(value="user_memory")),
                        FieldCondition(key="network", match=MatchValue(value="observation")),
                        FieldCondition(key="user_id", match=MatchValue(value=obs.user_id)),
                        FieldCondition(key="summary", match=MatchText(text=search_text)),
                    ])

                    results = self._memory_manager.qdrant.search(
                        collection="memory_vectors",
                        query_vector=[0.0] * 1024,  # dummy vector
                        limit=1,
                        score_threshold=0.0,
                        raw_filter=obs_filter,
                    )

                    if results:
                        point_id = results[0].id
                        self._memory_manager.qdrant._client.set_payload(
                            collection_name="memory_vectors",
                            payload={"freshness": "stale"},
                            points=[point_id],
                        )
                except Exception:
                    pass  # fire-and-forget

        return stats

    # ── Reflect（深度反思 — 借鉴 Hindsight CARA）──────────

    async def reflect(
        self, db: AsyncSession, user_id: int = 0, days: int = 7,
    ) -> dict:
        """深度反思 — LLM 驱动的 Insight 生成

        借鉴 Hindsight CARA:
          - 输入近期 Observations + 已有 Insights
          - LLM 发现跨时间模式、矛盾、趋势
          - 输出结构化 Insight（pattern/trend/risk/contradiction）

        Returns:
            {"insights": [...], "analyzed": int, "stats": {...}}
        """
        from app.services.llm_provider_service import LLMProviderService
        from app.agent.llm_service import llm_service
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.models.memory_insight import MemoryInsight
        from sqlalchemy import select

        # 1. 获取近期 observations
        recent_obs = await self.obs_repo.find_all(db, user_id=user_id, limit=50)
        if not recent_obs:
            return {"insights": [], "analyzed": 0, "stats": {}, "message": "没有近期记忆可供分析"}

        # 2. 获取已有 active insights（避免重复 + 支持强化/弱化）
        stmt = select(MemoryInsight).where(
            MemoryInsight.is_deleted == 0, MemoryInsight.status == "active"
        ).order_by(MemoryInsight.confidence.desc()).limit(20)
        existing_insights = list((await db.execute(stmt)).scalars().all())

        # 3. 构建观测文本
        obs_text = "\n".join(
            f"- [{o.category}|{o.freshness}] {o.content[:200]}"
            for o in recent_obs
        )
        insight_text = "\n".join(
            f"- [{i.insight_type}|置信度:{i.confidence}%] {i.content[:200]}"
            for i in existing_insights
        ) if existing_insights else "（暂无已有洞察）"

        # 4. 统计信息（保留用于返回）
        category_counts: dict[str, int] = {}
        freshness_counts: dict[str, int] = {}
        for o in recent_obs:
            category_counts[o.category] = category_counts.get(o.category, 0) + 1
            freshness_counts[o.freshness] = freshness_counts.get(o.freshness, 0) + 1

        # 5. 加载 Agent 行为画像（P2-8: 借鉴 Hindsight CARA）
        profile_context = ""
        try:
            from app.models.agent_profile import AgentProfile
            profile = (await db.execute(
                select(AgentProfile).where(
                    AgentProfile.is_deleted == 0, AgentProfile.is_active == 1
                ).limit(1)
            )).scalar_one_or_none()
            if profile and profile.id:
                profile_context = f"""
## Agent 行为画像（Disposition Profile）
- 怀疑性(S): {profile.skepticism}/5  字面性(L): {profile.literalism}/5  共情性(E): {profile.empathy}/5
- 偏见强度: {profile.bias_strength}
- 背景: {profile.background or '（未设置）'}
"""
        except Exception:
            pass

        # 6. LLM 调用
        provider_service = LLMProviderService()
        provider = await provider_service.get_default_provider(db)
        if not provider:
            raise ValueError("请先在设置中配置默认 AI 供应商")
        model_name = ""
        if provider.models:
            enabled = [m for m in provider.models if m.is_enabled == 1]
            if enabled:
                model_name = enabled[0].model_name
        if not model_name:
            raise ValueError("没有可用的模型")

        system_prompt = f"""你是一个高级记忆反思系统（借鉴 Hindsight CARA 架构）。
你的任务是分析 Agent 近期的提炼记忆，产生有深度的洞察。
{profile_context}
## 分析维度
1. **模式识别（pattern）**: 跨时间的重复行为、偏好倾向、技术选择模式
2. **趋势检测（trend）**: 正在增强或减弱的主题，关注方向变化
3. **风险预警（risk）**: 反复出现的问题、潜在隐患、需要注意的偏差
4. **矛盾发现（contradiction）**: 新旧信息之间的冲突、立场变化

## 输出要求
严格按以下 JSON 格式输出，不要输出任何其他内容：

```json
{{
  "insights": [
    {{
      "content": "洞察内容（有深度、有具体发现，不要泛泛而谈）",
      "insight_type": "pattern/trend/risk/contradiction",
      "confidence": 70,
      "related_obs_indices": [1, 3],
      "rationale": "为什么得出这个结论（引用具体记忆）"
    }}
  ]
}}
```

## 规则
1. 每条洞察必须有具体证据支撑（引用 related_obs_indices）
2. confidence: 0-100，证据越充分越高
3. 优先发现人类难以察觉的跨时间模式
4. 与已有洞察对比：支持则 confidence 应高于已有的，矛盾则标记为 contradiction
5. 如果记忆数据太少无法得出有意义的洞察，返回空列表
6. 不要生成模板化的通用建议，每个洞察必须与具体记忆内容相关"""

        user_prompt = f"""## 近期提炼记忆（{len(recent_obs)} 条）
{obs_text}

## 已有洞察（{len(existing_insights)} 条）
{insight_text}

请分析以上记忆，产生有深度的洞察。严格按 JSON 格式输出。"""

        llm = await llm_service.get_chat_llm(
            db, provider_id=provider.id, model_name=model_name,
            temperature=0.4, max_tokens=4096,
        )
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        raw = response.content if isinstance(response.content, str) else str(response.content)

        tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens = response.usage_metadata.get("total_tokens", 0)
        logger.info(f"[reflect] LLM 完成: {len(recent_obs)} obs, raw={len(raw)} 字, tokens={tokens}")

        # 6. 解析 + 写入
        parsed = self._parse_distill_json(raw)
        insight_items = parsed.get("insights", [])

        created: list[dict] = []
        for item in insight_items:
            content = (item.get("content", "") or "").strip()
            if not content:
                continue
            insight_type = item.get("insight_type", "insight")
            if insight_type not in ("pattern", "trend", "risk", "contradiction"):
                insight_type = "insight"
            confidence = max(0, min(100, int(item.get("confidence", 50))))

            insight = MemoryInsight(
                user_id=user_id,
                content=content,
                insight_type=insight_type,
                confidence=confidence,
                evidence_count=len(item.get("related_obs_indices", [])),
                source_period=f"最近 {len(recent_obs)} 条记忆",
                status="active",
            )
            db.add(insight)
            created.append({
                "content": content,
                "insightType": insight_type,
                "confidence": confidence,
                "rationale": item.get("rationale", ""),
            })

        await db.flush()

        logger.info(f"[reflect] 生成 {len(created)} 条洞察")
        return {
            "insights": created,
            "analyzed": len(recent_obs),
            "existingInsights": len(existing_insights),
            "categoryBreakdown": category_counts,
            "freshnessBreakdown": freshness_counts,
        }

    # ── 实体自动抽取（借鉴 Hindsight TEMPR）──────────────

    async def extract_entities(
        self, db: AsyncSession, observations: list, user_id: int = 0,
    ) -> dict:
        """从新 Observation 中自动抽取实体和关系

        借鉴 Hindsight TEMPR:
          - LLM 识别命名实体（PERSON/TECH/PROJECT/TOOL/CONCEPT/ORG）
          - 自动消歧（匹配已有实体 + 字符串相似度）
          - 自动构建关系（含因果链接 causes/enables/prevents）

        Args:
            observations: 新产生的 Observation ORM 对象列表
            user_id: 用户 ID

        Returns:
            {"entities": int, "relations": int}
        """
        from app.services.llm_provider_service import LLMProviderService
        from app.agent.llm_service import llm_service
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.models.memory_entity import MemoryEntity
        from app.models.memory_entity_relation import MemoryEntityRelation
        from sqlalchemy import select

        if not observations:
            return {"entities": 0, "relations": 0}

        obs_text = "\n".join(
            f"[obs_id={o.id}][{o.category}] {o.content[:300]}"
            for o in observations
        )

        # 获取已有实体（用于消歧匹配）
        existing = (await db.execute(
            select(MemoryEntity).where(MemoryEntity.is_deleted == 0)
        )).scalars().all()
        existing_text = "\n".join(
            f"- {e.name} ({e.entity_type}, id={e.id})" for e in existing
        ) if existing else "（暂无已有实体）"

        provider_service = LLMProviderService()
        provider = await provider_service.get_default_provider(db)
        if not provider:
            return {"entities": 0, "relations": 0}
        model_name = ""
        if provider.models:
            enabled = [m for m in provider.models if m.is_enabled == 1]
            if enabled:
                model_name = enabled[0].model_name
        if not model_name:
            return {"entities": 0, "relations": 0}

        system_prompt = """你是一个实体和关系抽取专家。从记忆中识别实体并建立关系图谱。

## 实体类型
person（人）、tech（技术/框架）、project（项目）、tool（工具）、concept（概念）、org（组织）

## 关系类型
- uses（使用）: A 使用 B
- depends（依赖）: A 依赖 B
- belongs（属于）: A 属于 B
- creates（创建）: A 创建了 B
- works_at（就职）: A 就职于 B
- related（相关）: A 和 B 有关联
- causes（导致）: A 导致 B（因果）
- enables（使能）: A 使 B 成为可能（因果）
- prevents（阻止）: A 阻止了 B（因果）

## 时间推断 (v5.1 Bi-Temporal)
如果记忆内容暗示了时间信息，推断 valid_at（关系生效时间）。
例如: "2024年开始使用Python" → valid_at: "2024-01-01"
例如: "去年换了工作" → 推断为大约一年前的时间
没有明确时间信息时，valid_at 填 null。

## 输出 JSON

```json
{
  "entities": [
    {"name": "实体名称", "entity_type": "tech", "description": "简短描述", "aliases": ["别名1"]}
  ],
  "relations": [
    {"source": "实体名称1", "target": "实体名称2", "relation_type": "uses", "evidence": "来源依据", "valid_at": "2024-01-01"}
  ]
}
```

## 规则
1. 如果实体在已有列表中存在，使用已有名称（自动消歧）
2. 不要抽取过于泛化的实体（如"代码"、"系统"）
3. 因果关系（causes/enables/prevents）仅在证据明确时标注
4. 每个实体名称保持简洁规范
5. valid_at 格式为 "YYYY-MM-DD" 或 null"""

        user_prompt = f"""## 已有实体
{existing_text}

## 新提炼记忆
{obs_text}

请抽取实体和关系，严格按 JSON 格式输出。"""

        llm = await llm_service.get_chat_llm(
            db, provider_id=provider.id, model_name=model_name,
            temperature=0.2, max_tokens=2048,
        )
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        raw = response.content if isinstance(response.content, str) else str(response.content)
        parsed = self._parse_distill_json(raw)

        # 写入实体
        entity_name_map: dict[str, MemoryEntity] = {e.name: e for e in existing}
        new_entities = parsed.get("entities", [])
        created_count = 0

        for ent_data in new_entities:
            name = (ent_data.get("name", "") or "").strip()
            if not name or len(name) > 128:
                continue
            etype = ent_data.get("entity_type", "concept")
            if etype not in ("person", "tech", "project", "tool", "concept", "org"):
                etype = "concept"

            if name in entity_name_map:
                # 消歧命中：更新提及次数
                existing_ent = entity_name_map[name]
                existing_ent.mention_count += 1
                existing_ent.last_mentioned_at = datetime.now().isoformat()
            else:
                # 新实体
                new_ent = MemoryEntity(
                    user_id=user_id, name=name, entity_type=etype,
                    description=(ent_data.get("description", "") or "")[:500],
                    aliases=",".join(ent_data.get("aliases", []) or [])[:500],
                    mention_count=1,
                    last_mentioned_at=datetime.now().isoformat(),
                )
                db.add(new_ent)
                await db.flush()
                entity_name_map[name] = new_ent
                created_count += 1

        # 写入关系
        new_relations = parsed.get("relations", [])
        rel_count = 0
        valid_rel_types = {
            "uses", "depends", "belongs", "creates", "works_at",
            "related", "causes", "enables", "prevents",
        }

        for rel_data in new_relations:
            src_name = (rel_data.get("source", "") or "").strip()
            tgt_name = (rel_data.get("target", "") or "").strip()
            rtype = rel_data.get("relation_type", "related")
            if rtype not in valid_rel_types:
                rtype = "related"

            src_ent = entity_name_map.get(src_name)
            tgt_ent = entity_name_map.get(tgt_name)
            if not src_ent or not tgt_ent or src_ent.id == tgt_ent.id:
                continue

            # v5.1: 解析 valid_at 时间
            valid_at = None
            valid_at_str = rel_data.get("valid_at")
            if valid_at_str:
                try:
                    from datetime import datetime as dt_parse
                    valid_at = dt_parse.strptime(str(valid_at_str)[:10], "%Y-%m-%d")
                except (ValueError, TypeError):
                    valid_at = None

            # 检查是否已存在（含时间冲突检测）
            dup = (await db.execute(
                select(MemoryEntityRelation).where(
                    MemoryEntityRelation.source_entity_id == src_ent.id,
                    MemoryEntityRelation.target_entity_id == tgt_ent.id,
                    MemoryEntityRelation.relation_type == rtype,
                    MemoryEntityRelation.is_deleted == 0,
                )
            )).scalar_one_or_none()

            if dup:
                dup.weight += 1
                # v5.1: 如果新的有 valid_at 而旧的没有，更新
                if valid_at and not dup.valid_at:
                    dup.valid_at = valid_at
            else:
                # v5.1: 时间冲突检测 — 检查同对实体是否有不同类型的关系
                # 如果新关系与已有关系冲突（如 works_at 从 A 公司变为 B 公司）
                conflicting = (await db.execute(
                    select(MemoryEntityRelation).where(
                        MemoryEntityRelation.source_entity_id == src_ent.id,
                        MemoryEntityRelation.relation_type == rtype,
                        MemoryEntityRelation.target_entity_id != tgt_ent.id,
                        MemoryEntityRelation.invalid_at == None,  # noqa: E711
                        MemoryEntityRelation.is_deleted == 0,
                    )
                )).scalars().all()

                # 对某些关系类型（如 works_at, belongs），新关系可能意味着旧关系已失效
                if conflicting and rtype in ("works_at", "belongs", "uses"):
                    for old_rel in conflicting:
                        old_rel.invalid_at = datetime.now()
                        logger.info(
                            f"[extract_entities] 时间冲突检测: 关系 {src_name} -> {old_rel.target_entity_id} "
                            f"({rtype}) 已标记 invalid_at"
                        )

                rel = MemoryEntityRelation(
                    user_id=user_id,
                    source_entity_id=src_ent.id,
                    target_entity_id=tgt_ent.id,
                    relation_type=rtype,
                    evidence=(rel_data.get("evidence", "") or "")[:500],
                    weight=1,
                    valid_at=valid_at,
                )
                db.add(rel)
                rel_count += 1

        await db.flush()
        logger.info(f"[extract_entities] 新建 {created_count} 实体, {rel_count} 关系")
        return {"entities": created_count, "relations": rel_count}

    # ── 信念自动演化（借鉴 Hindsight Opinion Reinforcement）──────

    async def reinforce_insights(
        self, db: AsyncSession, new_observations: list, user_id: int = 0,
    ) -> dict:
        """信念自动演化 — 新证据到达时更新 Insight 置信度

        借鉴 Hindsight Opinion Reinforcement:
          - 通过语义相似度找到相关 Insight
          - LLM 评估关系：reinforce / weaken / contradict / neutral
          - 更新置信度：reinforce +10, weaken -10, contradict -20
          - 矛盾时更新状态为 superseded

        Args:
            new_observations: 新产生的 Observation ORM 对象列表
            user_id: 用户 ID

        Returns:
            {"reinforced": int, "weakened": int, "contradicted": int}
        """
        from app.services.llm_provider_service import LLMProviderService
        from app.agent.llm_service import llm_service
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.models.memory_insight import MemoryInsight
        from sqlalchemy import select

        if not new_observations:
            return {"reinforced": 0, "weakened": 0, "contradicted": 0}

        # 获取 active insights
        stmt = select(MemoryInsight).where(
            MemoryInsight.is_deleted == 0, MemoryInsight.status == "active"
        ).order_by(MemoryInsight.confidence.desc()).limit(30)
        active_insights = list((await db.execute(stmt)).scalars().all())
        if not active_insights:
            return {"reinforced": 0, "weakened": 0, "contradicted": 0}

        new_obs_text = "\n".join(
            f"- [{o.category}] {o.content[:200]}" for o in new_observations
        )
        insight_text = "\n".join(
            f"[id={i.id}] [{i.insight_type}|置信度:{i.confidence}%] {i.content[:200]}"
            for i in active_insights
        )

        provider_service = LLMProviderService()
        provider = await provider_service.get_default_provider(db)
        if not provider:
            return {"reinforced": 0, "weakened": 0, "contradicted": 0}
        model_name = ""
        if provider.models:
            enabled = [m for m in provider.models if m.is_enabled == 1]
            if enabled:
                model_name = enabled[0].model_name
        if not model_name:
            return {"reinforced": 0, "weakened": 0, "contradicted": 0}

        system_prompt = """你是一个信念演化评估系统（借鉴 Hindsight Opinion Reinforcement）。
评估新证据对已有洞察（信念）的影响。

## 评估维度
- reinforce: 新证据支持该洞察，增强置信度
- weaken: 新证据削弱该洞察，降低置信度
- contradict: 新证据与该洞察矛盾，需要大幅修正或替代
- neutral: 新证据与该洞察无关

## 输出 JSON

```json
{
  "assessments": [
    {"insight_id": 123, "verdict": "reinforce", "reason": "简要原因"}
  ]
}
```

## 规则
1. 只评估与已有洞察相关的新证据
2. 每个已有多达评估一次（如果有多条相关证据，取最强影响）
3. 只输出有相关性的评估，不要对每条洞察都输出
4. contradict 仅在证据明确矛盾时使用"""

        user_prompt = f"""## 新提炼记忆
{new_obs_text}

## 已有洞察
{insight_text}

请评估新证据对已有洞察的影响，严格按 JSON 格式输出。"""

        llm = await llm_service.get_chat_llm(
            db, provider_id=provider.id, model_name=model_name,
            temperature=0.2, max_tokens=2048,
        )
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        raw = response.content if isinstance(response.content, str) else str(response.content)
        parsed = self._parse_distill_json(raw)

        stats = {"reinforced": 0, "weakened": 0, "contradicted": 0}
        insight_map = {i.id: i for i in active_insights}
        ALPHA = 10  # 置信度调整步长

        # v5.0: 初始化仲裁服务 + history 审计
        from app.services.insight_arbitration_service import InsightArbitrationService
        arbiter = InsightArbitrationService()

        # 收集新 observation 的 obs_ids（用于仲裁）
        new_obs_ids = [o.id for o in new_observations if hasattr(o, 'id') and o.id]

        for assessment in parsed.get("assessments", []):
            iid = assessment.get("insight_id")
            verdict = assessment.get("verdict", "neutral")
            reason = assessment.get("reason", "")
            if iid not in insight_map or verdict == "neutral":
                continue

            insight = insight_map[iid]
            old_confidence = insight.confidence

            if verdict == "reinforce":
                insight.confidence = min(100, insight.confidence + ALPHA)
                insight.evidence_count += 1
                stats["reinforced"] += 1
                await arbiter.record_history(
                    db, insight.id, "reinforced",
                    old_confidence=old_confidence,
                    new_confidence=insight.confidence,
                    reason=reason[:500],
                    trigger_obs_ids=new_obs_ids,
                )
            elif verdict == "weaken":
                insight.confidence = max(0, insight.confidence - ALPHA)
                if insight.confidence < 20:
                    insight.status = "dismissed"
                stats["weakened"] += 1
                await arbiter.record_history(
                    db, insight.id, "weakened",
                    old_confidence=old_confidence,
                    new_confidence=insight.confidence,
                    reason=reason[:500],
                    trigger_obs_ids=new_obs_ids,
                )
            elif verdict == "contradict":
                # v5.0: 调用仲裁引擎而非简单标记 superseded
                try:
                    arb_result = await arbiter.arbitrate_contradiction(
                        db, insight,
                        new_evidence_text=new_obs_text[:500],
                        new_evidence_obs_ids=new_obs_ids,
                        contradiction_reason=reason[:500],
                        user_id=user_id,
                    )
                    if arb_result.get("action") == "superseded":
                        stats["contradicted"] += 1
                    else:
                        # 旧 Insight 保留，仅记录矛盾
                        stats["weakened"] += 1  # 统计为弱化
                except Exception as arb_err:
                    # 仲裁失败时降级为原始逻辑
                    logger.warning(f"[reinforce] 仲裁失败，降级: {arb_err}")
                    insight.confidence = max(0, insight.confidence - 2 * ALPHA)
                    insight.status = "superseded"
                    stats["contradicted"] += 1
                    await arbiter.record_history(
                        db, insight.id, "contradicted",
                        old_confidence=old_confidence,
                        new_confidence=insight.confidence,
                        reason=f"仲裁失败降级: {reason[:200]}",
                        trigger_obs_ids=new_obs_ids,
                    )

        await db.flush()
        logger.info(f"[reinforce] 强化={stats['reinforced']} 弱化={stats['weakened']} 矛盾={stats['contradicted']}")
        return stats

    # ── v5.0: 经历创建 + Observation 关联 ─────────────

    async def create_episode_from_conversation(
        self, db, conversation_id: int, user_id: int, messages: list,
    ) -> Optional[dict]:
        """从对话创建经历（借鉴 Zep Graphiti Episode Node）

        幂等: 同一 conversation_id 只创建一个经历。
        """
        if not messages or not self._memory_manager:
            return None

        existing = await self.episode_repo.find_by_conversation(db, conversation_id)
        if existing:
            return None

        started_at = datetime.utcnow()
        ended_at = datetime.utcnow()
        try:
            first_msg = messages[0]
            if isinstance(first_msg, dict) and first_msg.get("timestamp"):
                started_at = datetime.fromisoformat(first_msg["timestamp"])
            last_msg = messages[-1]
            if isinstance(last_msg, dict) and last_msg.get("timestamp"):
                ended_at = datetime.fromisoformat(last_msg["timestamp"])
        except (ValueError, TypeError, KeyError):
            pass

        msg_count = len(messages)
        text = "\n".join(
            f"{m.get('role', 'user')}: {(m.get('content', '') or '')[:100]}"
            for m in messages[:10]
        )
        title = f"对话 #{conversation_id} ({msg_count} 条消息)"
        summary = text[:1000] if text else title

        tags = []
        all_text = " ".join(str(m.get("content", ""))[:200] for m in messages[:20]).lower()
        tag_keywords = ["python", "javascript", "react", "vue", "架构", "部署", "bug", "重构"]
        for kw in tag_keywords:
            if kw in all_text:
                tags.append(kw)

        entity_ids = []
        try:
            from app.models.memory_entity import MemoryEntity
            from sqlalchemy import select
            entities = (await db.execute(
                select(MemoryEntity).where(MemoryEntity.is_deleted == 0)
            )).scalars().all()
            for ent in entities:
                ent_names = [ent.name.lower()] + [
                    a.strip().lower() for a in (ent.aliases or "").split(",") if a.strip()
                ]
                if any(name in all_text for name in ent_names):
                    entity_ids.append(ent.id)
        except Exception:
            pass

        qdrant_point_id = await self._memory_manager.save_episode(
            user_id=user_id, conversation_id=conversation_id,
            title=title, summary=summary,
            started_at=started_at.isoformat(), ended_at=ended_at.isoformat(),
            message_count=msg_count, entity_ids=entity_ids, tags=tags,
        )

        episode = await self.episode_repo.create(db, {
            "user_id": user_id, "conversation_id": conversation_id,
            "title": title, "summary": summary,
            "started_at": started_at, "ended_at": ended_at,
            "message_count": msg_count,
            "entity_ids": ",".join(str(e) for e in entity_ids),
            "observation_ids": "", "tags": tags,
            "qdrant_point_id": qdrant_point_id,
        })

        logger.info(f"[episode] 创建: id={episode.id} conv={conversation_id}")
        return {"id": episode.id, "title": title}

    async def _link_observations_to_episodes(self, db, observations: list):
        """将新创建的 observation 关联到来源对话的经历"""
        for obs in observations:
            if not obs.valid_from:
                continue
            try:
                episodes = await self.episode_repo.find_by_time_range(
                    db, user_id=obs.user_id,
                    start_time=obs.valid_from, end_time=obs.valid_from, limit=1,
                )
                for ep in episodes:
                    await self.episode_repo.append_observation(db, ep.id, obs.id)
            except Exception as e:
                logger.debug(f"[episode-link] obs_id={obs.id} 关联失败: {e}")

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

    async def _sync_observation_to_vector(
        self, obs_id: int, user_id: int, content: str, category: str, freshness: str = "new",
    ):
        """将 Observation 同步到 Qdrant 向量（P1-6: 打通提炼记忆的语义检索）

        v5.1: 同步 freshness 字段到 payload，用于检索时 stale 降权。
        """
        if not self._memory_manager:
            return
        await self._memory_manager.save_memory(
            user_id=user_id,
            summary=f"[observation:{category}] {content[:500]}",
            tags=["observation", f"category:{category}"],
            importance=8,  # 提炼记忆权重高于原始 detail
            network="observation",
            freshness=freshness,
        )
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
