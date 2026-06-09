"""Agent 模块 — LLM Agent 引擎核心组件（v1.2 重构）

核心模块:
  - llm_service: LLM 服务工厂（多供应商 + LangChain 兼容）
  - engine: Agent 引擎（LangGraph StateGraph v1.2，含意图路由）
  - context_engine: 动态 Context 组装管道（替代硬编码系统提示）
  - tool_registry: 工具注册表（Copy-on-Write 并发安全）
  - intent_router: 意图路由（向量相似度快速匹配）
  - rag_pipeline: RAG 管道（LlamaIndex + Qdrant）
  - memory_manager: 记忆系统（Redis 短期 + Qdrant 长期）
  - workflow_engine: 工作流引擎（DAG 拓扑排序 + 逐步执行）
  - tracing: 可观测性（LangFuse + 结构化日志）
  - eval_pipeline: 评估流水线（规则初筛 + LLM 复核）
  - skill_executor: 技能执行器（桥接技能与 Tool Calling）

v1.2 重构变更:
  - state.py: AgentState 从 Pydantic BaseModel 迁移到 TypedDict
  - engine.py: 意图路由纳入图内，Context Engine 动态组装
  - agent_service.py: 流式对话改用 astream + stream_mode（替代 astream_events）
  - context_engine.py: 新增，多源 Context 组装管道
  - tool_registry.py: Copy-on-Write 快照，并发安全
  - tracing.py: 结构化追踪，AgentTrace 数据结构
"""
