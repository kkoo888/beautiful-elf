"""Agent 模块 — LLM Agent 引擎核心组件

核心模块:
  - llm_service: LLM 服务工厂（多供应商 + LangChain 兼容）
  - engine: Agent 引擎（LangGraph StateGraph）
  - tool_registry: 工具注册表（风险分级 + 参数校验）
  - context_manager: 上下文窗口管理
  - intent_router: 意图路由（向量相似度快速匹配）
  - rag_pipeline: RAG 管道（LlamaIndex + Qdrant）
  - memory_manager: 记忆系统（Redis 短期 + Qdrant 长期）
  - workflow_engine: 工作流引擎（DAG 拓扑排序 + 逐步执行）
  - tracing: LangFuse 可观测性
  - eval_pipeline: 评估流水线（规则初筛 + LLM 复核）
"""
