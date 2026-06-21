"""原子声明验证 — 事实性幻觉检测与修正

核心思想:
  将 LLM 输出拆解为原子声明（每个声明一个独立事实），
  逐条验证每个声明是否被上下文/知识支持，修正幻觉。

前沿依据:
  - FActScore (Min et al. 2023): 原子声明级事实性评估
  - FinGround (ACL 2026): 通过原子声明验证检测金融幻觉
  - GSAR (2025): 多智能体幻觉检测与恢复

幻觉三类:
  1. 事实性幻觉 (45%): 错误的事实 → 原子声明验证
  2. 忠实性幻觉 (35%): 忽略上下文 → Grounding 验证
  3. 推理性幻觉 (20%): 逻辑链断裂 → Self-Consistency
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class AtomicClaim(BaseModel):
    """原子声明 — 一个独立的事实性陈述"""
    claim: str = Field(description="声明内容")
    claim_type: str = Field(default="fact", description="声明类型: fact/opinion/prediction")
    needs_verification: bool = Field(default=True, description="是否需要验证")


class ClaimExtraction(BaseModel):
    """声明提取结果"""
    claims: list[AtomicClaim] = Field(default_factory=list)


class ClaimVerification(BaseModel):
    """单条声明验证结果"""
    claim: str = Field(description="原始声明")
    verdict: str = Field(description="supported/refuted/uncertain")
    evidence: str = Field(default="", description="支持或反驳的证据")
    confidence: float = Field(default=0.5, ge=0, le=1, description="置信度")
    corrected_claim: str = Field(default="", description="修正后的声明（仅 refuted 时）")


class FactVerificationResult(BaseModel):
    """事实验证总结果"""
    original_text: str
    total_claims: int = 0
    supported: int = 0
    refuted: int = 0
    uncertain: int = 0
    hallucination_rate: float = 0.0
    corrected_text: str = ""
    verifications: list[ClaimVerification] = Field(default_factory=list)


async def verify_facts(
    llm,
    text: str,
    context: str = "",
    temperature: float = 0.2,
) -> Optional[FactVerificationResult]:
    """原子声明验证主流程

    1. 拆解文本为原子声明
    2. 逐条验证每个声明
    3. 修正幻觉内容

    Args:
        llm: LLM 实例
        text: 待验证的文本
        context: 上下文（RAG 检索结果、工具输出等）
        temperature: LLM 温度
    """
    if not text or len(text.strip()) < 20:
        return None

    try:
        # Step 1: 拆解为原子声明
        claims = await _extract_claims(llm, text, temperature)
        if not claims:
            return None

        # Step 2: 逐条验证
        verifications = []
        context_section = f"\n\n## 参考上下文\n{context[:2000]}" if context else ""

        for claim in claims:
            if not claim.needs_verification:
                verifications.append(ClaimVerification(
                    claim=claim.claim, verdict="supported", confidence=0.9,
                ))
                continue

            v = await _verify_single_claim(llm, claim.claim, context_section, temperature)
            verifications.append(v)

        # Step 3: 统计
        supported = sum(1 for v in verifications if v.verdict == "supported")
        refuted = sum(1 for v in verifications if v.verdict == "refuted")
        uncertain = sum(1 for v in verifications if v.verdict == "uncertain")
        total = len(verifications)

        # Step 4: 修正幻觉
        corrected = text
        refuted_claims = [v for v in verifications if v.verdict == "refuted"]
        if refuted_claims:
            corrected = await _correct_hallucinations(llm, text, refuted_claims, temperature)

        result = FactVerificationResult(
            original_text=text,
            total_claims=total,
            supported=supported,
            refuted=refuted,
            uncertain=uncertain,
            hallucination_rate=refuted / max(total, 1),
            corrected_text=corrected,
            verifications=verifications,
        )

        if refuted > 0:
            logger.info(f"[fact_verify] 发现 {refuted}/{total} 条幻觉，已修正")
        return result

    except Exception as e:
        logger.warning(f"[fact_verify] 事实验证失败（降级跳过）: {e}")
        return None


async def _extract_claims(llm, text: str, temperature: float) -> list[AtomicClaim]:
    """将文本拆解为原子声明"""
    try:
        prompt = f"""请将以下文本拆解为原子声明（每个声明只包含一个独立事实）。

## 文本
{text[:2000]}

## 规则
1. 每个声明是一个独立的、可验证的事实陈述
2. 跳过过渡句、修辞性表达、主观判断
3. 涉及数字/日期/人名/地名的声明必须提取
4. 最多提取 15 个声明"""

        structured_llm = llm.with_structured_output(ClaimExtraction)
        result = await structured_llm.ainvoke(prompt)
        return result.claims[:15]
    except Exception as e:
        logger.debug(f"[fact_verify] 声明提取失败: {e}")
        return []


async def _verify_single_claim(
    llm, claim: str, context_section: str, temperature: float,
) -> ClaimVerification:
    """验证单条声明"""
    try:
        prompt = f"""验证以下声明是否正确。

## 声明
{claim}
{context_section}

请判断:
1. 声明是否被上下文/已知事实支持？
2. 如果被反驳，正确的说法是什么？

verdict 选项:
- supported: 声明正确
- refuted: 声明错误
- uncertain: 无法确定"""

        structured_llm = llm.with_structured_output(ClaimVerification)
        result = await structured_llm.ainvoke(prompt)
        result.claim = claim
        return result
    except Exception:
        return ClaimVerification(claim=claim, verdict="uncertain", confidence=0.3)


async def _correct_hallucinations(
    llm, text: str, refuted: list[ClaimVerification], temperature: float,
) -> str:
    """修正幻觉内容"""
    try:
        corrections = "\n".join(
            f"- 错误: {v.claim}\n  正确: {v.corrected_claim or v.evidence}"
            for v in refuted
        )
        prompt = f"""以下文本包含一些错误信息，请修正。

## 原始文本
{text[:2000]}

## 需要修正的内容
{corrections}

## 要求
1. 修正所有指出的错误
2. 保持文本结构和风格不变
3. 无法确定正确信息时，删除该部分内容
4. 输出修正后的完整文本"""

        response = await llm.ainvoke(prompt)
        corrected = response.content if isinstance(response.content, str) else str(response.content)
        return corrected.strip() if corrected.strip() else text
    except Exception:
        return text
