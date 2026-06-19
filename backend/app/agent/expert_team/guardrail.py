"""专家团质量门禁 — 输出校验 + 自动重试

核心思想：
  专家输出后，Guardrail 做两层校验：
  1. 格式校验：长度、结构、必填字段
  2. 语义校验：LLM 判断是否完成子任务、是否有幻觉
  校验失败 → 将错误反馈注入 prompt，自动重试（最多 N 次）
"""
from typing import Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class GuardrailResult:
    """校验结果"""
    passed: bool
    errors: list[str]
    suggestions: list[str]


class SemanticValidation(BaseModel):
    """语义校验结果"""
    completed: bool = Field(..., description="是否完成子任务")
    has_hallucination: bool = Field(default=False, description="是否有幻觉/捏造")
    quality_score: int = Field(default=5, ge=1, le=10, description="质量评分 1-10")
    issues: list[str] = Field(default_factory=list, description="发现的问题")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


async def validate_output(
    db,
    provider_id: int,
    model_name: str,
    expert_name: str,
    subtask: str,
    output: str,
    min_length: int = 50,
    temperature: float = 0.2,
) -> GuardrailResult:
    """校验专家输出

    两层校验：
    1. 格式校验（本地，零成本）
    2. 语义校验（LLM，仅在格式通过后执行）
    """
    errors = []
    suggestions = []

    # ── 第一层：格式校验 ──
    if not output or not output.strip():
        errors.append("输出为空")
        return GuardrailResult(passed=False, errors=errors, suggestions=["请重新执行任务并输出内容"])

    if len(output.strip()) < min_length:
        errors.append(f"输出过短（{len(output.strip())} 字符，要求至少 {min_length} 字符）")
        return GuardrailResult(passed=False, errors=errors, suggestions=["请详细展开分析，至少 50 字符"])

    # ── 第二层：语义校验 ──
    try:
        from app.agent.llm_service import llm_service

        llm = await llm_service.get_chat_llm(
            db, provider_id=provider_id, model_name=model_name, temperature=temperature,
        )

        validation_prompt = f"""请评估以下专家输出的质量。

## 子任务
{subtask}

## 专家输出
{output[:2000]}

请评估：
1. 是否完成了子任务？
2. 是否有幻觉/捏造的内容？
3. 质量评分（1-10）
4. 有什么问题？
5. 如何改进？"""

        structured_llm = llm.with_structured_output(SemanticValidation)
        validation = await structured_llm.ainvoke(validation_prompt)

        if not validation.completed:
            errors.append("未完成子任务")
        if validation.has_hallucination:
            errors.append("包含幻觉/捏造内容")
        if validation.quality_score < 5:
            errors.append(f"质量评分过低: {validation.quality_score}/10")

        suggestions.extend(validation.suggestions)
        issues = validation.issues

    except Exception as e:
        logger.warning(f"语义校验失败（降级为仅格式校验）: {e}")
        issues = []

    passed = len(errors) == 0
    return GuardrailResult(passed=passed, errors=errors, suggestions=suggestions)


async def retry_with_feedback(
    db,
    provider_id: int,
    model_name: str,
    expert_name: str,
    expert_role: str,
    subtask: str,
    original_prompt: str,
    previous_output: str,
    errors: list[str],
    suggestions: list[str],
    temperature: float = 0.7,
    max_retries: int = 2,
) -> tuple[str, int]:
    """带反馈重试

    将校验失败的错误和建议注入 prompt，重新执行。

    Returns:
        (最终输出, 重试次数)
    """
    from app.agent.llm_service import llm_service
    from langchain_core.messages import HumanMessage

    current_output = previous_output
    retries = 0

    for attempt in range(max_retries):
        errors_text = "\n".join(f"  - {e}" for e in errors)
        suggestions_text = "\n".join(f"  - {s}" for s in suggestions)

        retry_prompt = f"""{original_prompt}

## 上一次输出（有问题）
{current_output[:1500]}

## 发现的问题
{errors_text}

## 改进建议
{suggestions_text}

请根据以上反馈，重新执行任务，修正问题并输出改进后的内容。"""

        try:
            llm = await llm_service.get_chat_llm(
                db, provider_id=provider_id, model_name=model_name, temperature=temperature,
            )
            response = await llm.ainvoke([HumanMessage(content=retry_prompt)])
            from app.agent.state import _content_to_str
            current_output = _content_to_str(response.content)
            retries = attempt + 1

            # 快速校验（仅格式）
            if current_output and len(current_output.strip()) >= 50:
                break

        except Exception as e:
            logger.warning(f"重试 {attempt + 1} 失败: {e}")
            break

    return current_output, retries
