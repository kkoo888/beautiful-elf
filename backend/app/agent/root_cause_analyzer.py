"""根因分析引擎 — 5-Why 分析 + Ishikawa 因果图

核心思想:
  失败发生时，不停留在表面症状，用 5-Why 方法逐层追问，
  找到根本原因后制定修复策略和预防措施。

前沿依据:
  - Toyota 5-Why: 追问 5 层找到根本原因
  - Ishikawa Diagram: 人/机/料/法/环 五因素分析
  - Reflexion (Shinn 2023): 语言反馈强化 Agent 决策

与 Self-Healing 的区别:
  - Self-Healing: 记录失败 + 标记成功/失败
  - RootCauseAnalyzer: 深度分析 WHY，找到根因 + 制定预防策略
  两者互补: RootCauseAnalyzer 产出 → 存入 Self-Healing Memory
"""
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


class CauseCategory(str, Enum):
    """根因类别（Ishikawa 五因素）"""
    TOOL = "tool"          # 工具问题: 工具调用失败、返回错误、参数错误
    KNOWLEDGE = "knowledge"  # 知识问题: 缺少领域知识、信息不足
    REASONING = "reasoning"  # 推理问题: 逻辑错误、幻觉、偏见
    CONTEXT = "context"      # 上下文问题: 信息丢失、上下文不足、干扰信息
    TASK = "task"            # 任务问题: 任务定义不清、粒度不当、依赖错误
    EXTERNAL = "external"    # 外部问题: 系统故障、网络问题、权限不足


class RootCauseAnalysis(BaseModel):
    """根因分析结果"""
    symptom: str = Field(description="症状描述")
    why_chain: list[str] = Field(default_factory=list, description="5-Why 链")
    root_cause: str = Field(description="根本原因（一句话）")
    cause_category: CauseCategory = Field(description="原因类别")
    fix_strategy: str = Field(description="修复策略")
    prevention: str = Field(description="预防措施")
    confidence: float = Field(default=0.5, ge=0, le=1, description="置信度 0-1")
    related_facts: list[str] = Field(default_factory=list, description="相关事实/证据")


async def analyze_root_cause(
    llm,
    symptom: str,
    failure_context: dict = None,
    max_whys: int = 5,
    temperature: float = 0.3,
) -> Optional[RootCauseAnalysis]:
    """5-Why 根因分析

    Args:
        llm: LLM 实例
        symptom: 症状描述（如 "子任务输出过短"、"工具调用返回空"）
        failure_context: 失败上下文（包含 subtask、output、error、guardrail_reason 等）
        max_whys: 最大追问层数（默认 5）
        temperature: LLM 温度
    """
    try:
        ctx = failure_context or {}
        context_parts = []
        if ctx.get("subtask"):
            context_parts.append(f"子任务: {ctx['subtask']}")
        if ctx.get("output"):
            context_parts.append(f"输出: {ctx['output'][:500]}")
        if ctx.get("error"):
            context_parts.append(f"错误: {ctx['error']}")
        if ctx.get("guardrail_reason"):
            context_parts.append(f"校验失败原因: {ctx['guardrail_reason']}")
        if ctx.get("expert_name"):
            context_parts.append(f"执行专家: {ctx['expert_name']}({ctx.get('expert_role', '')})")
        context_text = "\\n".join(context_parts) if context_parts else "无额外上下文"

        prompt = f"""你是一个根因分析专家。使用 5-Why 方法分析以下失败案例。

## 症状
{symptom}

## 上下文
{context_text}

## 分析要求
1. 从症状开始，逐层追问「为什么」（最多 {max_whys} 层）
2. 每层的回答必须是上一层原因的原因（因果链）
3. 追问到可操作的根本原因时停止
4. 将根本原因归类到以下类别之一:
   - tool: 工具问题（调用失败、参数错误、返回异常）
   - knowledge: 知识问题（缺少领域知识、信息不足）
   - reasoning: 推理问题（逻辑错误、幻觉、偏见）
   - context: 上下文问题（信息丢失、上下文不足、干扰信息）
   - task: 任务问题（定义不清、粒度不当、依赖错误）
   - external: 外部问题（系统故障、网络问题）
5. 给出修复策略和预防措施

请严格按 JSON 格式输出。"""

        from langchain_core.messages import HumanMessage

        # 使用 structured output 保证格式
        structured_llm = llm.with_structured_output(RootCauseAnalysis)
        result = await structured_llm.ainvoke([HumanMessage(content=prompt)])

        # 确保 why_chain 不为空
        if not result.why_chain:
            result.why_chain = [symptom, result.root_cause]

        logger.info(f"[root_cause] 根因分析完成: {result.cause_category.value} — {result.root_cause[:80]}")
        return result

    except Exception as e:
        logger.warning(f"[root_cause] 根因分析失败（降级为简单记录）: {e}")
        return None


def format_root_cause_for_prompt(rca: Optional[RootCauseAnalysis]) -> str:
    """将根因分析结果格式化为 prompt 注入文本"""
    if not rca:
        return ""

    why_text = " → ".join(rca.why_chain) if rca.why_chain else "未分析"
    return f"""
## 根因分析（5-Why）
**症状:** {rca.symptom}
**因果链:** {why_text}
**根本原因:** {rca.root_cause}
**原因类别:** {rca.cause_category.value}
**修复策略:** {rca.fix_strategy}
**预防措施:** {rca.prevention}
**置信度:** {rca.confidence:.0%}"""


async def store_root_cause(
    rca: RootCauseAnalysis,
    user_id: int = 0,
    conversation_id: int = 0,
    db=None,
) -> bool:
    """将根因分析结果存入记忆系统

    存储为原子事实，分类为 root_cause，供跨任务召回。
    """
    try:
        from app.agent.expert_team.memory import AtomicFact, store_experience

        # 根因 → 高重要性 insight
        fact = AtomicFact(
            content=f"[根因:{rca.cause_category.value}] {rca.root_cause} | 修复: {rca.fix_strategy} | 预防: {rca.prevention}",
            category="root_cause",
            importance=min(rca.confidence + 0.2, 1.0),
        )

        # 用 team_id=0 表示全局经验（跨 team 可召回）
        stored = await store_experience(
            expert_id=user_id, team_id=0, facts=[fact], db=db,
        )
        return stored > 0

    except Exception as e:
        logger.warning(f"[root_cause] 根因存储失败: {e}")
        return False
