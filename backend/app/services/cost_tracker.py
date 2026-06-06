"""成本追踪服务 — 记录每次 LLM 调用的 token 用量和费用

定价参考（2026年主流模型，人民币）:
  - GPT-4o:       input ¥0.038/1K, output ¥0.114/1K
  - GPT-4o-mini:  input ¥0.001/1K, output ¥0.003/1K
  - DeepSeek-V3:  input ¥0.001/1K, output ¥0.002/1K
  - Qwen3-72B:    input ¥0.004/1K, output ¥0.012/1K
  - Qwen3-7B:     input ¥0.0006/1K, output ¥0.0012/1K
  - Claude-3.5:   input ¥0.025/1K, output ¥0.075/1K
  - Ollama 本地:   ¥0（忽略电费）
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository.cost_repo import CostRepository
from app.core.logging import get_logger

logger = get_logger(__name__)

# 模型定价表（人民币/千 token）
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 0.038, "output": 0.114},
    "gpt-4o-mini": {"input": 0.001, "output": 0.003},
    "gpt-4-turbo": {"input": 0.076, "output": 0.228},
    "gpt-3.5-turbo": {"input": 0.004, "output": 0.008},
    # DeepSeek
    "deepseek-v3": {"input": 0.001, "output": 0.002},
    "deepseek-r1": {"input": 0.004, "output": 0.016},
    "deepseek-chat": {"input": 0.001, "output": 0.002},
    # Qwen
    "qwen3-72b": {"input": 0.004, "output": 0.012},
    "qwen3-32b": {"input": 0.002, "output": 0.006},
    "qwen3-7b": {"input": 0.0006, "output": 0.0012},
    "qwen-plus": {"input": 0.004, "output": 0.012},
    "qwen-turbo": {"input": 0.001, "output": 0.002},
    # Claude
    "claude-3-5-sonnet": {"input": 0.025, "output": 0.075},
    "claude-3-opus": {"input": 0.113, "output": 0.563},
    "claude-3-haiku": {"input": 0.002, "output": 0.008},
    # 默认（未知模型）
    "_default": {"input": 0.005, "output": 0.015},
}

# 美元兑人民币汇率
USD_TO_CNY = 7.25


class CostTracker:
    """成本追踪器"""

    def __init__(self):
        self.repo = CostRepository()

    async def record(
        self,
        db: AsyncSession,
        user_id: int,
        conversation_id: int,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: int = 0,
        call_type: str = "chat",
        provider_id: int = 0,
        is_stream: bool = False,
    ) -> None:
        """记录一次 LLM 调用的成本"""
        total_tokens = prompt_tokens + completion_tokens
        cost_cny, cost_usd = self._calculate_cost(model_name, prompt_tokens, completion_tokens)

        try:
            await self.repo.create(db, {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "provider_id": provider_id,
                "model_name": model_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "cost_cny": cost_cny,
                "call_type": call_type,
                "duration_ms": duration_ms,
                "is_stream": 1 if is_stream else 0,
            })
            logger.debug(f"[cost] {model_name} tokens={total_tokens} cost=¥{cost_cny:.4f}")
        except Exception as e:
            logger.warning(f"[cost] 记录失败: {e}")

    def _calculate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> tuple:
        """计算费用（返回 cny, usd）"""
        model_lower = model_name.lower().strip()

        # 精确匹配
        pricing = MODEL_PRICING.get(model_lower)
        if not pricing:
            # 模糊匹配（如 "ollama/qwen3:7b" → 匹配 "qwen3-7b"）
            for key in MODEL_PRICING:
                if key != "_default" and key in model_lower:
                    pricing = MODEL_PRICING[key]
                    break
        if not pricing:
            pricing = MODEL_PRICING["_default"]

        # Ollama 本地模型免费
        if "ollama" in model_lower or ":latest" in model_lower:
            return 0.0, 0.0

        cost_cny = (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1000
        cost_usd = cost_cny / USD_TO_CNY

        return round(cost_cny, 6), round(cost_usd, 6)

    async def get_summary(self, db: AsyncSession, user_id: int, days: int = 30) -> dict:
        """获取成本汇总"""
        total = await self.repo.summary_by_user(db, user_id)
        by_model = await self.repo.summary_by_model(db, user_id, days)
        by_type = await self.repo.summary_by_type(db, user_id, days)
        return {
            "total_cost_cny": total["total_cny"],
            "total_cost_usd": total["total_usd"],
            "total_tokens": total["total_tokens"],
            "call_count": total["call_count"],
            "by_model": by_model,
            "by_type": by_type,
        }


# 全局单例
cost_tracker = CostTracker()
