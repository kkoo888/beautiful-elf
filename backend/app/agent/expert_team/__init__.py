"""专家团进化模块 — Planning + Reasoning + Guardrail + 知识源 + 记忆 + 辩论 + 检查点"""
from .planner import generate_expert_plan, format_plan_for_prompt, ExpertPlan
from .reasoning import generate_reasoning, format_reasoning_for_prompt, ExpertReasoning
from .guardrail import validate_output, retry_with_feedback, GuardrailResult
from .knowledge import inject_expert_knowledge
from .memory import extract_facts, store_experience, recall_experience, AtomicFact
from .query_rewriter import rewrite_query, rerank_results
from .debate import run_debate_round, revise_opinion, format_debate_for_prompt
from .checkpoint import save_checkpoint, load_latest_checkpoint, request_human_review, resume_from_review
from .reflexion import generate_reflexion, format_reflexion_for_prompt, store_reflexion_as_memory
from .consistency import execute_with_self_consistency
from .tot import explore_thoughts, format_tot_for_prompt

__all__ = [
    "generate_expert_plan", "format_plan_for_prompt", "ExpertPlan",
    "generate_reasoning", "format_reasoning_for_prompt", "ExpertReasoning",
    "validate_output", "retry_with_feedback", "GuardrailResult",
    "inject_expert_knowledge",
    "extract_facts", "store_experience", "recall_experience", "AtomicFact",
    "rewrite_query", "rerank_results",
    "run_debate_round", "revise_opinion", "format_debate_for_prompt",
    "save_checkpoint", "load_latest_checkpoint", "request_human_review", "resume_from_review",
    "generate_reflexion", "format_reflexion_for_prompt", "store_reflexion_as_memory",
    "execute_with_self_consistency",
    "explore_thoughts", "format_tot_for_prompt",
]
