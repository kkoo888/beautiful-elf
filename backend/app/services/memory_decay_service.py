"""ACT-R 认知衰减引擎 — 记忆激活度管理

借鉴 ACT-R (Anderson, 2025) 认知激活度模型:
  - A ≈ ln(access_count + 1) - d * ln(age_hours + 1) + (importance - 5) * 0.05
  - activation = sigmoid(A) ∈ (0, 1)
  - 动态半衰期: half_life = 30天 × (importance / 5.0)

策略: lazy + batch 混合
  - 检索时: lazy 修正 activation（在 memory_manager._apply_temporal_decay 中）
  - sweep: 批量扫描标记 dormant（本服务）
  - 存量回填: 首次运行时为无 activation 的 payload 补默认值

Qdrant payload 约定:
  - activation: float, 默认 1.0
  - decay_status: "active" | "dormant" | "archived"
"""
import math
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.mappers.qdrant_mapper import QdrantMapper

logger = get_logger(__name__)

MEMORY_COLLECTION = "memory_vectors"
DORMANT_THRESHOLD = 0.1  # activation 低于此值标记为 dormant
DECAY_RATE = 0.5  # ACT-R 标准衰减参数 d


class MemoryDecayService:
    """ACT-R 认知衰减服务"""

    @staticmethod
    def calculate_activation(
        access_count: int, age_hours: float, importance: int = 5,
    ) -> float:
        """标准 ACT-R 激活度公式

        A ≈ ln(access_count + 1) - d * ln(age_hours + 1) + (importance - 5) * 0.05
        activation = 1 / (1 + exp(-A))  # sigmoid 归一化到 (0, 1)

        Args:
            access_count: 被检索命中次数
            age_hours: 距离创建的小时数
            importance: 重要度 1-10（从 Qdrant payload 读）

        Returns:
            activation ∈ (0, 1)
        """
        A = (
            math.log(access_count + 1)
            - DECAY_RATE * math.log(age_hours + 1)
            + (importance - 5) * 0.05
        )
        # sigmoid 归一化
        activation = 1.0 / (1.0 + math.exp(-A))
        return round(activation, 4)

    @staticmethod
    def dynamic_half_life_days(importance: int, base_days: int = 30) -> float:
        """动态半衰期: importance=10 → 60天; importance=5 → 30天; importance=1 → 6天"""
        return base_days * (importance / 5.0)

    def batch_mark_dormant(self, qdrant: 'QdrantMapper', threshold: float = DORMANT_THRESHOLD) -> int:
        """批量扫描 Qdrant，将 activation < threshold 的 active 记忆标记为 dormant

        使用 scroll 分页处理，避免一次性加载全部数据。
        只修改 Qdrant payload，不逐条重算 ACT-R（依赖 lazy 修正）。

        Returns:
            标记为 dormant 的记忆数量
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        marked = 0
        offset = None
        batch_size = 100

        while True:
            # 只扫描 active 状态的记忆
            scroll_filter = Filter(must=[
                FieldCondition(key="decay_status", match=MatchValue(value="active")),
            ])

            try:
                points, next_offset = qdrant._client.scroll(
                    collection_name=MEMORY_COLLECTION,
                    scroll_filter=scroll_filter,
                    limit=batch_size,
                    offset=offset,
                    with_vectors=False,
                )
            except Exception as e:
                logger.warning(f"[decay_sweep] scroll 失败: {e}")
                break

            if not points:
                break

            # 找出需要标记 dormant 的点
            dormant_ids = []
            for p in points:
                payload = p.payload or {}
                activation = float(payload.get("activation", 1.0))
                saved_at = payload.get("saved_at", "")
                importance = int(payload.get("importance", 5))

                # 如果 payload 有 activation 且低于阈值
                if activation < threshold:
                    dormant_ids.append(str(p.id))
                    continue

                # 对于没有 activation 字段的旧数据，用时间估算
                if "activation" not in payload and saved_at:
                    try:
                        saved_dt = datetime.fromisoformat(
                            saved_at.replace("Z", "+00:00").replace("+00:00", "")
                        )
                        age_hours = (datetime.utcnow() - saved_dt).total_seconds() / 3600
                        est_activation = self.calculate_activation(0, age_hours, importance)
                        if est_activation < threshold:
                            dormant_ids.append(str(p.id))
                    except (ValueError, TypeError):
                        pass

            # 批量更新 Qdrant payload
            if dormant_ids:
                try:
                    qdrant._client.set_payload(
                        collection_name=MEMORY_COLLECTION,
                        payload={"decay_status": "dormant"},
                        points=dormant_ids,
                    )
                    marked += len(dormant_ids)
                except Exception as e:
                    logger.warning(f"[decay_sweep] 批量更新失败: {e}")

            if next_offset is None:
                break
            offset = next_offset

        return marked

    def backfill_existing(self, qdrant) -> int:
        """存量回填: 为缺少 activation/decay_status 的 Qdrant payload 补默认值

        幂等操作: 只处理缺少字段的 payload。

        Returns:
            回填的 payload 数量
        """
        backfilled = 0
        offset = None
        batch_size = 100

        while True:
            try:
                points, next_offset = qdrant._client.scroll(
                    collection_name=MEMORY_COLLECTION,
                    scroll_filter=None,
                    limit=batch_size,
                    offset=offset,
                    with_vectors=False,
                )
            except Exception as e:
                logger.warning(f"[backfill] scroll 失败: {e}")
                break

            if not points:
                break

            update_ids = []
            for p in points:
                payload = p.payload or {}
                if "activation" not in payload or "decay_status" not in payload:
                    update_ids.append(str(p.id))

            if update_ids:
                try:
                    qdrant._client.set_payload(
                        collection_name=MEMORY_COLLECTION,
                        payload={
                            "activation": 1.0,
                            "decay_status": "active",
                        },
                        points=update_ids,
                    )
                    backfilled += len(update_ids)
                except Exception as e:
                    logger.warning(f"[backfill] 批量更新失败: {e}")

            if next_offset is None:
                break
            offset = next_offset

        return backfilled

    @staticmethod
    def sync_qdrant_activation(
        qdrant, point_id: str, activation: float, decay_status: str = "active",
    ):
        """同步单条记忆的 activation 到 Qdrant payload"""
        try:
            qdrant._client.set_payload(
                collection_name=MEMORY_COLLECTION,
                payload={"activation": activation, "decay_status": decay_status},
                points=[point_id],
            )
        except Exception as e:
            logger.warning(f"[decay] sync_qdrant_activation 失败: {point_id}: {e}")

    def archive_old_dormant(self, qdrant, base_days: int = 90) -> int:
        """将 dormant 超过保留期的记忆标记为 archived

        分级保留策略（重要记忆永不删除）：
          - importance 1-4: 90 天后归档
          - importance 5-7: 180 天后归档
          - importance 8-10: 永不归档（高价值记忆保留）

        幂等操作：已 archived 的不会重复处理。

        Returns:
            标记为 archived 的记忆数量
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        from datetime import timedelta

        # importance → 保留天数映射
        RETENTION_DAYS = {
            range(1, 5): 90,     # 低价值: 90 天
            range(5, 8): 180,    # 中价值: 180 天
            range(8, 11): 9999,  # 高价值: 永不归档（用超大值兜底）
        }

        archived = 0
        offset = None
        batch_size = 100
        now = datetime.utcnow()

        while True:
            scroll_filter = Filter(must=[
                FieldCondition(key="decay_status", match=MatchValue(value="dormant")),
            ])

            try:
                points, next_offset = qdrant._client.scroll(
                    collection_name=MEMORY_COLLECTION,
                    scroll_filter=scroll_filter,
                    limit=batch_size,
                    offset=offset,
                    with_vectors=False,
                )
            except Exception as e:
                logger.warning(f"[archive] scroll 失败: {e}")
                break

            if not points:
                break

            archive_ids = []
            for p in points:
                payload = p.payload or {}
                saved_at = payload.get("saved_at", "")
                importance = int(payload.get("importance", 5))
                if not saved_at:
                    continue

                # 根据 importance 确定保留天数
                retention_days = base_days  # 默认
                for importance_range, days in RETENTION_DAYS.items():
                    if importance in importance_range:
                        retention_days = days
                        break

                # 高价值记忆跳过归档
                if retention_days >= 9999:
                    continue

                cutoff = now - timedelta(days=retention_days)
                try:
                    saved_dt = datetime.fromisoformat(
                        saved_at.replace("Z", "+00:00").replace("+00:00", "")
                    )
                    if saved_dt < cutoff:
                        archive_ids.append(str(p.id))
                except (ValueError, TypeError):
                    pass

            if archive_ids:
                try:
                    qdrant._client.set_payload(
                        collection_name=MEMORY_COLLECTION,
                        payload={"decay_status": "archived"},
                        points=archive_ids,
                    )
                    archived += len(archive_ids)
                except Exception as e:
                    logger.warning(f"[archive] 批量更新失败: {e}")

            if next_offset is None:
                break
            offset = next_offset

        return archived

    def cleanup_archived(self, qdrant) -> int:
        """物理删除所有 archived 记忆

        最终清理步骤：archived 记忆从 Qdrant 永久移除。
        幂等操作：无 archived 记忆时返回 0。

        Returns:
            物理删除的记忆数量
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList

        deleted = 0
        offset = None
        batch_size = 100

        while True:
            scroll_filter = Filter(must=[
                FieldCondition(key="decay_status", match=MatchValue(value="archived")),
            ])

            try:
                points, next_offset = qdrant._client.scroll(
                    collection_name=MEMORY_COLLECTION,
                    scroll_filter=scroll_filter,
                    limit=batch_size,
                    offset=offset,
                    with_vectors=False,
                )
            except Exception as e:
                logger.warning(f"[cleanup] scroll 失败: {e}")
                break

            if not points:
                break

            ids_to_delete = [p.id for p in points]
            if ids_to_delete:
                try:
                    qdrant._client.delete(
                        collection_name=MEMORY_COLLECTION,
                        points_selector=PointIdsList(points=ids_to_delete),
                    )
                    deleted += len(ids_to_delete)
                except Exception as e:
                    logger.warning(f"[cleanup] 批量删除失败: {e}")

            if next_offset is None:
                break
            offset = next_offset

        return deleted
