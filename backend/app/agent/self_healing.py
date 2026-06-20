"""Self-Healing Agent 模块 — Reflexion 模式实现

基于论文《Reflexion: Language Agents with Verbal Reinforcement Learning》
结合 2026 年行业最佳实践。

核心闭环：
  失败 → 归因(错误类型/触发条件) → 结构化反思 → 存入记忆 → 下轮注入 → 成功

存储策略：
  短期反思: Redis (TTL 30min, key=healing:goal:{goal_id})
  长期反思: MySQL healing_reflection 表 (持久化)

四大支柱：
  1. FailureAnalyzer — 失败分析与结构化反思
  2. HealingMemory — 长短期自愈记忆（Redis + MySQL）
  3. HealingStrategy — 策略注入与重试决策
  4. 治理机制 — TTL/作用域/衰减/最大重试
"""

import time
import json
import re
from enum import Enum
from typing import Optional
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── 失败类型枚举 ──────────────────────────────────────────

class FailureType(str, Enum):
    """失败类型分类"""
    TOOL_ERROR = "tool_error"               # 工具调用失败
    GUARDRAIL_FAIL = "guardrail_fail"       # 输出校验失败
    LLM_ERROR = "llm_error"                # LLM 调用失败
    TIMEOUT = "timeout"                     # 超时
    EMPTY_OUTPUT = "empty_output"           # 空输出
    IRRELEVANT = "irrelevant"               # 输出与目标无关
    INCOMPLETE = "incomplete"               # 输出不完整
    BUDGET_EXCEEDED = "budget_exceeded"     # 预算超限
    UNKNOWN = "unknown"                     # 未知错误


# ── 结构化反思（Reflexion 核心）──────────────────────────

class Reflection(BaseModel):
    """结构化反思 — 将失败转化为可积累的资产"""
    failure_type: FailureType = Field(description="失败类型")
    trigger_condition: str = Field(description="触发条件")
    what_not_to_do: str = Field(description="避免的错误")
    suggested_strategy: str = Field(description="建议策略")
    confidence: float = Field(default=0.7, ge=0, le=1, description="置信度 0-1")
    scope_tags: list[str] = Field(default_factory=list, description="作用域标签")
    ttl_seconds: int = Field(default=3600, description="有效期（秒）")
    created_at: float = Field(default_factory=time.time, description="创建时间戳")
    retry_count: int = Field(default=0, description="已重试次数")
    subtask_id: Optional[int] = Field(default=None, description="关联子任务ID")
    subtask_title: str = Field(default="", description="子任务标题")
    goal_definition: str = Field(default="", description="目标描述")
    user_id: int = Field(default=0, description="用户ID")

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl_seconds

    def to_prompt_context(self) -> str:
        return (
            f"⚠️ 历史经验（置信度 {self.confidence:.0%}）：\n"
            f"- 失败类型: {self.failure_type.value}\n"
            f"- 触发条件: {self.trigger_condition}\n"
            f"- 避免: {self.what_not_to_do}\n"
            f"- 建议: {self.suggested_strategy}"
        )

    def to_mysql_dict(self) -> dict:
        """转为 MySQL 存储格式"""
        return {
            "user_id": self.user_id,
            "failure_type": self.failure_type.value,
            "trigger_cond": self.trigger_condition[:500],
            "what_not_to_do": self.what_not_to_do[:500],
            "suggested_strategy": self.suggested_strategy[:500],
            "confidence": int(self.confidence * 100),
            "scope_tags": self.scope_tags,
            "subtask_id": self.subtask_id or 0,
            "subtask_title": self.subtask_title[:256],
            "goal_definition": self.goal_definition[:1000],
            "retry_count": self.retry_count,
            "was_successful": 0,
            "ttl_seconds": self.ttl_seconds,
            "expired_at": datetime.utcnow() + timedelta(seconds=self.ttl_seconds),
        }

    def to_redis_dict(self) -> dict:
        """转为 Redis 存储格式"""
        return {
            "failure_type": self.failure_type.value,
            "trigger_condition": self.trigger_condition,
            "what_not_to_do": self.what_not_to_do,
            "suggested_strategy": self.suggested_strategy,
            "confidence": self.confidence,
            "scope_tags": self.scope_tags,
            "subtask_id": self.subtask_id,
            "subtask_title": self.subtask_title,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
        }


# ── 失败分析器 ───────────────────────────────────────────

