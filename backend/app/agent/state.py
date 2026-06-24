"""Agent State — TypedDict（LangGraph 官方推荐）

行业标准：TypedDict 做 State Schema，节点函数天然 dict 访问。

核心价值：
  1. 轻量级 — 无运行时校验开销，LangGraph 内部处理状态合并
  2. 天然 dict — state["key"] / state.get("key") 零适配成本
  3. Annotated reducer — operator.add 实现追加语义
  4. 类型提示 — IDE 补全和 mypy 静态检查照常工作

迁移自: Pydantic BaseModel 版 AgentState（2026-06-10）
"""
from typing import Annotated, Optional, Union
import operator
from dataclasses import dataclass

from typing_extensions import TypedDict


# ── 辅助函数（保留，供 engine 节点归一化用）──────────────────

def _content_blocks_to_str(content: Union[str, list, dict, None]) -> str:
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


def _normalize_memory_context(value: Union[dict, str, None]) -> Optional[dict]:
    """归一化 memory_context — 处理 fallback 路径返回的 str。"""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"raw": value, "count": 0, "avg_score": 0, "ids": [], "scores": []}
    return {"raw": str(value), "count": 0, "avg_score": 0, "ids": [], "scores": []}


# ── State 定义 ─────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    """LangGraph Agent 状态 — TypedDict 版。

    设计原则：
      - Annotated[list, operator.add] = LangGraph reducer（追加而非覆盖）
      - total=False：所有字段可选，节点返回 dict 只需包含要更新的字段
      - 默认值由初始状态 dict 提供，节点函数按需读取

    注意：
      - 节点函数返回 dict，LangGraph 自动合并到 state
      - state["key"] 和 state.get("key") 均可用（原生 dict 语法）
    """

    # ── 身份 ──────────────────────────────────────────
    conversation_id: int
    user_id: int
    provider_id: Optional[int]
    model_name: str
    temperature: float           # 请求级温度（0=使用 DB 值）
    max_tokens: int              # 请求级最大输出 token（0=使用 DB 值）

    # ── 消息（reducer: 追加而非覆盖）──────────────────
    messages: Annotated[list, operator.add]

    # ── LLM 交互 ─────────────────────────────────────
    system_prompt: str
    context: str
    final_answer: Optional[str]
    tool_calls: list
    tools_used: Annotated[list, operator.add]
    current_tools_used: list         # 当前迭代的工具（非 reducer，每轮覆盖）
    iterations: int
    error: Optional[str]

    # ── 工具审批 ──────────────────────────────────────
    needs_approval: bool
    pending_tool_call: Optional[dict]

    # ── 模型路由──────
    selected_model: str       # 路由选择的模型名（如 "gpt-4o" / "deepseek-chat"）
    routing_confidence: float
    routing_reason: str
    route_class: str          # R0/R1/R2/R3
    tier: str                 # S/M/L/XL（模型 tier）
    thinking_mode: str        # T0/T1/T2/T3（思维深度）
    prompt_policy: str        # P0/P1/P2（提示策略）
    prompt_hint: str          # 提示文本（压缩/标准/充分分析）
    difficulty_score: float   # 难度分数
    routing_probabilities: dict  # R0-R3 概率分布
    routing_flags: dict       # 标志位（high_risk/debug/long_context...）

    # ── 意图路由 ──────────────────────────────────────
    intent: Optional[dict]
    skill_answer: Optional[str]

    # ── 评估 ──────────────────────────────────────────
    evaluation: Optional[dict]

    # ── 记忆 ──────────────────────────────────────────
    memory_context: Optional[dict]
    conversation_importance: Optional[int]

    # ── 可观测性 ──────────────────────────────────────
    trace_metadata: dict

    # ── 动态工具选择 ──────────────────────────────────
    selected_tools: list

    # ── 推理深度（前端传入: auto/fast/deep/full）─────────
    reasoning_depth: str

    # ── Skills 按需加载 ──────────────────────────────────
    matched_skills: list  # intent_router 匹配到的 skills

    # ── Tier 配置（路由闭环使用）───────────────────────────
    tier_config: dict  # 当前 tier 的配置 {model_name, max_tokens, temperature, reasoning_enabled, ...}

    # ── Compaction 状态 ─────────────────────────────────
    is_compacted: bool  # 本轮是否已执行过 compaction（避免重复检查）

    # ── Goal 模式 ─────────────────────────────────────────
    goal_mode: bool              # 是否为 Goal 模式
    goal_definition: str         # 用户定义的目标描述
    goal_status: str             # "pending" | "in_progress" | "achieved" | "failed" | "budget_exceeded" | "blocked"
    goal_iterations: int         # 当前迭代次数
    goal_max_iterations: int     # 最大迭代次数（默认 5）
    goal_token_budget: int       # Token 预算上限（默认 50000）
    goal_tokens_used: int        # 已使用的 Token 数
    goal_history: list           # 历史迭代记录 [{iteration, action, result, evaluation}]
    goal_current_plan: str       # 当前执行计划
    goal_subtasks: list          # 目标拆分子任务 [{id, title, description, status: "pending"|"in_progress"|"done"|"failed"}]
    goal_working_memory: list    # 子任务执行结果累积 [{task_id, title, result_summary, tools_used}]
    goal_blocked_reason: str     # blocked 状态的原因（等待用户输入/暂时性错误等）
    goal_current_task_id: int    # 当前正在执行的子任务 ID（用于关联 tool 事件）


# ── Runtime Context（P1: context_schema）────────────────────

@dataclass
class Context:
    """运行时上下文 — 请求级常量，不参与图状态流转。

    通过 StateGraph(..., context_schema=Context) 注入。
    节点内通过 config["configurable"]["user_id"] 访问。

    设计意图：
      - user_id / provider_id / conversation_id 是请求级常量
      - 不应参与图状态的 reducer/merge 逻辑
      - 未来可逐步从 AgentState 中迁移至此
    """
    user_id: int = 0
    provider_id: int = 0
    conversation_id: int = 0
    model_name: str = ""


# ── Input / Output State（P1: 输入输出约束）────────────────

class InputState(TypedDict, total=False):
    """图输入 schema — 只包含外部传入的字段。"""
    conversation_id: int
    user_id: int
    provider_id: int
    model_name: str
    messages: Annotated[list, operator.add]
    reasoning_depth: str
    # ── Goal 模式 ─────────────────────────────────────
    goal_mode: bool
    goal_definition: str


class OutputState(TypedDict, total=False):
    """图输出 schema — 只包含对外暴露的字段。"""
    final_answer: Optional[str]
    messages: Annotated[list, operator.add]
    tools_used: Annotated[list, operator.add]
    intent: Optional[dict]
    evaluation: Optional[dict]
    error: Optional[str]


class _PrivateState(TypedDict, total=False):
    """内部状态通道 — 节点间私有通信，不暴露给外部。

    用途：
      - 模型路由元数据（route_class / tier / thinking_mode 等）
      - 内部追踪信息（trace_metadata）
      - 调试/评估中间数据

    注意：
      - input_schema / output_schema 只约束 invoke 的输入输出
      - stream_mode="values" 仍会暴露所有通道（含 private）
      - 真正的安全隔离需要在节点层面控制
    """
    selected_model: str
    routing_confidence: float
    routing_reason: str
    route_class: str
    tier: str
    thinking_mode: str
    prompt_policy: str
    prompt_hint: str
    difficulty_score: float
    routing_probabilities: dict
    routing_flags: dict
    trace_metadata: dict
    conversation_importance: Optional[int]
