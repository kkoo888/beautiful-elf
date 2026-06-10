"""统一 LLM 对话服务 — 基于 Protocol + Selector 运行时

供 skill_executor、非流式调用等场景使用。
对话主路径走 agent_service → LangGraph，不经过本服务。
"""
import logging
from typing import List

from app.llm.runtime import llm_runtime, ChatResult
from app.repository.llm_provider_repo import LLMProviderRepository
from app.repository.llm_model_repo import LLMModelRepository

logger = logging.getLogger(__name__)


class LLMChatService:
    """统一 LLM 对话服务（非流式）"""

    async def chat(
        self,
        db,
        provider_id: int,
        model_name: str,
        messages: List[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> ChatResult:
        """非流式对话

        Args:
            db: 数据库会话
            provider_id: 供应商 ID
            model_name: 模型名称
            messages: [{"role": "user", "content": "..."}]
            temperature: 温度
            max_tokens: 最大 token

        Returns:
            ChatResult（content, model, provider_type, input_tokens, output_tokens, error）
        """
        provider_repo = LLMProviderRepository()
        model_repo = LLMModelRepository()

        provider = await provider_repo.find_by_id(db, provider_id)
        if not provider:
            return ChatResult(error=f"供应商 ID={provider_id} 不存在")

        # 确定模型名
        if not model_name:
            models = await model_repo.find_enabled_by_provider(db, provider_id)
            model_name = models[0].model_name if models else ""
        if not model_name:
            return ChatResult(error=f"供应商 '{provider.name}' 未配置模型")

        # 构建 LLMProvider 运行时
        llm_provider = llm_runtime.from_db_provider(provider, model_name)

        # 提取 system message
        system = ""
        chat_messages = []
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
            else:
                chat_messages.append(m)

        # 调用
        result = await llm_runtime.chat(
            provider=llm_provider,
            messages=chat_messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        result.provider_type = provider.provider_type
        return result


# 全局单例
llm_chat_service = LLMChatService()