class FailureAnalyzer:
    """失败分析器 — 检测失败 + 生成结构化反思"""

    @staticmethod
    def analyze_from_guardrail(
        subtask_title: str, subtask_id: int,
        answer_text: str, guardrail_reason: str,
    ) -> Reflection:
        if "过短" in guardrail_reason or "为空" in guardrail_reason:
            return Reflection(
                failure_type=FailureType.EMPTY_OUTPUT,
                trigger_condition=f"子任务「{subtask_title}」输出为空或过短",
                what_not_to_do="不要只输出承诺性回复（'我来帮你...'），必须输出实质内容",
                suggested_strategy="先调用工具获取数据，再基于工具结果整理输出",
                confidence=0.9, scope_tags=["guardrail", "empty_output"], ttl_seconds=1800,
                subtask_id=subtask_id, subtask_title=subtask_title,
            )
        if "失败标记" in guardrail_reason:
            return Reflection(
                failure_type=FailureType.TOOL_ERROR,
                trigger_condition=f"子任务「{subtask_title}」工具调用失败",
                what_not_to_do="不要在工具失败后直接输出'抱歉'，应该尝试降级策略",
                suggested_strategy="工具不可用时，基于已有知识直接回答，并注明降级",
                confidence=0.8, scope_tags=["guardrail", "tool_failure"], ttl_seconds=1800,
                subtask_id=subtask_id, subtask_title=subtask_title,
            )
        if "承诺性" in guardrail_reason:
            return Reflection(
                failure_type=FailureType.INCOMPLETE,
                trigger_condition=f"子任务「{subtask_title}」输出为承诺性回复",
                what_not_to_do="不要说'我来帮你搜索'，直接调用工具",
                suggested_strategy="直接调用工具获取数据，输出工具结果的整理",
                confidence=0.9, scope_tags=["guardrail", "promise_only"], ttl_seconds=1800,
                subtask_id=subtask_id, subtask_title=subtask_title,
            )
        return Reflection(
            failure_type=FailureType.GUARDRAIL_FAIL,
            trigger_condition=f"子任务「{subtask_title}」未通过质量校验: {guardrail_reason}",
            what_not_to_do="不要忽略输出质量要求",
            suggested_strategy="严格按照子任务要求的格式和内容输出",
            confidence=0.6, scope_tags=["guardrail"], ttl_seconds=1800,
            subtask_id=subtask_id, subtask_title=subtask_title,
        )

    @staticmethod
    def analyze_from_llm_error(
        subtask_title: str, subtask_id: int, error_message: str,
    ) -> Reflection:
        if "timeout" in error_message.lower() or "超时" in error_message:
            return Reflection(
                failure_type=FailureType.TIMEOUT,
                trigger_condition=f"子任务「{subtask_title}」LLM 调用超时",
                what_not_to_do="不要发送过长的 prompt",
                suggested_strategy="简化 prompt，减少上下文长度",
                confidence=0.8, scope_tags=["llm", "timeout"], ttl_seconds=3600,
                subtask_id=subtask_id, subtask_title=subtask_title,
            )
        if "rate" in error_message.lower() or "429" in error_message:
            return Reflection(
                failure_type=FailureType.LLM_ERROR,
                trigger_condition=f"子任务「{subtask_title}」触发速率限制",
                what_not_to_do="不要短时间内大量调用 LLM",
                suggested_strategy="等待后重试，或减少并行调用",
                confidence=0.9, scope_tags=["llm", "rate_limit"], ttl_seconds=600,
                subtask_id=subtask_id, subtask_title=subtask_title,
            )
        return Reflection(
            failure_type=FailureType.LLM_ERROR,
            trigger_condition=f"子任务「{subtask_title}」LLM 调用失败: {error_message[:100]}",
            what_not_to_do="不要重复相同的调用参数",
            suggested_strategy="检查输入格式，简化请求，或降级到备用模型",
            confidence=0.5, scope_tags=["llm"], ttl_seconds=1800,
            subtask_id=subtask_id, subtask_title=subtask_title,
        )

    @staticmethod
    def analyze_from_eval(
        subtask_title: str, subtask_id: int, eval_reason: str,
    ) -> Reflection:
        return Reflection(
            failure_type=FailureType.IRRELEVANT,
            trigger_condition=f"目标评估未达成: {eval_reason[:100]}",
            what_not_to_do="不要偏离原始目标",
            suggested_strategy="回顾原始目标，检查是否有遗漏的子任务",
            confidence=0.7, scope_tags=["eval", "goal_miss"], ttl_seconds=3600,
            subtask_id=subtask_id, subtask_title=subtask_title,
        )


# ── 自愈记忆系统（Redis 短期 + MySQL 长期）────────────────

