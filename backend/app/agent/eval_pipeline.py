"""评估流水线 — 规则初筛 + LLM 复核

职责:
  - 加载测试用例集
  - 规则初筛（关键词命中 + 禁止模式检测）
  - 边界 case 用 LLM 复核
  - 输出评估报告

设计原则:
  - 评估是离线任务，不影响在线服务
  - 规则初筛快速过滤，LLM 只处理边界 case
"""
from typing import List, Dict, Any
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class EvalCase(BaseModel):
    """评估用例"""
    id: int
    question: str
    expected_keywords: List[str] = []
    forbidden_patterns: List[str] = []


class EvalResult(BaseModel):
    """评估结果"""
    case_id: int
    passed: bool
    correctness: float
    has_forbidden: bool
    answer: str = ""


class EvalReport(BaseModel):
    """评估报告"""
    total: int
    passed: int
    failed: int
    pass_rate: float
    avg_correctness: float
    results: List[EvalResult]


class EvalPipeline:
    """评估流水线"""

    def __init__(self, agent_graph=None, llm_client=None):
        """
        Args:
            agent_graph: Agent 图实例（用于运行测试用例）
            llm_client: LLM 实例（用于边界 case 复核）
        """
        self.agent = agent_graph
        self.llm = llm_client

    async def run_eval(self, cases: List[EvalCase]) -> EvalReport:
        """
        运行评估。

        Args:
            cases: 测试用例列表

        Returns:
            评估报告
        """
        results = []
        for case in cases:
            result = await self._eval_single(case)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        avg_corr = sum(r.correctness for r in results) / max(len(results), 1)

        return EvalReport(
            total=len(results),
            passed=passed,
            failed=failed,
            pass_rate=round(passed / max(len(results), 1), 4),
            avg_correctness=round(avg_corr, 4),
            results=results,
        )

    async def _eval_single(self, case: EvalCase) -> EvalResult:
        """评估单个用例"""
        # 获取 Agent 回答
        answer = await self._get_answer(case.question)

        # 规则初筛
        has_forbidden = any(p in answer for p in case.forbidden_patterns)
        keyword_hits = sum(1 for kw in case.expected_keywords if kw in answer)
        keyword_ratio = keyword_hits / max(len(case.expected_keywords), 1)

        # 边界 case 用 LLM 复核
        if 0.3 < keyword_ratio < 0.7 and not has_forbidden:
            score = await self._llm_judge(case, answer)
        else:
            score = keyword_ratio

        return EvalResult(
            case_id=case.id,
            passed=score >= 0.7 and not has_forbidden,
            correctness=round(score, 4),
            has_forbidden=has_forbidden,
            answer=answer[:500],
        )

    async def _get_answer(self, question: str) -> str:
        """获取 Agent 回答"""
        if not self.agent:
            return ""

        try:
            result = await self.agent.ainvoke({
                "conversation_id": 0,
                "user_id": 0,
                "messages": [{"role": "user", "content": question}],
                "context": "",
                "tool_calls": [],
                "tools_used": [],
                "final_answer": None,
                "iterations": 0,
                "needs_approval": False,
                "pending_tool_call": None,
            })
            return result.get("final_answer", "") or ""
        except Exception as e:
            logger.error(f"评估 Agent 调用失败: {e}")
            return ""

    async def _llm_judge(self, case: EvalCase, answer: str) -> float:
        """LLM 复核边界 case"""
        if not self.llm:
            return 0.5

        import asyncio
        prompt = (
            f"评估回答质量（0-1 的浮点数，只输出数字）：\n"
            f"问题: {case.question}\n"
            f"回答: {answer[:1000]}\n"
            f"期望关键词: {case.expected_keywords}"
        )

        try:
            result = await asyncio.to_thread(self.llm.complete, prompt)
            score = float(str(result).strip())
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.5
