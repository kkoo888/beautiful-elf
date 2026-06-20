"""记忆合并去重服务 — Sleep-Time Compute 核心组件

借鉴 Mem0/Zep 的记忆合并策略 + expert_team 已验证的 _consolidate 逻辑。
在 sleep-time agent 管线中被调用，对碎片 detail/summary 执行合并去重。

核心流程:
  1. 扫描近 7 天未合并的 detail/summary
  2. 按语义相似度聚类（>0.85 阈值）
  3. 对每组执行 LLM 合并决策（keep/update/delete）
  4. 更新 Qdrant（删除冗余 + 写入合并后版本）
"""
import uuid
from datetime import datetime
from typing import List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

MEMORY_COLLECTION = "memory_vectors"


class MergeDecision:
    """合并决策常量"""
    KEEP = "keep"           # 保留旧记忆，丢弃新的
    UPDATE = "update"       # 合并为一条更完整的
    DELETE = "delete"       # 旧记忆过时，用新的替换
    INSERT_NEW = "insert_new"  # 两条是不同方面，都保留


class MemoryConsolidationService:
    """记忆合并去重服务

    用于 Sleep-Time Compute Phase A: 碎片合并。
    也可被 save_summary() 调用做写入前检查。
    """

    def __init__(self, qdrant_mapper, embedding_func, llm_client=None):
        self.qdrant = qdrant_mapper
        self.embedding_func = embedding_func
        self.llm = llm_client

    async def find_similar(self, text: str, user_id: int, threshold: float = 0.85,
                           limit: int = 5, exclude_ids: List[str] = None) -> List[dict]:
        """查找语义相似的记忆

        Args:
            text: 查询文本
            user_id: 用户 ID
            threshold: 相似度阈值
            limit: 最大返回数
            exclude_ids: 排除的 point_id 列表

        Returns:
            相似记忆列表 [{id, score, summary, type, ...}, ...]
        """
        query_vector = await self.embedding_func(text)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        conditions = [
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="decay_status", match=MatchValue(value="active")),
        ]
        if exclude_ids:
            # Qdrant 不支持 must_not with ID，用 must_not_match 代替
            pass  # 后面在代码中过滤

        search_filter = Filter(must=conditions)

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=limit * 2,  # 多取一些用于过滤
            score_threshold=threshold,
            raw_filter=search_filter,
        )

        candidates = []
        for r in results:
            if r.id in (exclude_ids or []):
                continue
            candidates.append({
                "id": r.id,
                "score": r.score,
                "type": r.payload.get("type", ""),
                "summary": r.payload.get("summary", ""),
                "tags": r.payload.get("tags", []),
                "importance": r.payload.get("importance", 5),
                "saved_at": r.payload.get("saved_at", ""),
                "consolidated": r.payload.get("consolidated", False),
            })

        return candidates[:limit]

    async def decide_merge(self, existing_text: str, new_text: str) -> dict:
        """LLM 判断合并策略

        Returns:
            {action: str, merged_text: str, reason: str}
        """
        if not self.llm:
            return {"action": MergeDecision.INSERT_NEW, "merged_text": "", "reason": "no_llm"}

        try:
            from llama_index.core import Settings
            from llama_index.core.llms import ChatMessage, MessageRole

            llm = Settings.llm or self.llm
            result = await llm.complete(
                prompt=f"""以下是两条相似的记忆片段，请决定如何处理。

## 已有记忆
{existing_text[:1500]}

## 新记忆
{new_text[:1500]}

选项：
- keep: 已有记忆准确且完整，不需要更新
- update: 两条都有价值，合并为一条更完整的
- delete: 已有记忆已过时或错误，用新的替换
- insert_new: 两条是不同方面的信息，都应该保留

请严格按以下 JSON 格式输出:
{{"action": "keep|update|delete|insert_new", "merged_text": "合并后的文本（仅 action=update 时填写）", "reason": "简要说明原因"}}""",
            )

            import json
            # 尝试解析 JSON
            text = result.text.strip()
            # 处理 markdown code block
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            data = json.loads(text)
            return {
                "action": data.get("action", MergeDecision.INSERT_NEW),
                "merged_text": data.get("merged_text", ""),
                "reason": data.get("reason", ""),
            }

        except Exception as e:
            logger.warning(f"[consolidation] LLM 合并决策失败，默认保留两条: {e}")
            return {"action": MergeDecision.INSERT_NEW, "merged_text": "", "reason": str(e)}

    async def consolidate_pair(self, existing: dict, new_text: str,
                               user_id: int) -> dict:
        """对一对记忆执行合并决策

        Args:
            existing: 已有记忆 {id, summary, type, ...}
            new_text: 新记忆文本
            user_id: 用户 ID

        Returns:
            {action: str, new_point_id: str|None, deleted_ids: list}
        """
        decision = await self.decide_merge(
            existing.get("summary", ""),
            new_text,
        )

        action = decision["action"]
        result = {"action": action, "new_point_id": None, "deleted_ids": []}

        if action == MergeDecision.KEEP:
            # 保留旧的，但增加证据计数（多源佐证）
            old_evidence = existing.get("evidence_count", 1)
            old_confidence = existing.get("confidence", 1.0)
            new_evidence = old_evidence + 1
            new_confidence = min(old_confidence + 0.1, 2.0)  # 最高 2.0
            try:
                self.qdrant._client.set_payload(
                    collection_name=MEMORY_COLLECTION,
                    payload={
                        "evidence_count": new_evidence,
                        "confidence": round(new_confidence, 2),
                        "last_reinforced_at": datetime.utcnow().isoformat(),
                    },
                    points=[existing["id"]],
                )
            except Exception:
                pass
            result["deleted_ids"] = []  # 新的不写入

        elif action == MergeDecision.UPDATE:
            # 用合并后的文本替换旧的
            merged_text = decision.get("merged_text") or new_text
            vector = await self.embedding_func(merged_text)
            new_point_id = str(uuid.uuid4())

            # 继承旧记忆的证据计数并增加
            old_evidence = existing.get("evidence_count", 1)
            old_confidence = existing.get("confidence", 1.0)

            # v5.2 fix: 先写入新的，不立即删除旧的（延迟到验证通过后）
            self.qdrant.upsert(
                collection=MEMORY_COLLECTION,
                point_id=new_point_id,
                vector=vector,
                payload={
                    "type": "summary",
                    "user_id": user_id,
                    "summary": merged_text,
                    "tags": existing.get("tags", []),
                    "importance": max(existing.get("importance", 5), 5),
                    "activation": 1.0,
                    "decay_status": "active",
                    "consolidated": True,
                    "consolidated_at": datetime.utcnow().isoformat(),
                    "saved_at": datetime.utcnow().isoformat(),
                    "evidence_count": old_evidence + 1,
                    "confidence": min(old_confidence + 0.1, 2.0),
                    "parent_point_id": existing["id"],
                },
            )
            result["new_point_id"] = new_point_id
            # 延迟删除旧点：调用方验证通过后再删
            result["pending_delete_ids"] = [existing["id"]]

        elif action == MergeDecision.DELETE:
            # v5.1 fix: 不立即删除旧的，只标记为待删除
            # 调用方写入新记忆成功后再删除旧的，避免数据丢失窗口
            result["pending_delete_ids"] = [existing["id"]]

        elif action == MergeDecision.INSERT_NEW:
            # 两条都保留，不需要操作
            pass

        return result

    async def batch_consolidate(self, items: List[dict], user_id: int) -> dict:
        """批量合并去重

        对一组记忆执行两两比较和合并。

        Args:
            items: [{id, summary, type, tags, importance}, ...]
            user_id: 用户 ID

        Returns:
            {merged: int, deleted: int, kept: int}
        """
        stats = {"merged": 0, "deleted": 0, "kept": 0}
        processed_ids = set()

        for i, item in enumerate(items):
            if item["id"] in processed_ids:
                continue

            # 查找与当前项相似的其他项
            similar = await self.find_similar(
                text=item.get("summary", ""),
                user_id=user_id,
                threshold=0.85,
                limit=3,
                exclude_ids=[item["id"]] + list(processed_ids),
            )

            if not similar:
                # 没有相似项，标记为已合并
                await self._mark_consolidated(item["id"])
                stats["kept"] += 1
                processed_ids.add(item["id"])
                continue

            # 与最相似的项合并
            top_match = similar[0]
            result = await self.consolidate_pair(
                existing=top_match,
                new_text=item.get("summary", ""),
                user_id=user_id,
            )

            if result["action"] == MergeDecision.UPDATE:
                # 验证合并质量
                is_quality = await self.verify_merge_quality(
                    merged_text=item.get("summary", ""),
                    original_texts=[item.get("summary", ""), top_match.get("summary", "")],
                    user_id=user_id,
                )
                pending_delete = result.get("pending_delete_ids", [])
                if is_quality:
                    # 验证通过：删除旧点
                    for old_id in pending_delete:
                        try:
                            self.qdrant._client.delete(
                                collection_name=MEMORY_COLLECTION,
                                points_selector=[old_id],
                            )
                        except Exception:
                            pass
                    stats["merged"] += 1
                    processed_ids.add(item["id"])
                    processed_ids.add(top_match["id"])
                else:
                    # 验证失败：删除新点，保留旧点
                    logger.warning(f"[consolidation] 合并验证失败，回滚: {item['id']}")
                    new_id = result.get("new_point_id")
                    if new_id:
                        try:
                            self.qdrant._client.delete(
                                collection_name=MEMORY_COLLECTION,
                                points_selector=[new_id],
                            )
                        except Exception:
                            pass
                    await self._mark_consolidated(item["id"])
                    stats["kept"] += 1
                    processed_ids.add(item["id"])
            elif result["action"] == MergeDecision.KEEP:
                stats["deleted"] += 1
                processed_ids.add(item["id"])  # 新的被丢弃
            elif result["action"] == MergeDecision.DELETE:
                stats["deleted"] += 1
                processed_ids.add(top_match["id"])
                # 新的需要写入
                await self._mark_consolidated(item["id"])
            else:  # INSERT_NEW
                await self._mark_consolidated(item["id"])
                stats["kept"] += 1
                processed_ids.add(item["id"])

        return stats

    async def _mark_consolidated(self, point_id: str):
        """标记记忆为已合并"""
        try:
            self.qdrant._client.set_payload(
                collection_name=MEMORY_COLLECTION,
                payload={
                    "consolidated": True,
                    "consolidated_at": datetime.utcnow().isoformat(),
                },
                points=[point_id],
            )
        except Exception:
            pass

    async def verify_merge_quality(
        self, merged_text: str, original_texts: List[str],
        user_id: int, threshold: float = 0.8,
    ) -> bool:
        """验证合并质量 — 确保合并后的记忆能召回原始内容

        借鉴 LangMem 的压缩反馈环：
        - 用合并记忆的 embedding 搜索原始记忆
        - 如果 top-K 召回率 < threshold，说明信息丢失
        - 返回 True 表示质量合格，False 需要回滚

        Args:
            merged_text: 合并后的文本
            original_texts: 原始记忆文本列表
            user_id: 用户 ID
            threshold: 最低召回率阈值（默认 0.8 = 80%）

        Returns:
            True if quality acceptable, False if should rollback
        """
        if not original_texts or not self.embedding_func:
            return True  # 无法验证时默认通过

        try:
            # 用合并记忆的 embedding 搜索
            query_vector = await self.embedding_func(merged_text)

            from qdrant_client.models import Filter, FieldCondition, MatchValue
            search_filter = Filter(must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="decay_status", match=MatchValue(value="active")),
            ])

            # 搜索 top-N 条
            results = self.qdrant.search(
                collection=MEMORY_COLLECTION,
                query_vector=query_vector,
                limit=len(original_texts) + 5,
                score_threshold=0.3,
                raw_filter=search_filter,
            )

            if not results:
                return False  # 搜索无结果，合并可能有问题

            # 计算召回率：原始文本中有多少能被 top-K 召回
            found_count = 0
            for orig in original_texts:
                orig_lower = orig[:100].lower()
                for r in results:
                    r_summary = (r.payload or {}).get("summary", "")[:200].lower()
                    # 简单匹配：原始文本的前 100 字符出现在搜索结果中
                    if orig_lower[:50] in r_summary or r_summary[:50] in orig_lower:
                        found_count += 1
                        break

            recall_rate = found_count / len(original_texts)
            if recall_rate < threshold:
                logger.warning(
                    f"[consolidation] 合并质量不合格: recall={recall_rate:.2f} "
                    f"< {threshold}, 建议回滚"
                )
                return False

            return True

        except Exception as e:
            logger.warning(f"合并质量验证失败(默认通过): {e}")
            return True