class HealingMemory:
    """自愈记忆系统 — Redis 短期 + MySQL 长期

    Redis: 当前 Goal 内的反思（TTL 30min，重启不丢）
    MySQL: 跨 Goal 的高置信度反思（持久化，可统计）
    """

    REDIS_KEY_PREFIX = "healing:goal:"
    REDIS_TTL = 1800  # 30 分钟

    async def store(self, reflection: Reflection, goal_id: str = ""):
        """存储反思到 Redis + MySQL"""
        # 1. Redis 短期记忆
        if goal_id:
            try:
                from app.core.redis_client import get_redis
                redis = get_redis()
                key = f"{self.REDIS_KEY_PREFIX}{goal_id}"
                data = reflection.to_redis_dict()
                await redis.rpush(key, json.dumps(data, ensure_ascii=False))
                await redis.expire(key, self.REDIS_TTL)
                logger.info(f"[healing_memory] Redis 存储: {reflection.failure_type.value} goal={goal_id}")
            except Exception as e:
                logger.warning(f"[healing_memory] Redis 存储失败: {e}")

        # 2. MySQL 长期记忆（高置信度反思才持久化）
        if reflection.confidence >= 0.7:
            try:
                from app.core.database import AsyncSessionLocal
                from app.repository.healing_reflection_repo import HealingReflectionRepository
                async with AsyncSessionLocal() as db:
                    repo = HealingReflectionRepository()
                    await repo.create(db, reflection.to_mysql_dict())
                    await db.commit()
                    logger.info(f"[healing_memory] MySQL 存储: {reflection.failure_type.value} "
                                f"confidence={reflection.confidence}")
            except Exception as e:
                logger.warning(f"[healing_memory] MySQL 存储失败: {e}")

    async def recall_from_redis(self, goal_id: str) -> list[Reflection]:
        """从 Redis 检索当前 Goal 的反思"""
        if not goal_id:
            return []
        try:
            from app.core.redis_client import get_redis
            redis = get_redis()
            key = f"{self.REDIS_KEY_PREFIX}{goal_id}"
            items = await redis.lrange(key, 0, -1)
            reflections = []
            for item in items:
                try:
                    data = json.loads(item)
                    # 重建 Reflection（跳过过期的）
                    r = Reflection(
                        failure_type=data["failure_type"],
                        trigger_condition=data["trigger_condition"],
                        what_not_to_do=data["what_not_to_do"],
                        suggested_strategy=data["suggested_strategy"],
                        confidence=data.get("confidence", 0.7),
                        scope_tags=data.get("scope_tags", []),
                        subtask_id=data.get("subtask_id"),
                        subtask_title=data.get("subtask_title", ""),
                        retry_count=data.get("retry_count", 0),
                        created_at=data.get("created_at", time.time()),
                    )
                    if not r.is_expired():
                        reflections.append(r)
                except Exception:
                    continue
            return reflections
        except Exception as e:
            logger.warning(f"[healing_memory] Redis 检索失败: {e}")
            return []

    async def recall_from_mysql(
        self, user_id: int, scope_tags: list[str] = None, limit: int = 3,
    ) -> list[Reflection]:
        """从 MySQL 检索相关反思"""
        try:
            from app.core.database import AsyncSessionLocal
            from app.repository.healing_reflection_repo import HealingReflectionRepository
            async with AsyncSessionLocal() as db:
                repo = HealingReflectionRepository()
                records = await repo.find_active_by_user(db, user_id=user_id, limit=limit)
                reflections = []
                for rec in records:
                    # 作用域匹配
                    if scope_tags:
                        rec_tags = set(rec.scope_tags or [])
                        if not set(scope_tags).intersection(rec_tags):
                            continue
                    r = Reflection(
                        failure_type=rec.failure_type,
                        trigger_condition=rec.trigger_cond,
                        what_not_to_do=rec.what_not_to_do,
                        suggested_strategy=rec.suggested_strategy,
                        confidence=rec.confidence / 100,
                        scope_tags=rec.scope_tags or [],
                        subtask_id=rec.subtask_id,
                        subtask_title=rec.subtask_title,
                        retry_count=rec.retry_count,
                        created_at=rec.created_at.timestamp() if rec.created_at else time.time(),
                    )
                    if not r.is_expired():
                        reflections.append(r)
                return reflections
        except Exception as e:
            logger.warning(f"[healing_memory] MySQL 检索失败: {e}")
            return []

    async def recall(
        self, user_id: int = 0, goal_id: str = "",
        scope_tags: list[str] = None, limit: int = 3,
    ) -> list[Reflection]:
        """统一检索入口 — Redis 优先，MySQL 补充"""
        results = []
        # 1. Redis 短期记忆（当前 Goal 内的反思，最相关）
        if goal_id:
            redis_results = await self.recall_from_redis(goal_id)
            results.extend(redis_results)

        # 2. MySQL 长期记忆（跨 Goal 的历史反思）
        if user_id and len(results) < limit:
            mysql_results = await self.recall_from_mysql(
                user_id, scope_tags=scope_tags, limit=limit - len(results),
            )
            results.extend(mysql_results)

        # 按置信度排序
        results.sort(key=lambda r: -r.confidence)
        return results[:limit]

    async def mark_successful(self, user_id: int, subtask_id: int):
        """标记反思最终导致了成功（直接查询，不遍历）"""
        try:
            from app.core.database import AsyncSessionLocal
            from app.repository.healing_reflection_repo import HealingReflectionRepository
            async with AsyncSessionLocal() as db:
                repo = HealingReflectionRepository()
                # 直接用 find_active_by_user 过滤，减少查询量
                records = await repo.find_active_by_user(
                    db, user_id=user_id, limit=50,
                )
                for rec in records:
                    if rec.subtask_id == subtask_id:
                        await repo.mark_successful(db, rec.id)
                        await db.commit()
                        logger.info(f"[healing_memory] 反思标记成功: subtask_id={subtask_id}")
                        break
        except Exception as e:
            logger.debug(f"[healing_memory] 标记成功失败: {e}")

    async def to_prompt_context(
        self, user_id: int = 0, goal_id: str = "",
        scope_tags: list[str] = None,
    ) -> str:
        """将相关反思转化为 prompt 注入文本"""
        reflections = await self.recall(user_id=user_id, goal_id=goal_id, scope_tags=scope_tags)
        if not reflections:
            return ""
        lines = ["\n═══════════════════════════════════════════",
                 "【自愈记忆 — 历史失败经验】",
                 "以下是从过去的失败中学到的经验，请避免重复这些错误："]
        for i, r in enumerate(reflections[:3], 1):
            lines.append(f"\n经验 {i}:")
            lines.append(r.to_prompt_context())
        lines.append("═══════════════════════════════════════════\n")
        return "\n".join(lines)


