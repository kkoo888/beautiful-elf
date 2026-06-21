"""LATS — Language Agent Tree Search (蒙特卡洛树搜索)

核心原理 (Zhou et al. 2023):
  MCTS + LLM 评估 + 反思回传
  Select(UCB) → Expand → Simulate(LLM评估) → Backpropagate

UCB 公式:
  UCB(node) = Q(node)/visits + c × √(ln(parent.visits) / visits)

与 ToT 的区别:
  - ToT: 一次性生成 N 条路径，选最优
  - LATS: 树搜索，每步探索/利用平衡，有回传机制
  - LATS 在复杂推理上 +20%，成本 5-20x
"""
import math
from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MCTSNode:
    """MCTS 树节点"""
    state: str
    parent: Optional['MCTSNode'] = None
    children: list = field(default_factory=list)
    value: float = 0.0
    visits: int = 0
    reflection: str = ""
    action: str = ""

    def ucb_score(self, c: float = 1.4) -> float:
        if self.visits == 0:
            return float('inf')
        exploitation = self.value / self.visits
        exploration = c * math.sqrt(math.log(max(self.parent.visits, 1)) / self.visits)
        return exploitation + exploration

    def best_child(self) -> 'MCTSNode':
        return max(self.children, key=lambda n: n.ucb_score()) if self.children else self

    def select_leaf(self) -> 'MCTSNode':
        node = self
        while node.children:
            node = node.best_child()
        return node

    def backpropagate(self, value: float):
        node = self
        while node:
            node.value += value
            node.visits += 1
            node = node.parent

    def is_terminal(self) -> bool:
        return "[SUCCESS]" in self.state or "[DONE]" in self.state


class LATSNodeEval(BaseModel):
    """节点评估结果"""
    score: float = Field(ge=0, le=1, description="质量评分 0-1")
    reflection: str = Field(default="", description="反思内容")
    is_terminal: bool = Field(default=False, description="是否为终止状态")


class LATSResult(BaseModel):
    """LATS 搜索结果"""
    best_state: str
    best_score: float
    total_nodes: int
    iterations: int
    reflections: list[str] = Field(default_factory=list)


async def run_lats(
    llm,
    problem: str,
    context: str = "",
    max_iterations: int = 8,
    max_children: int = 3,
    c_exploration: float = 1.4,
    temperature: float = 0.7,
) -> Optional[LATSResult]:
    """LATS 主循环"""
    root = MCTSNode(state=f"问题: {problem[:200]}")
    all_reflections = []

    for i in range(max_iterations):
        # 1. Select
        leaf = root.select_leaf()

        # 2. Expand
        children_states = await _expand(llm, problem, leaf.state, max_children, temperature, context)
        if not children_states:
            continue
        for state in children_states:
            child = MCTSNode(state=state, parent=leaf, action="expand")
            leaf.children.append(child)

        # 3. Simulate + 4. Backpropagate
        for child in leaf.children:
            if child.visits == 0:
                score, reflection, is_terminal = await _simulate(llm, problem, child.state, context)
                child.value = score
                child.visits = 1
                if reflection:
                    child.reflection = reflection
                    all_reflections.append(reflection)
                child.backpropagate(score)
                if is_terminal:
                    child.state = f"{child.state}\n[DONE]"

    # 找最优叶节点
    best = _best_leaf(root)
    if best == root:
        return None

    return LATSResult(
        best_state=best.state,
        best_score=best.value / max(best.visits, 1),
        total_nodes=_count_nodes(root),
        iterations=max_iterations,
        reflections=all_reflections[-5:],
    )


async def _expand(llm, problem: str, current: str, n: int, temp: float, ctx: str) -> list[str]:
    """生成 N 个候选下一步"""
    ctx_section = f"\n\n参考信息: {ctx[:500]}" if ctx else ""
    prompt = f"""问题: {problem[:300]}
当前推理: {current[-400:]}{ctx_section}

请生成 {n} 个不同的下一步推理方向（用 --- 分隔）。每个方向用不同的策略。"""
    try:
        response = await llm.ainvoke(prompt)
        text = response.content if isinstance(response.content, str) else str(response.content)
        steps = [s.strip() for s in text.split("---") if s.strip() and len(s.strip()) > 20]
        return steps[:n]
    except Exception:
        return []


async def _simulate(llm, problem: str, state: str, ctx: str) -> tuple[float, str, bool]:
    """LLM 评估当前状态质量"""
    try:
        structured = llm.with_structured_output(LATSNodeEval)
        result = await structured.ainvoke(
            f"问题: {problem[:200]}\n推理状态: {state[-500:]}\n\n"
            f"评估此推理的质量(0-1)，是否有反思，是否已完成。"
        )
        return result.score, result.reflection, result.is_terminal
    except Exception:
        return 0.5, "", False


def _best_leaf(root: MCTSNode) -> MCTSNode:
    leaves = _all_leaves(root)
    if not leaves:
        return root
    return max(leaves, key=lambda n: n.value / max(n.visits, 1))


def _all_leaves(node: MCTSNode) -> list:
    if not node.children:
        return [node]
    result = []
    for c in node.children:
        result.extend(_all_leaves(c))
    return result


def _count_nodes(node: MCTSNode) -> int:
    return 1 + sum(_count_nodes(c) for c in node.children)


def format_lats_for_prompt(result: Optional[LATSResult]) -> str:
    if not result:
        return ""
    reflections = "\n".join(f"  - {r}" for r in result.reflections) if result.reflections else "  无"
    return f"""
## 树搜索最优路径（LATS）
**最优评分:** {result.best_score:.2f}
**搜索节点:** {result.total_nodes} | **迭代:** {result.iterations}
**关键反思:**
{reflections}
**最优推理:**
{result.best_state[:500]}"""
