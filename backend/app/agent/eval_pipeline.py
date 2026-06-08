"""评估流水线 — LlamaIndex Eval 框架规范化（v2.0）

v2.0 重构（Harrison Chase 视角优化）:
  - 评估框架: LlamaIndex FaithfulnessEvaluator + RelevancyEvaluator + CorrectnessEvaluator
  - 评估模式: 在线（轻量规则）+ 离线（LlamaIndex Eval 完整评估）
  - 评估指标: faithfulness / relevancy / correctness / 意图命中率
  - 代码量: ~120 行 → ~200 行（增加了评估能力）

设计原则:
  - 评估是离线任务，不影响在线服务
  - 在线评估用轻量规则（engine.py 中的 _rule_based_eval）
  - 离线评估用 LlamaIndex Eval 框架（批量跑测试集）
"""
from typing import List, Dict, Any, Optional
import asyncio
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class EvalCase(BaseModel):
    """评估用例"""
    id: int
    question: str
    expected_answer: str = ""  # v2.0: 支持标准答案对比
    expected_keywords: List[str] = []
    forbidden_patterns: List[str] = []


class EvalResult(BaseModel):
    """评估结果（v2.0: 扩展 LlamaIndex 评估指标）"""
    case_id: int
    passed: bool
    correctness: float
    faithfulness: float = 0.0   # v2.0: 幻觉检测
    relevancy: float = 0.0      # v2.0: 相关性
    has_forbidden: bool
    answer: str = ""


class EvalReport(BaseModel):
    """评估报告（v2.0: 扩展统计）"""
    total: int
    passed: int
    failed: int
    pass_rate: float
    avg_correctness: float
    avg_faithfulness: float = 0.0
    avg_relevancy: float = 0.0
    results: List[EvalResult]


class EvalPipeline:
    """评估流水线（v2.0 — LlamaIndex Eval 框架）"""

    def __init__(self, agent_graph=None, llm_client=None):
        """
        Args:
            agent_graph: Agent 图实例（用于运行测试用例）
            llm_client: LlamaIndex LLM 实例（用于评估）
        """
        self.agent = agent_graph
        self.llm = llm_client

    async def run_eval(self, cases: List[EvalCase]) -> EvalReport:
        """
        运行离线评估（LlamaIndex Eval 框架）。

        评估流程:
          1. Agent 生成回答
          2. FaithfulnessEvaluator 检测幻觉
          3. RelevancyEvaluator 检测相关性
          4. CorrectnessEvaluator 对比标准答案
          5. 规则初筛（关键词 + 禁止模式）
        """
        results = []
        for case in cases:
            result = await self._eval_single(case)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        return EvalReport(
            total=len(results),
            passed=passed,
            failed=failed,
            pass_rate=round(passed / max(len(results), 1), 4),
            avg_correctness=round(sum(r.correctness for r in results) / max(len(results), 1), 4),
            avg_faithfulness=round(sum(r.faithfulness for r in results) / max(len(results), 1), 4),
            avg_relevancy=round(sum(r.relevancy for r in results) / max(len(results), 1), 4),
            results=results,
        )

    async def _eval_single(self, case: EvalCase) -> EvalResult:
        """评估单个用例（v2.0: LlamaIndex Eval 三维度）"""
        answer = await self._get_answer(case.question)

        # ── 规则初筛 ──────────────────────────────
        has_forbidden = any(p in answer for p in case.forbidden_patterns)
        keyword_hits = sum(1 for kw in case.expected_keywords if kw in answer)
        keyword_ratio = keyword_hits / max(len(case.expected_keywords), 1)

        # ── LlamaIndex Eval（三维度）────────────────
        faithfulness = 0.0
        relevancy = 0.0
        correctness = keyword_ratio  # 默认用关键词匹配

        if self.llm and answer:
            try:
                faithfulness = await self._eval_faithfulness(case.question, answer)
                relevancy = await self._eval_relevancy(case.question, answer)

                if case.expected_answer:
                    correctness = await self._eval_correctness(
                        case.question, answer, case.expected_answer
                    )
                elif 0.3 < keyword_ratio < 0.7:
                    # 边界 case 用 LLM 复核
                    correctness = await self._llm_judge(case, answer)

            except Exception as e:
                logger.warning(f"LlamaIndex Eval 失败，降级为规则评估: {e}")

        # ── 综合评分 ──────────────────────────────
        # 权重: correctness 0.4 + faithfulness 0.3 + relevancy 0.3
        if faithfulness > 0 or relevancy > 0:
            final_score = (
                correctness * 0.4
                + faithfulness * 0.3
                + relevancy * 0.3
            )
        else:
            final_score = correctness

        return EvalResult(
            case_id=case.id,
            passed=final_score >= 0.7 and not has_forbidden,
            correctness=round(correctness, 4),
            faithfulness=round(faithfulness, 4),
            relevancy=round(relevancy, 4),
            has_forbidden=has_forbidden,
            answer=answer[:500],
        )

    async def _eval_faithfulness(self, query: str, answer: str, contexts: List[str] = None) -> float:
        """幻觉检测（LlamaIndex FaithfulnessEvaluator）

        检查回答是否基于检索到的上下文，而非捏造信息。
        contexts: 检索到的上下文列表（可选，无上下文时降级为规则检测）
        """
        try:
            from llama_index.core.evaluation import FaithfulnessEvaluator

            evaluator = FaithfulnessEvaluator(llm=self.llm)
            result = await asyncio.to_thread(
                evaluator.evaluate,
                query=query,
                response=answer,
                contexts=contexts or [],
            )
            return result.score
        except Exception as e:
            logger.debug(f"FaithfulnessEvaluator 失败: {e}")
            return 0.0

    async def _eval_relevancy(self, query: str, answer: str, contexts: List[str] = None) -> float:
        """相关性检测（LlamaIndex RelevancyEvaluator）

        检查回答是否与用户问题相关。
        """
        try:
            from llama_index.core.evaluation import RelevancyEvaluator

            evaluator = RelevancyEvaluator(llm=self.llm)
            result = await asyncio.to_thread(
                evaluator.evaluate,
                query=query,
                response=answer,
                contexts=contexts or [],
            )
            return result.score
        except Exception as e:
            logger.debug(f"RelevancyEvaluator 失败: {e}")
            return 0.0

    async def _eval_correctness(self, query: str, answer: str, expected: str) -> float:
        """正确性检测（LlamaIndex CorrectnessEvaluator）

        对比回答与标准答案的正确性。
        """
        try:
            from llama_index.core.evaluation import CorrectnessEvaluator

            evaluator = CorrectnessEvaluator(llm=self.llm)
            result = await asyncio.to_thread(
                evaluator.evaluate,
                query=query,
                response=answer,
                reference=expected,
            )
            return result.score
        except Exception as e:
            logger.debug(f"CorrectnessEvaluator 失败: {e}")
            return 0.0

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

        prompt = (
            f"评估回答质量（0-1 的浮点数，只输出数字）：\n"
            f"问题: {case.question}\n"
            f"回答: {answer[:1000]}\n"
            f"期望关键词: {case.expected_keywords}"
        )

        try:
            from llama_index.core.llms import ChatMessage, MessageRole

            response = await self.llm.achat([
                ChatMessage(role=MessageRole.USER, content=prompt),
            ])
            score = float(str(response).strip())
            return max(0.0, min(1.0, score))
        except Exception:
            return 0.5
