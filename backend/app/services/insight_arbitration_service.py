"""Insight 冲突仲裁引擎 — 借鉴 GraphMem temporal precedence + Hindsight CARA

设计动机:
  - 新证据与旧 Insight 矛盾时，通过仲裁公式决定替代/保留/合并
  - temporal precedence: 更新的证据有额外权重（recency bonus）
  - 级联深度保护: cascade_supersede max_depth=3 防循环引用
  - 演化历史审计: 每次变更记录到 memory_insight_history

仲裁公式（修正版，加入 recency 因子）:
  old_strength = min(evidence_count * 10, 50) + confidence * 0.5
  new_strength = len(obs_ids) * 15 + 30 + 10  # recency bonus
  新证据胜出 → LLM 生成合并 Insight → 旧 Insight superseded
  旧 Insight 胜出 → 仅记录矛盾 → confidence 微调

参考:
  - GraphMem (2026): temporal precedence 自动替代
  - Hindsight CARA: 背景合并 / 冲突解决
  - MAGMA (ACL 2026 Main): 多图正交表示
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.memory_insight import MemoryInsight
from app.models.insight_history import MemoryInsightHistory
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_CASCADE_DEPTH = 3  # 级联替代最大深度


class InsightArbitrationService:
    """Insight 冲突仲裁引擎"""

    async def arbitrate_contradiction(
        self,
        db: AsyncSession,
        old_insight: MemoryInsight,
        new_evidence_text: str,
        new_evidence_obs_ids: List[int],
        contradiction_reason: str,
        user_id: int = 0,
    ) -> dict:
        """仲裁新证据与旧 Insight 的矛盾

        Args:
            db: 数据库会话
            old_insight: 被矛盾的旧 Insight
            new_evidence_text: 新证据文本
            new_evidence_obs_ids: 新证据关联的 observation ID 列表
            contradiction_reason: 矛盾原因描述
            user_id: 用户 ID

        Returns:
            {"action": "superseded"|"recorded", "new_insight_id": int|None, "reason": str}
        """
        # 仲裁公式（修正版：加入 recency bonus）
        old_strength = min(old_insight.evidence_count * 10, 50) + old_insight.confidence * 0.5
        # 新证据有 recency bonus（GraphMem temporal precedence）
        new_strength = len(new_evidence_obs_ids) * 15 + 30 + 10  # +10 recency bonus

        logger.info(
            f"[arbitration] old_id={old_insight.id} old_strength={old_strength:.1f} "
            f"new_strength={new_strength:.1f} reason={contradiction_reason[:50]}"
        )

        if new_strength > old_strength:
            # 新证据胜出 → 创建合并 Insight + 旧 Insight superseded
            new_insight = await self._create_merged_insight(
                db, old_insight, new_evidence_text, new_evidence_obs_ids,
                contradiction_reason, user_id,
            )
            if new_insight:
                # 标记旧 Insight 为 superseded
                old_insight.status = "superseded"
                old_insight.superseded_by = new_insight.id

                # 记录审计
                await self.record_history(
                    db, old_insight.id, "superseded",
                    old_confidence=old_insight.confidence,
                    new_confidence=0,
                    reason=f"被新证据替代: {contradiction_reason[:200]}",
                    trigger_obs_ids=new_evidence_obs_ids,
                )
                await self.record_history(
                    db, new_insight.id, "created",
                    old_confidence=0,
                    new_confidence=new_insight.confidence,
                    reason=f"合并创建，替代 insight_id={old_insight.id}",
                    trigger_obs_ids=new_evidence_obs_ids,
                )

                # 级联替代（保护 max_depth=3）
                await self.cascade_supersede(db, old_insight.id, new_insight.id, depth=0)

                await db.flush()
                return {
                    "action": "superseded",
                    "new_insight_id": new_insight.id,
                    "reason": contradiction_reason,
                }

        # 旧 Insight 胜出 → 仅记录矛盾 + confidence 微调
        old_insight.confidence = max(0, old_insight.confidence - 5)
        old_insight.evidence_count += 1  # 矛盾也是证据

        await self.record_history(
            db, old_insight.id, "contradicted",
            old_confidence=old_insight.confidence + 5,
            new_confidence=old_insight.confidence,
            reason=f"被矛盾但保留（证据不足替代）: {contradiction_reason[:200]}",
            trigger_obs_ids=new_evidence_obs_ids,
        )

        await db.flush()
        return {
            "action": "recorded",
            "new_insight_id": None,
            "reason": f"旧 Insight 证据充分，仅记录矛盾: {contradiction_reason[:100]}",
        }

    async def _create_merged_insight(
        self,
        db: AsyncSession,
        old_insight: MemoryInsight,
        new_evidence_text: str,
        new_evidence_obs_ids: List[int],
        contradiction_reason: str,
        user_id: int,
    ) -> Optional[MemoryInsight]:
        """创建合并 Insight（替代旧的矛盾 Insight）"""
        # 简化合并：基于新证据内容创建新 Insight
        merged_content = (
            f"[更新] {new_evidence_text[:400]}\n\n"
            f"原洞察: {old_insight.content[:200]}\n"
            f"矛盾原因: {contradiction_reason[:200]}"
        )

        new_insight = MemoryInsight(
            user_id=user_id,
            content=merged_content,
            insight_type=old_insight.insight_type,
            confidence=max(50, min(90, 60 + len(new_evidence_obs_ids) * 5)),
            evidence_count=len(new_evidence_obs_ids),
            source_period="最新提炼",
            status="active",
            contradicts_id=old_insight.id,
            merged_from=str(old_insight.id),
        )
        db.add(new_insight)
        await db.flush()
        return new_insight

    async def record_history(
        self,
        db: AsyncSession,
        insight_id: int,
        action: str,
        old_confidence: int = 0,
        new_confidence: int = 0,
        reason: str = "",
        trigger_obs_ids: List[int] = None,
    ):
        """记录 Insight 变更审计日志"""
        history = MemoryInsightHistory(
            insight_id=insight_id,
            action=action,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            reason=reason[:1000],
            trigger_obs_ids=",".join(str(i) for i in (trigger_obs_ids or [])),
        )
        db.add(history)

    async def cascade_supersede(
        self, db: AsyncSession, old_id: int, new_id: int, depth: int = 0,
    ):
        """级联替代: 将被旧 Insight 替代的其他 Insight 也指向新 Insight

        保护: max_depth=3 防止循环引用
        """
        if depth >= MAX_CASCADE_DEPTH:
            logger.warning(f"[cascade_supersede] 达到最大深度 {MAX_CASCADE_DEPTH}，停止级联")
            return

        # 查找所有 superseded_by == old_id 的 Insight
        stmt = select(MemoryInsight).where(
            MemoryInsight.superseded_by == old_id,
            MemoryInsight.is_deleted == 0,
        )
        result = await db.execute(stmt)
        cascaded = list(result.scalars().all())

        for insight in cascaded:
            insight.superseded_by = new_id
            logger.info(
                f"[cascade_supersede] depth={depth} insight_id={insight.id} "
                f"superseded_by: {old_id} → {new_id}"
            )
            await self.cascade_supersede(db, insight.id, new_id, depth + 1)

    async def get_insight_history(
        self, db: AsyncSession, insight_id: int, limit: int = 50,
    ) -> List[dict]:
        """获取 Insight 演化历史"""
        stmt = (
            select(MemoryInsightHistory)
            .where(
                MemoryInsightHistory.insight_id == insight_id,
                MemoryInsightHistory.is_deleted == 0,
            )
            .order_by(MemoryInsightHistory.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        return [
            {
                "id": h.id,
                "insightId": h.insight_id,
                "action": h.action,
                "oldConfidence": h.old_confidence,
                "newConfidence": h.new_confidence,
                "reason": h.reason,
                "triggerObsIds": h.trigger_obs_ids,
                "createdAt": str(h.created_at) if h.created_at else None,
            }
            for h in rows
        ]

    async def get_conflicts(
        self, db: AsyncSession, user_id: int = 0, limit: int = 50,
    ) -> List[dict]:
        """获取矛盾 Insight 列表（有 contradicts_id 或 status=superseded 的）"""
        stmt = select(MemoryInsight).where(
            MemoryInsight.is_deleted == 0,
            MemoryInsight.user_id == user_id,
        )
        # 有矛盾关系或被替代的 Insight
        from sqlalchemy import or_
        stmt = stmt.where(or_(
            MemoryInsight.contradicts_id > 0,
            MemoryInsight.superseded_by > 0,
            MemoryInsight.status == "superseded",
        )).order_by(MemoryInsight.created_at.desc()).limit(limit)

        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        return [
            {
                "id": i.id,
                "content": i.content,
                "insightType": i.insight_type,
                "confidence": i.confidence,
                "status": i.status,
                "contradictsId": i.contradicts_id,
                "supersededBy": i.superseded_by,
                "contradictionReason": i.contradiction_reason,
                "mergedFrom": i.merged_from,
                "createdAt": str(i.created_at) if i.created_at else None,
            }
            for i in rows
        ]
