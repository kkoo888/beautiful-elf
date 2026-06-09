"""Agent State — Pydantic BaseModel（生产级类型安全）

2026 行业标准：用 Pydantic 替代 TypedDict 做 State Schema。

核心价值：
  1. 运行时类型校验 — 写入时自动归一化，不等到消费端才炸
  2. field_validator — 在数据进入 State 前统一转换格式
  3. Field description — 自动出现在 LangSmith 追踪面板
  4. 默认值管理 — 不再需要 state.get("field", default)

迁移自: engine.py 中的 TypedDict AgentState
"""
from typing import Annotated, Optional, Any
import operator

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _content_blocks_to_str(content: Any) -> str:
    """将 LLM content 统一转为字符串。

    处理所有模型返回格式：
      - str → 直接返回
      - None → ""
      - list[dict] → 提取 text 字段拼接（OpenAI / Claude / agnes 格式）
      - 其他 → str() 强转
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def _normalize_memory_context(value: Any) -> Optional[dict]:
    """归一化 memory_context — 处理 fallback 路径返回的 str。"""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        # fallback 路径：memory_manager.search() 返回字符串
        return {"raw": value, "count": 0, "avg_score": 0, "ids": [], "scores": []}
    return {"raw": str(value), "count": 0, "avg_score": 0, "ids": [], "scores": []}


class AgentState(BaseModel):
    """LangGraph Agent 状态 — Pydantic 类型安全版。

    设计原则：
      - 生产者归一化：field_validator 在写入时转换格式，消费端无需防御
      - 不可变字段用 Field，可变字段用 default_factory
      - Annotated[list, operator.add] = LangGraph reducer（追加而非覆盖）

    注意：
      - 节点函数仍返回 dict，LangGraph + Pydantic 自动处理校验
      - state["key"] 和 state.get("key") 均可用（Pydantic BaseModel 兼容）
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # 允许 AIMessage 等非标准类型
        extra="allow",                 # 允许临时字段（调试、扩展用）
    )

    # ── 身份 ──────────────────────────────────────────
    conversation_id: int = Field(default=0, description="会话 ID")
    user_id: int = Field(default=0, description="用户 ID")
    provider_id: Optional[int] = Field(default=None, description="模型供应商 ID")
    model_name: str = Field(default="", description="当前使用的模型名称")

    # ── 消息（reducer: 追加而非覆盖）──────────────────
    messages: Annotated[list, operator.add] = Field(
        default_factory=list,
        description="对话消息历史（自动追加）",
    )

    # ── LLM 交互 ─────────────────────────────────────
    system_prompt: str = Field(default="", description="系统提示词")
    context: str = Field(default="", description="上下文（与 system_prompt 同步）")
    final_answer: Optional[str] = Field(
        default=None,
        description="最终回答文本（归一化为 str）",
    )
    tool_calls: list = Field(
        default_factory=list,
        description="LLM 返回的工具调用请求",
    )
    tools_used: Annotated[list, operator.add] = Field(
        default_factory=list,
        description="已执行的工具名列表（自动追加）",
    )
    iterations: int = Field(default=0, ge=0, description="当前迭代次数")
    error: Optional[str] = Field(default=None, description="错误信息")

    # ── 工具审批 ──────────────────────────────────────
    needs_approval: bool = Field(default=False, description="是否需要用户审批")
    pending_tool_call: Optional[dict] = Field(
        default=None,
        description="等待审批的工具调用",
    )

    # ── 意图路由 ──────────────────────────────────────
    intent: Optional[dict] = Field(default=None, description="意图识别结果")
    skill_answer: Optional[str] = Field(
        default=None,
        description="技能模块返回的答案",
    )

    # ── 评估 ──────────────────────────────────────────
    evaluation: Optional[dict] = Field(
        default=None,
        description="评估结果 {score, passed, reason, dimensions}",
    )

    # ── 记忆 ──────────────────────────────────────────
    memory_context: Optional[dict] = Field(
        default=None,
        description="记忆元数据 {ids, scores, count, avg_score}",
    )
    conversation_importance: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="对话重要性评分 1-10",
    )

    # ── 可观测性 ──────────────────────────────────────
    trace_metadata: dict = Field(
        default_factory=dict,
        description="链路追踪元数据",
    )

    # ── 动态工具选择 ──────────────────────────────────
    selected_tools: list = Field(
        default_factory=list,
        description="当前请求选中的工具名列表",
    )

    # ═══════════════════════════════════════════════════
    # field_validator — 写入时自动归一化
    # mode='before'：在 Pydantic 类型检查之前执行
    # 这是生产者归一化的核心——消费端永远拿到正确类型
    # ═══════════════════════════════════════════════════

    @field_validator("final_answer", mode="before")
    @classmethod
    def _normalize_final_answer(cls, v: Any) -> Optional[str]:
        """归一化 final_answer — 处理模型返回 content blocks 格式。"""
        if v is None:
            return None
        return _content_blocks_to_str(v)

    @field_validator("memory_context", mode="before")
    @classmethod
    def _normalize_memory(cls, v: Any) -> Optional[dict]:
        """归一化 memory_context — 处理 fallback 路径返回的 str。"""
        return _normalize_memory_context(v)

    @field_validator("evaluation", mode="before")
    @classmethod
    def _normalize_evaluation(cls, v: Any) -> Optional[dict]:
        """归一化 evaluation — 确保始终是 dict 或 None。"""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        # 如果是 Pydantic 模型实例，转为 dict
        if hasattr(v, "model_dump"):
            return v.model_dump()
        return None

    @field_validator("skill_answer", mode="before")
    @classmethod
    def _normalize_skill_answer(cls, v: Any) -> Optional[str]:
        """归一化 skill_answer — skill_executor 返回 result.content 可能是 list。"""
        if v is None:
            return None
        return _content_blocks_to_str(v)
