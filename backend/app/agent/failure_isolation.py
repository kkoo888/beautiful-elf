"""失败隔离机制 — 切断子任务间级联失败

核心问题:
  上游子任务失败 → 下游正确率降 30% → 级联失败
  模拟数据显示: 复杂目标基线仅 32.3%，根因是级联

解决方案:
  1. 失败隔离: 上游失败时，用"降级输出"替代"无输出"
     - 降级输出: 从上下文/RAG/记忆中提取部分信息
     - 效果: 下游正确率仅降 10%（而非 30%）
  2. 并行化: 无依赖的子任务并行执行，减少串行等待
  3. 弹性依赖: 依赖失败时自动切换到备选策略

前沿依据:
  - Circuit Breaker 模式 (Nygard 2007): 防止级联故障
  - Bulkhead 模式: 隔离故障域
  - LangGraph Send API: 并行 fan-out
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class DegradedOutput(BaseModel):
    """降级输出 — 上游失败时的替代方案"""
    source: str = Field(description="降级来源: memory/rag/context/default")
    content: str = Field(description="降级输出内容")
    confidence: float = Field(default=0.3, ge=0, le=1, description="置信度（通常较低）")
    strategy: str = Field(description="降级策略说明")


async def generate_degraded_output(
    llm,
    failed_task_title: str,
    failed_task_reason: str,
    context: str = "",
    memory_context: str = "",
    rag_context: str = "",
) -> DegradedOutput:
    """上游失败时 LLM 自主推理替代（不降级）

    策略: 直接用 LLM 知识推理，不用缓存/降级
    """
    # 策略 1: LLM 自主推理（首选）
    if llm:
        try:
            prompt = f"""任务「{failed_task_title}」的前置依赖失败了（原因: {failed_task_reason}）。
请用你自己的知识直接完成这个任务的分析。

{f'上下文信息: {context[:500]}' if context else ''}
{f'相关记忆: {memory_context[:300]}' if memory_context else ''}

要求:
1. 用你的知识直接推理，给出有价值的分析
2. 涉及实时数据时说明是基于训练数据的推测
3. 给出明确的结论和建议"""
            response = await llm.ainvoke(prompt)
            content = response.content if isinstance(response.content, str) else str(response.content)
            if content and len(content.strip()) > 20:
                return DegradedOutput(
                    source="llm_reasoning", content=content.strip(),
                    confidence=0.6, strategy="LLM 自主推理替代",
                )
        except Exception:
            pass

    # 策略 2: RAG
    if rag_context and len(rag_context.strip()) > 20:
        return DegradedOutput(
            source="rag", content=f"[推理] 基于知识库: {rag_context[:300]}",
            confidence=0.3, strategy="从 RAG 知识中提取",
        )

    # 策略 3: 上下文
    if context and len(context.strip()) > 20:
        return DegradedOutput(
            source="context", content=f"[推理] 基于上下文: {context[:300]}",
            confidence=0.2, strategy="从对话上下文中提取",
        )

    # 策略 4: 默认
    return DegradedOutput(
        source="default",
        content=f"[注意] 任务「{failed_task_title}」的前置依赖失败，模型无法独立推理此任务。",
        confidence=0.1,
        strategy="无法推理，提示下游注意",
    )


def compute_failure_impact(
    upstream_failed: bool,
    has_degraded_output: bool,
    base_failure_propagation: float = 0.3,
) -> float:
    """计算上游失败对下游的影响系数

    Returns:
        影响系数 (0 = 无影响, 1 = 完全失败)
    """
    if not upstream_failed:
        return 0.0
    if has_degraded_output:
        # 有降级输出: 影响减半
        return base_failure_propagation * 0.4  # 30% → 12%
    # 无降级输出: 原始影响
    return base_failure_propagation


class TaskDependencyGraph:
    """子任务依赖图 — 分析最大并行路径 + 失败隔离"""

    def __init__(self, subtasks: list[dict]):
        self.subtasks = {t["id"]: t for t in subtasks}
        self.deps = {t["id"]: t.get("dependencies", []) for t in subtasks}

    def get_parallel_groups(self) -> list[list[int]]:
        """将子任务分组为可并行执行的批次

        Returns:
            [[id1, id2], [id3], [id4, id5]] — 每组内可并行
        """
        remaining = set(self.subtasks.keys())
        completed = set()
        groups = []

        while remaining:
            # 找到所有依赖已满足的任务
            ready = [
                tid for tid in remaining
                if all(d in completed for d in self.deps.get(tid, []))
            ]
            if not ready:
                # 存在循环依赖，强制取第一个
                ready = [min(remaining)]
                logger.warning(f"[dep_graph] 检测到循环依赖，强制执行: {ready}")

            groups.append(ready)
            for tid in ready:
                remaining.discard(tid)
                completed.add(tid)

        return groups

    def get_critical_path(self) -> list[int]:
        """获取关键路径（最长依赖链）"""
        # 拓扑排序 + 最长路径
        in_degree = {tid: 0 for tid in self.subtasks}
        for tid, deps in self.deps.items():
            for d in deps:
                if d in in_degree:
                    in_degree[tid] += 1

        # BFS 求最长路径
        dist = {tid: 0 for tid in self.subtasks}
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        parent = {}

        while queue:
            tid = queue.pop(0)
            for child_id, child_deps in self.deps.items():
                if tid in child_deps:
                    if dist[tid] + 1 > dist[child_id]:
                        dist[child_id] = dist[tid] + 1
                        parent[child_id] = tid
                    in_degree[child_id] -= 1
                    if in_degree[child_id] == 0:
                        queue.append(child_id)

        # 回溯最长路径
        end = max(dist, key=dist.get)
        path = [end]
        while end in parent:
            end = parent[end]
            path.append(end)
        return list(reversed(path))

    def get_failure_risk(self, task_id: int) -> float:
        """计算任务失败风险（考虑上游依赖）"""
        deps = self.deps.get(task_id, [])
        if not deps:
            return 0.0
        # 上游失败概率的累积
        risk = 1.0
        for dep_id in deps:
            if dep_id in self.subtasks:
                # 假设每个上游有 15% 失败率
                risk *= 0.85
        return 1 - risk