# ── 自愈策略 ─────────────────────────────────────────────

MAX_RETRY_COUNT = 3


class HealingStrategy:
    """自愈策略 — 决策与注入"""

    @staticmethod
    def should_retry(reflection: Reflection, current_retry: int) -> bool:
        if current_retry >= MAX_RETRY_COUNT:
            logger.warning(f"[healing_strategy] 已达最大重试次数 ({MAX_RETRY_COUNT})")
            return False
        if reflection.confidence < 0.3:
            return False
        if reflection.failure_type == FailureType.BUDGET_EXCEEDED:
            return False
        return True

    @staticmethod
    def build_retry_prompt(
        original_prompt: str, reflection: Reflection, failed_subtask_title: str,
    ) -> str:
        return f"""{original_prompt}

═══════════════════════════════════════════
【自愈指令 — 第 {reflection.retry_count + 1} 次重试】
上次子任务「{failed_subtask_title}」执行失败。

{reflection.to_prompt_context()}

本次执行要求：
1. 严格按照上述「建议策略」执行，不要重复上次的错误
2. 如果是工具问题，尝试降级策略（基于已有知识回答）
3. 如果是输出质量问题，确保输出完整、有实质内容
4. 完成后输出状态标记: • [子任务] - [done] (100%)
═══════════════════════════════════════════"""


# ── 模块级函数 ───────────────────────────────────────────

_healing_memory = HealingMemory()


def get_healing_memory() -> HealingMemory:
    return _healing_memory


def analyze_failure(
    subtask_title: str, subtask_id: int,
    failure_source: str,
    answer_text: str = "", error_message: str = "",
    guardrail_reason: str = "",
    user_id: int = 0, goal_definition: str = "",
) -> Reflection:
    """统一的失败分析入口"""
    if failure_source == "guardrail":
        reflection = FailureAnalyzer.analyze_from_guardrail(
            subtask_title, subtask_id, answer_text, guardrail_reason,
        )
    elif failure_source == "llm_error":
        reflection = FailureAnalyzer.analyze_from_llm_error(
            subtask_title, subtask_id, error_message,
        )
    elif failure_source == "eval":
        reflection = FailureAnalyzer.analyze_from_eval(
            subtask_title, subtask_id, error_message,
        )
    else:
        reflection = Reflection(
            failure_type=FailureType.UNKNOWN,
            trigger_condition=f"未知失败: {error_message[:100]}",
            what_not_to_do="不要忽略错误继续执行",
            suggested_strategy="检查错误原因，尝试简化任务或降级处理",
            confidence=0.3, scope_tags=["unknown"],
            subtask_id=subtask_id, subtask_title=subtask_title,
        )

    # 注入用户和目标信息
    reflection.user_id = user_id
    reflection.goal_definition = goal_definition

    return reflection
