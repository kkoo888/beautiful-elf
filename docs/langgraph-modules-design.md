# Beautiful-Elf LangGraph 模块流程设计

> 基于 `langgraph-for-agents` 技能的参考模式设计
> 设计日期：2026-05-30 | 修订：2026-05-30 v2（修复 16 项审查问题）

---

## 📐 设计模式总览

本项目用到 4 种 LangGraph 核心模式：

| 模式 | 用途 | 参考 |
|---|---|---|
| **Routing** | 查询分类 → 选择处理路径 | `langgraph_workflow_routing.py` |
| **Orchestrator-Worker** | 主代理拆任务 → 子代理并行执行 | `langgraph_workflow_orch_worker.py` |
| **Evaluator-Optimizer** | 生成 → 评估 → 迭代优化 | `langgraph_workflow_eval_optim.py` |
| **Human-in-the-Loop** | 需要人工确认时暂停等待 | `langgraph_human_in_the_loop.py` |

---

## 📊 新增数据表

### T1. rag_query_logs — RAG 多跳推理日志

```sql
CREATE TABLE rag_query_logs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED DEFAULT NULL COMMENT '关联对话 ID',
    user_id         BIGINT UNSIGNED DEFAULT NULL COMMENT '用户 ID',
    query           TEXT            NOT NULL COMMENT '用户原始问题',
    complexity      VARCHAR(16)     NOT NULL COMMENT 'simple/complex',
    sub_questions   JSON            DEFAULT NULL COMMENT '拆解后的子问题列表',
    retrieval_steps JSON            DEFAULT NULL COMMENT '每步检索详情 [{step, query, chunks_count, top_score, doc_ids}]',
    evaluations     JSON            DEFAULT NULL COMMENT '每步评估结果 [{step, need_more, reason}]',
    answer          TEXT            NOT NULL COMMENT '最终生成的答案',
    sources         JSON            DEFAULT NULL COMMENT '引用来源 [{doc_id, chunk_index, score, text_preview}]',
    total_steps     TINYINT         NOT NULL DEFAULT 1 COMMENT '实际检索步数',
    duration_ms     INT UNSIGNED    DEFAULT 0 COMMENT '总耗时 (毫秒)',
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_rag_conversation (conversation_id),
    INDEX idx_rag_user (user_id),
    INDEX idx_rag_created (created_at),
    INDEX idx_rag_complexity (complexity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RAG 多跳推理查询日志';
```

### T2. subagent_definitions — 子代理定义

```sql
CREATE TABLE subagent_definitions (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(128)    NOT NULL COMMENT 'Agent 唯一标识 (如 retriever, analyzer)',
    display_name    VARCHAR(256)    DEFAULT '' COMMENT '显示名称',
    description     VARCHAR(1024)   DEFAULT '' COMMENT '职责描述',
    agent_type      VARCHAR(64)     NOT NULL COMMENT '类型 (retriever/analyzer/coder/reviewer/generator/planner)',
    system_prompt   TEXT            DEFAULT NULL COMMENT '系统提示词 (定义行为准则)',
    llm_model       VARCHAR(128)    DEFAULT NULL COMMENT '使用的 LLM 模型 (为空则用默认)',
    temperature     DECIMAL(2,1)    DEFAULT 0.7 COMMENT '模型温度',
    tools           JSON            DEFAULT NULL COMMENT '可用工具列表 [{name, description, json_schema}]',
    max_iterations  INT UNSIGNED    DEFAULT 10 COMMENT '最大推理迭代次数',
    timeout_seconds INT UNSIGNED    DEFAULT 120 COMMENT '单次执行超时 (秒)',
    enabled         TINYINT         NOT NULL DEFAULT 1,
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_subagent_name (name),
    INDEX idx_subagent_type (agent_type),
    INDEX idx_subagent_enabled (deleted, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='子代理定义';
```

### T3. subagent_runs — 子代理运行记录

```sql
CREATE TABLE subagent_runs (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    definition_id   BIGINT UNSIGNED NOT NULL COMMENT '子代理定义 ID',
    parent_run_id   BIGINT UNSIGNED DEFAULT NULL COMMENT '父工作流运行 ID（被工作流调用时）',
    parent_type     VARCHAR(32)     DEFAULT NULL COMMENT '父级类型 (workflow/expert_team)',
    status          TINYINT         NOT NULL DEFAULT 0 COMMENT '0=待运行, 1=运行中, 2=成功, 3=失败, 4=已取消, 5=已暂停',
    task_input      TEXT            NOT NULL COMMENT '任务输入',
    output_json     JSON            DEFAULT NULL COMMENT '输出结果',
    error_message   VARCHAR(2048)   DEFAULT '' COMMENT '错误信息',
    iterations      INT UNSIGNED    DEFAULT 0 COMMENT '实际推理迭代次数',
    started_at      DATETIME        DEFAULT NULL,
    finished_at     DATETIME        DEFAULT NULL,
    duration_ms     INT UNSIGNED    DEFAULT 0,
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_subagent_runs_def (definition_id, status),
    INDEX idx_subagent_runs_parent (parent_run_id, parent_type),
    INDEX idx_subagent_runs_status (status),
    INDEX idx_subagent_runs_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='子代理运行记录';
```

### T4. workflow_templates — 工作流模板

```sql
CREATE TABLE workflow_templates (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(256)    NOT NULL COMMENT '模板名称',
    description     VARCHAR(1024)   DEFAULT '' COMMENT '模板描述',
    category        VARCHAR(64)     DEFAULT '' COMMENT '分类 (document/code/data/research/custom)',
    icon            VARCHAR(256)    DEFAULT '' COMMENT '图标 URL',
    dag_json        JSON            NOT NULL COMMENT 'DAG 定义模板 (节点中的参数可引用变量)',
    variables       JSON            DEFAULT NULL COMMENT '可替换变量 [{name, type, default_value, description, required}]',
    usage_count     INT UNSIGNED    DEFAULT 0 COMMENT '使用次数',
    sort_order      INT             NOT NULL DEFAULT 0,
    enabled         TINYINT         NOT NULL DEFAULT 1,
    deleted         TINYINT         NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_wf_templates_category (category),
    INDEX idx_wf_templates_usage (usage_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流模板';
```

### T5. 已有表补充字段

```sql
-- workflow_runs 补充：支持 HITL 暂停查询
ALTER TABLE workflow_runs ADD COLUMN run_type TINYINT NOT NULL DEFAULT 0
    COMMENT '0=工作流, 1=子代理调用' AFTER workflow_id;
ALTER TABLE workflow_runs ADD COLUMN paused_node VARCHAR(128) DEFAULT NULL
    COMMENT 'HITL 暂停的节点名 (NULL=未暂停)' AFTER error_message;
ALTER TABLE workflow_runs ADD COLUMN pause_config JSON DEFAULT NULL
    COMMENT 'HITL 暂停时的上下文 (interrupt 传给前端的数据)' AFTER paused_node;

-- workflow_step_runs 补充：记录技能/工具调用详情
ALTER TABLE workflow_step_runs ADD COLUMN skills_used JSON DEFAULT NULL
    COMMENT '该节点调用的技能列表 [{skill_id, name, status}]' AFTER output_json;
ALTER TABLE workflow_step_runs ADD COLUMN tools_used JSON DEFAULT NULL
    COMMENT '该节点调用的工具列表 [{tool_id, name, status}]' AFTER skills_used;
```

---

## 一、RAG 多跳推理模块

### 定位
处理复杂用户问题，自动拆解为多步检索，用状态机管理推理链。查询过程记录到 `rag_query_logs` 表。

### 设计模式：Routing + Evaluator-Optimizer

### 流程图

```
                          ┌─────────────┐
                          │   START     │
                          └──────┬──────┘
                                 │
                          ┌──────▼──────┐
                          │  classify   │  ← LLM 判断问题复杂度
                          │  (Routing)  │
                          └──────┬──────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
               "simple"                  "complex"
                    │                         │
                    │                  ┌──────▼──────┐
                    │                  │ decompose   │  ← 拆解为 2-3 个子问题
                    │                  │ (规划步骤)   │
                    │                  └──────┬──────┘
                    │                         │
                    ▼                         ▼
             ┌──────────┐            ┌──────────────┐
             │ retrieve │            │ retrieve     │  ← 按子问题逐个检索
             │ (单次)   │            │ (多轮, step) │     Qdrant 混合检索
             └────┬─────┘            └──────┬───────┘
                  │                         │
                  │                  ┌──────▼──────┐
                  │                  │ evaluate    │  ← 评估信息是否充分
                  │                  │ (够了吗?)   │
                  │                  └──────┬──────┘
                  │                         │
                  │              ┌──────────┴──────────┐
                  │              │                     │
                  │         need_more              enough
                  │         & step<max                │
                  │              │                     │
                  │         ┌────▼─────┐               │
                  │         │ retrieve │ (补充检索)     │
                  │         └────┬─────┘               │
                  │              │ (回到 evaluate)      │
                  │              │                     │
                  ▼              ▼                     ▼
                  └──────────────┴──────────────┌─────▼──────┐
                                                │ deduplicate│  ← 去重 (按 doc_id+chunk)
                                                │ + synthesize│  ← 合成答案 + 引用来源
                                                └─────┬──────┘
                                                      │
                                               ┌──────▼──────┐
                                               │  log_query  │  ← 记录到 rag_query_logs
                                               │  (持久化)    │
                                               └──────┬──────┘
                                                      │
                                               ┌──────▼──────┐
                                               │    END      │
                                               └─────────────┘
```

### State 定义

```python
class RAGState(TypedDict):
    # === 请求上下文 ===
    query: str                                          # 用户原始问题
    conversation_id: int | None                         # 关联对话 ID（用于写回 messages 表）
    user_id: int | None                                 # 用户 ID

    # === 多跳推理状态 ===
    complexity: str                                     # "simple" | "complex"
    sub_questions: list[str]                            # 拆解后的子问题
    retrieved_chunks: Annotated[list[dict], operator.add]  # 检索结果（累加，允许去重在 synthesize 前）
    current_step: int                                   # 当前检索步骤
    max_steps: int                                      # 最大检索步数（默认 3）
    evaluation: dict                                    # {"need_more": bool, "reason": str}

    # === 过程记录（用于 rag_query_logs）===
    retrieval_steps: Annotated[list[dict], operator.add]  # 每步检索元数据
    evaluations: Annotated[list[dict], operator.add]      # 每步评估结果

    # === 输出 ===
    answer: str                                         # 最终答案
    sources: list[dict]                                 # 引用来源（去重后）
    duration_ms: int                                    # 总耗时
```

### 核心节点

```python
import time
from langgraph.graph import StateGraph, START, END
from typing import Annotated
import operator

# 1. 分类节点 — 判断问题复杂度
def classify(state: RAGState) -> dict:
    """简单问题直接检索，复杂问题进入多跳"""
    prompt = f"""判断以下问题是否需要多步检索：
    - 简单：单个概念、直接事实查询 → "simple"
    - 复杂：需要关联多个知识点、对比分析、因果推理 → "complex"
    
    问题：{state['query']}
    只返回 simple 或 complex"""
    
    result = llm.invoke(prompt)
    return {"complexity": result.content.strip().lower()}

# 2. 拆解节点 — 将复杂问题分解为子问题
def decompose(state: RAGState) -> dict:
    """将复杂问题拆解为可独立检索的子问题"""
    prompt = f"""将以下复杂问题拆解为 2-3 个可独立检索的子问题：
    问题：{state['query']}
    
    返回 JSON：{{"sub_questions": ["子问题1", "子问题2"]}}"""
    
    result = llm.invoke(prompt)
    plan = json.loads(result.content)
    return {"sub_questions": plan["sub_questions"], "current_step": 0}

# 3. 检索节点 — 调用 Qdrant 混合检索
def retrieve(state: RAGState) -> dict:
    """从知识库检索相关片段，记录每步检索元数据"""
    # 简单模式用原始问题，复杂模式用子问题
    if state["complexity"] == "simple":
        q = state["query"]
    else:
        q = state["sub_questions"][state["current_step"]]
    
    results = qdrant_client.search(
        collection_name="knowledge_chunks",
        query_vector=embed(q),
        query_filter=Filter(must_not=[FieldCondition(key="deleted", match=MatchValue(value=True))]),
        limit=5,
    )
    
    chunks = [
        {"text": r.payload["text"], "doc_id": r.payload["doc_id"],
         "chunk_index": r.payload.get("chunk_index", 0), "score": r.score}
        for r in results
    ]
    
    # 记录本步检索元数据（轻量，不含全文）
    step_meta = {
        "step": state.get("current_step", 0),
        "query": q,
        "chunks_count": len(chunks),
        "top_score": chunks[0]["score"] if chunks else 0,
        "doc_ids": list(set(c["doc_id"] for c in chunks)),
    }
    
    return {
        "retrieved_chunks": chunks,
        "current_step": state.get("current_step", 0) + 1,
        "retrieval_steps": [step_meta],
    }

# 4. 评估节点 — 判断信息是否充分
def evaluate(state: RAGState) -> dict:
    """评估已检索的信息是否足以回答问题"""
    context = "\n".join([c["text"] for c in state["retrieved_chunks"]])
    prompt = f"""基于以下已检索信息，判断是否能完整回答用户问题：
    
    用户问题：{state['query']}
    已检索信息：{context}
    
    返回 JSON：{{"need_more": true/false, "reason": "原因"}}"""
    
    result = llm.invoke(prompt)
    eval_result = json.loads(result.content)
    
    # 记录评估结果
    eval_meta = {
        "step": state["current_step"] - 1,
        "need_more": eval_result["need_more"],
        "reason": eval_result["reason"],
    }
    
    return {"evaluation": eval_result, "evaluations": [eval_meta]}

# 5. 去重 + 合成节点
def synthesize(state: RAGState) -> dict:
    """去重后合成最终答案，记录到 rag_query_logs"""
    # 按 doc_id + chunk_index 去重
    seen = set()
    unique_chunks = []
    for c in state["retrieved_chunks"]:
        key = (c["doc_id"], c.get("chunk_index", 0))
        if key not in seen:
            seen.add(key)
            unique_chunks.append(c)
    
    context = "\n---\n".join([c["text"] for c in unique_chunks])
    prompt = f"""基于以下参考资料回答用户问题，并标注引用来源。
    
    问题：{state['query']}
    参考资料：{context}
    
    要求：
    1. 答案必须基于参考资料，不要编造
    2. 在相关段落后标注 [来源: doc_id]
    3. 如果资料不足，明确说明"""
    
    result = llm.invoke(prompt)
    
    # 构建去重后的来源列表
    sources = [
        {"doc_id": c["doc_id"], "chunk_index": c.get("chunk_index", 0),
         "score": c["score"], "text_preview": c["text"][:100]}
        for c in unique_chunks
    ]
    
    return {"answer": result.content, "sources": sources}

# 6. 日志持久化节点
def log_query(state: RAGState) -> dict:
    """将查询过程记录到 rag_query_logs 表"""
    db.execute(
        """INSERT INTO rag_query_logs 
           (conversation_id, user_id, query, complexity, sub_questions,
            retrieval_steps, evaluations, answer, sources, total_steps, duration_ms)
           VALUES (:conv_id, :user_id, :query, :complexity, :sub_questions,
                   :retrieval_steps, :evaluations, :answer, :sources, :total_steps, :duration_ms)""",
        {
            "conv_id": state.get("conversation_id"),
            "user_id": state.get("user_id"),
            "query": state["query"],
            "complexity": state["complexity"],
            "sub_questions": json.dumps(state.get("sub_questions")),
            "retrieval_steps": json.dumps(state.get("retrieval_steps", [])),
            "evaluations": json.dumps(state.get("evaluations", [])),
            "answer": state["answer"],
            "sources": json.dumps(state["sources"]),
            "total_steps": state.get("current_step", 1),
            "duration_ms": state.get("duration_ms", 0),
        },
    )
    return {}
```

### 路由逻辑

```python
def route_by_complexity(state: RAGState) -> str:
    """路由函数：只读 State，返回字符串，不做任何修改"""
    if state["complexity"] == "simple":
        return "retrieve_simple"
    return "decompose"

def route_by_evaluation(state: RAGState) -> str:
    """路由函数：判断是否需要继续检索"""
    if state["evaluation"]["need_more"] and state["current_step"] < state["max_steps"]:
        return "retrieve"  # 继续检索
    return "synthesize"    # 信息足够，合成答案
```

### 图构建

```python
workflow = StateGraph(RAGState)

workflow.add_node("classify", classify)
workflow.add_node("decompose", decompose)
workflow.add_node("retrieve", retrieve)           # 复杂模式：多轮检索
workflow.add_node("retrieve_simple", retrieve)     # 简单模式：单次检索（复用同一函数）
workflow.add_node("evaluate", evaluate)
workflow.add_node("synthesize", synthesize)
workflow.add_node("log_query", log_query)

workflow.add_edge(START, "classify")

# 分类路由
workflow.add_conditional_edges(
    "classify",
    route_by_complexity,
    {"retrieve_simple": "retrieve_simple", "decompose": "decompose"},
)

# 简单路径：检索 → 合成
workflow.add_edge("retrieve_simple", "synthesize")

# 复杂路径：拆解 → 检索 → 评估 → (继续/合成)
workflow.add_edge("decompose", "retrieve")
workflow.add_edge("retrieve", "evaluate")
workflow.add_conditional_edges(
    "evaluate",
    route_by_evaluation,
    {"retrieve": "retrieve", "synthesize": "synthesize"},
)

# 合成 → 日志 → 结束
workflow.add_edge("synthesize", "log_query")
workflow.add_edge("log_query", END)

rag_graph = workflow.compile()
```

---

## 二、子代理系统模块

### 定位
主代理根据任务复杂度动态调度子代理（从 `subagent_definitions` 表加载），子代理独立运行并返回结果，支持暂停/终止。

### 设计模式：Orchestrator-Worker

### 流程图

```
                    ┌──────────────┐
                    │    START     │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ load_agents  │  ← 从 subagent_definitions 加载 Agent 配置
                    │ (加载配置)    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  orchestrator│  ← 主代理分析任务，制定执行计划
                    │  (拆解任务)   │     产出: [{task, agent_def_id, deps}, ...]
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │ Send()     │ Send()     │ Send()
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────┐
       │ worker_1 │ │ worker_2 │ │ worker_3 │  ← 各子代理独立执行
       │ (检索)    │ │ (分析)    │ │ (生成)    │     每个写入 subagent_runs
       └────┬─────┘ └────┬─────┘ └────┬─────┘
            │             │             │
            │    带依赖上下文传递（context）│
            └─────────────┼─────────────┘
                          │
                   ┌──────▼───────┐
                   │  synthesizer │  ← 汇总所有子代理结果
                   │  (结果合并)   │
                   └──────┬───────┘
                          │
                   ┌──────▼───────┐
                   │     END      │
                   └──────────────┘
```

### State 定义

```python
class OrchestratorState(TypedDict):
    # === 任务输入 ===
    task: str                                                    # 原始任务描述
    workflow_id: str                                             # 关联工作流 ID（可选）
    run_id: str                                                  # 本次运行 ID

    # === Agent 配置（load_agents 填充）===
    agent_defs: list[dict]                                       # 可用子代理定义列表

    # === 编排（orchestrator 填充）===
    task_plan: list[dict]                                        # 任务拆解计划

    # === 执行结果（Worker 累加）===
    sub_agent_results: Annotated[list[dict], operator.add]       # 子代理结果

    # === 输出 ===
    final_result: str                                            # 最终汇总结果

class WorkerState(TypedDict):
    sub_task: dict                                               # 子任务 {task, agent_def_id, context}
    sub_agent_results: Annotated[list[dict], operator.add]       # 结果累加
```

### 核心节点

```python
# 1. 加载子代理配置
def load_agents(state: OrchestratorState) -> dict:
    """从 subagent_definitions 表加载可用的 Agent 配置"""
    agents = db.query(SubagentDefinition).filter(
        SubagentDefinition.deleted == 0,
        SubagentDefinition.enabled == 1,
    ).all()
    
    agent_defs = [
        {
            "id": a.id,
            "name": a.name,
            "display_name": a.display_name,
            "type": a.agent_type,
            "description": a.description,
            "system_prompt": a.system_prompt,
            "llm_model": a.llm_model,
            "temperature": float(a.temperature) if a.temperature else 0.7,
            "tools": a.tools or [],
            "max_iterations": a.max_iterations,
            "timeout_seconds": a.timeout_seconds,
        }
        for a in agents
    ]
    return {"agent_defs": agent_defs}

# 2. 编排节点 — 分析任务，制定执行计划
def orchestrator(state: OrchestratorState) -> dict:
    """主代理分析任务并拆解为可并行/串行的子任务"""
    agents_desc = "\n".join([
        f"- {a['name']} ({a['type']}): {a['description']}"
        for a in state["agent_defs"]
    ])
    
    prompt = f"""分析以下任务，拆解为 2-5 个子任务。
    
    任务：{state['task']}
    
    可用子代理：
    {agents_desc}
    
    每个子任务包含：
    - task: 子任务描述
    - agent_name: 执行子代理的 name
    - dependencies: 依赖的其他子任务索引列表（空数组表示可立即执行）
    
    返回 JSON：{{"sub_tasks": [...]}}"""
    
    result = llm.invoke(prompt)
    plan = json.loads(result.content)
    
    # 记录到 subagent_runs（创建运行记录）
    save_subagent_run(state["run_id"], status=1, plan=plan)
    
    # WebSocket 推送
    ws_broadcast("subagent_progress", {
        "run_id": state["run_id"],
        "phase": "orchestrator",
        "plan": plan["sub_tasks"],
    })
    
    return {"task_plan": plan["sub_tasks"]}

# 3. 工作节点 — 子代理执行
def worker(state: WorkerState) -> dict:
    """单个子代理执行其子任务，结果写入 subagent_runs"""
    sub_task = state["sub_task"]
    context = sub_task.get("context", "")
    
    # 从 agent_defs 中找到对应配置
    agent_def = next(
        (a for a in state.get("agent_defs", []) if a["name"] == sub_task["agent_name"]),
        None
    )
    if not agent_def:
        # 回退：用默认 LLM
        agent_def = {"system_prompt": f"你是{sub_task['agent_name']}，请完成任务。"}
    
    # 创建子代理运行记录
    sub_run_id = save_subagent_definition_run(
        definition_id=agent_def.get("id"),
        parent_run_id=state.get("run_id"),
        task_input=sub_task["task"],
        status=1,  # 运行中
    )
    
    # WebSocket：子代理开始
    ws_broadcast("subagent_progress", {
        "run_id": state.get("run_id"),
        "phase": "agent_start",
        "agent_name": sub_task["agent_name"],
        "sub_task": sub_task["task"],
    })
    
    try:
        # 构建 LangChain Agent（基于配置）
        tools = load_tools_for_agent(agent_def.get("tools", []))
        agent = create_react_agent(
            model=get_llm(agent_def.get("llm_model"), agent_def.get("temperature", 0.7)),
            tools=tools,
            prompt=agent_def.get("system_prompt", ""),
        )
        
        # 执行
        result = agent.invoke({
            "messages": [
                SystemMessage(content=agent_def.get("system_prompt", "")),
                HumanMessage(content=f"任务：{sub_task['task']}\n\n上下文：{context}" if context else sub_task["task"]),
            ]
        })
        
        output = result["messages"][-1].content
        
        # 更新运行记录
        save_subagent_definition_run(sub_run_id, status=2, output_json={"output": output})
        
        # WebSocket：子代理完成
        ws_broadcast("subagent_progress", {
            "run_id": state.get("run_id"),
            "phase": "agent_complete",
            "agent_name": sub_task["agent_name"],
            "output": output[:300],
        })
        
        return {"sub_agent_results": [{
            "agent_name": sub_task["agent_name"],
            "agent_type": agent_def.get("type", "unknown"),
            "sub_task": sub_task["task"],
            "output": output,
            "status": "completed",
        }]}
        
    except Exception as e:
        save_subagent_definition_run(sub_run_id, status=3, error=str(e))
        return {"sub_agent_results": [{
            "agent_name": sub_task["agent_name"],
            "sub_task": sub_task["task"],
            "output": "",
            "status": "failed",
            "error": str(e),
        }]}

# 4. 汇总节点
def synthesizer(state: OrchestratorState) -> dict:
    """汇总所有子代理的执行结果"""
    results_text = "\n\n".join([
        f"### {r['agent_name']} ({r['agent_type']})\n"
        f"**任务**: {r['sub_task']}\n"
        f"**状态**: {r['status']}\n"
        f"**输出**: {r.get('output', r.get('error', '无'))}"
        for r in state["sub_agent_results"]
    ])
    
    prompt = f"""基于以下各子代理的执行结果，汇总为最终答案：
    
    原始任务：{state['task']}
    
    子代理结果：
    {results_text}
    
    请给出完整、连贯的最终回答。"""
    
    result = llm.invoke(prompt)
    
    # 更新运行记录
    save_subagent_run(state["run_id"], status=2, output_json={"final_result": result.content})
    
    ws_broadcast("subagent_progress", {
        "run_id": state["run_id"],
        "phase": "completed",
        "final_result": result.content,
    })
    
    return {"final_result": result.content}
```

### 并行调度（带依赖上下文传递）

```python
def assign_workers(state: OrchestratorState) -> list[Send]:
    """根据任务计划分配工作节点，带依赖上下文传递"""
    sends = []
    completed = {r["agent_name"] for r in state["sub_agent_results"]}
    
    for plan in state["task_plan"]:
        agent_name = plan["agent_name"]
        if agent_name in completed:
            continue
        
        # 检查依赖是否已完成
        deps = plan.get("dependencies", [])
        dep_names = [state["task_plan"][d]["agent_name"] for d in deps if d < len(state["task_plan"])]
        
        if all(dn in completed for dn in dep_names):
            # 收集依赖子代理的输出作为上下文
            dep_context = "\n\n".join([
                f"[{r['agent_name']}的输出]: {r['output']}"
                for r in state["sub_agent_results"]
                if r["agent_name"] in dep_names
            ])
            
            sends.append(Send("worker", {
                "sub_task": {
                    "task": plan["task"],
                    "agent_name": agent_name,
                    "context": dep_context,  # ← 传递依赖上下文
                }
            }))
    
    return sends if sends else [Send("synthesizer", {})]
```

### 子代理管理 API

```python
# 终止子代理
@router.post("/subagent-runs/{run_id}/cancel")
async def cancel_subagent(run_id: int):
    """取消运行中的子代理"""
    run = db.query(SubagentRun).get(run_id)
    if run.status != 1:  # 不是运行中
        raise HTTPException(400, "只能取消运行中的子代理")
    
    # 通过 Celery revoke 终止任务
    celery_app.control.revoke(run.task_id, terminate=True)
    save_subagent_definition_run(run_id, status=4)  # 已取消
    
    return {"status": "cancelled"}

# 查询子代理运行列表
@router.get("/subagent-runs")
async def list_subagent_runs(status: int = None, parent_run_id: int = None):
    """查询子代理运行历史，支持按状态和父级过滤"""
    query = db.query(SubagentRun).filter(SubagentRun.deleted == 0)
    if status is not None:
        query = query.filter(SubagentRun.status == status)
    if parent_run_id:
        query = query.filter(SubagentRun.parent_run_id == parent_run_id)
    return query.order_by(SubagentRun.created_at.desc()).all()
```

### 图构建

```python
workflow = StateGraph(OrchestratorState)

workflow.add_node("load_agents", load_agents)
workflow.add_node("orchestrator", orchestrator)
workflow.add_node("worker", worker)
workflow.add_node("synthesizer", synthesizer)

workflow.add_edge(START, "load_agents")
workflow.add_edge("load_agents", "orchestrator")
workflow.add_conditional_edges("orchestrator", assign_workers, ["worker", "synthesizer"])
workflow.add_edge("worker", "synthesizer")
workflow.add_edge("synthesizer", END)

subagent_graph = workflow.compile()
```

---

## 三、工作流模块（通用 DAG 引擎）

### 定位
用户可自定义工作流，节点可以是工具、技能或子代理，支持手动/定时/事件触发。HITL 暂停状态可通过 `paused_node` 字段查询。

### 设计模式：Routing + Parallelization + HITL

### 流程图

```
┌──────────────┐
│    START     │
└──────┬───────┘
       │
┌──────▼───────┐
│  load_dag    │  ← 从 MySQL workflows.dag_json 加载 DAG 定义
│  (解析工作流) │
└──────┬───────┘
       │
┌──────▼───────┐
│  validate    │  ← 校验 DAG 合法性（无环、节点存在）
│  (DAG 校验)   │
└──────┬───────┘
       │
┌──────▼──────────────────────────────────────────────┐
│              execution_loop (循环)                   │
│                                                     │
│  ┌──────────────┐                                   │
│  │ get_ready    │  ← 找出所有依赖已满足的 pending 节点│
│  │ (就绪节点)    │                                   │
│  └──────┬───────┘                                   │
│         │                                           │
│    ┌────┴────┐                                      │
│    │         │                                      │
│  有就绪    无就绪 → finalize                         │
│    │                                                │
│    ▼                                                │
│  ┌──────────────────────────────────────────┐       │
│  │ assign_ready_nodes (Send 并行分发)        │       │
│  │                                          │       │
│  │  对每个就绪节点:                           │       │
│  │    → tool    → execute_tool_node          │       │
│  │    → skill   → execute_skill_node         │       │
│  │    → agent   → execute_agent_node         │       │
│  │    → human   → human_confirm_node         │       │
│  └──────────────┬───────────────────────────┘       │
│                 │                                    │
│  ┌──────────────▼───────────────────────────┐       │
│  │ check_status (检查所有节点执行结果)        │       │
│  └──────────────┬───────────────────────────┘       │
│                 │                                    │
│          ┌──────┴──────┐                             │
│          │             │                             │
│      has_human_wait  all_done                        │
│          │             │                             │
│          ▼             │                             │
│  ┌──────────────┐      │                             │
│  │ update_pause │      │  ← 记录 paused_node 到 DB   │
│  │ (记录暂停)    │      │     WebSocket 推送暂停状态    │
│  └──────┬───────┘      │                             │
│         │              │                             │
│        END        回到 get_ready                     │
│                                                     │
└─────────────────────────┼───────────────────────────┘
                          │
                   ┌──────▼───────┐
                   │  finalize    │  ← 汇总结果，更新 workflow_runs
                   │  (完成)       │
                   └──────┬───────┘
                          │
                   ┌──────▼───────┐
                   │     END      │
                   └──────────────┘
```

### State 定义

```python
class WorkflowState(TypedDict):
    # === 运行标识 ===
    workflow_id: str                     # 工作流定义 ID
    run_id: str                          # 本次运行 ID

    # === DAG 定义 ===
    dag: dict                            # DAG 定义 {nodes: [], edges: []}

    # === 执行状态 ===
    node_states: dict[str, str]          # 各节点状态: pending/running/completed/failed/human_wait
    node_outputs: dict[str, any]         # 各节点输出
    ready_nodes: list[str]               # 当前就绪节点
    has_human_wait: bool                 # 是否有节点在等待人工确认
    human_wait_node: str | None          # 等待人工确认的节点 ID

    # === 输出 ===
    final_output: dict                   # 最终输出
    error: str | None                    # 错误信息
```

### 核心节点

```python
# 1. 加载 DAG
def load_dag(state: WorkflowState) -> dict:
    """从 MySQL 加载工作流定义"""
    workflow = db.query(Workflow).get(state["workflow_id"])
    dag = json.loads(workflow.dag_json)
    node_states = {node["id"]: "pending" for node in dag["nodes"]}
    return {"dag": dag, "node_states": node_states, "node_outputs": {}, "has_human_wait": False}

# 2. DAG 校验
def validate_dag(state: WorkflowState) -> dict:
    """校验 DAG 无环、节点引用合法"""
    dag = state["dag"]
    if has_cycle(dag["edges"]):
        raise ValueError("工作流 DAG 存在循环依赖")
    node_ids = {n["id"] for n in dag["nodes"]}
    for edge in dag["edges"]:
        if edge["from"] not in node_ids or edge["to"] not in node_ids:
            raise ValueError(f"边引用了不存在的节点: {edge}")
    return {}

# 3. 获取就绪节点
def get_ready_nodes(state: WorkflowState) -> dict:
    """找出所有前置依赖已满足的 pending 节点"""
    ready = []
    for node in state["dag"]["nodes"]:
        nid = node["id"]
        if state["node_states"][nid] != "pending":
            continue
        deps = [e["from"] for e in state["dag"]["edges"] if e["to"] == nid]
        if all(state["node_states"].get(d) == "completed" for d in deps):
            ready.append(nid)
    return {"ready_nodes": ready, "has_human_wait": False, "human_wait_node": None}

# 4. 执行单个节点（Send 分发目标）
def execute_single_node(state: dict) -> dict:
    """执行单个工作流节点（通过 Send 接收 node_id）"""
    node_id = state["node_id"]
    workflow_id = state["workflow_id"]
    run_id = state["run_id"]
    
    # 加载节点定义
    dag = state["dag"]
    node = next(n for n in dag["nodes"] if n["id"] == node_id)
    node_type = node["type"]
    
    # 更新状态
    save_step_run(run_id, node_id, "running")
    ws_broadcast("workflow_progress", {"run_id": run_id, "node": node_id, "status": "running"})
    
    try:
        if node_type == "tool":
            result = execute_tool(node["config"]["tool_name"], node["config"]["params"])
        elif node_type == "skill":
            result = execute_skill(node["config"]["skill_name"], get_node_input(dag, node_id))
        elif node_type == "agent":
            result = execute_subagent_from_def(node["config"]["agent_def_id"], get_node_input(dag, node_id))
        elif node_type == "human":
            # 返回 interrupt 标记，不在此处调用 interrupt()
            return {
                "node_outputs": {node_id: "__human_wait__"},
                "has_human_wait": True,
                "human_wait_node": node_id,
            }
        
        save_step_run(run_id, node_id, "completed", output=result)
        ws_broadcast("workflow_progress", {"run_id": run_id, "node": node_id, "status": "completed"})
        
        return {"node_outputs": {node_id: result}}
        
    except Exception as e:
        save_step_run(run_id, node_id, "failed", error=str(e))
        ws_broadcast("workflow_progress", {"run_id": run_id, "node": node_id, "status": "failed", "error": str(e)})
        return {"error": str(e)}

# 5. 更新暂停状态（节点函数，不是路由函数）
def update_pause_state(state: WorkflowState) -> dict:
    """记录 HITL 暂停状态到数据库（节点函数，有副作用）"""
    node_id = state["human_wait_node"]
    node = next(n for n in state["dag"]["nodes"] if n["id"] == node_id)
    
    # 更新 workflow_runs 的 paused_node 字段
    db.execute(
        "UPDATE workflow_runs SET paused_node = :node, pause_config = :config WHERE id = :run_id",
        {
            "node": node_id,
            "config": json.dumps({
                "prompt": node["config"].get("confirm_prompt", "请确认是否继续执行？"),
                "current_output": state["node_outputs"].get(node_id, ""),
            }),
            "run_id": state["run_id"],
        },
    )
    db.commit()
    
    ws_broadcast("workflow_progress", {
        "run_id": state["run_id"],
        "node": node_id,
        "status": "human_wait",
        "prompt": node["config"].get("confirm_prompt", "请确认是否继续执行？"),
    })
    
    # 更新节点状态
    new_states = dict(state["node_states"])
    new_states[node_id] = "human_wait"
    return {"node_states": new_states}

# 6. 完成
def finalize(state: WorkflowState) -> dict:
    """汇总结果，更新运行记录"""
    final_output = {}
    end_nodes = get_end_nodes(state["dag"])
    for nid in end_nodes:
        final_output[nid] = state["node_outputs"].get(nid)
    
    save_workflow_run(state["workflow_id"], state["run_id"], status=2, output=final_output)
    ws_broadcast("workflow_complete", {"run_id": state["run_id"], "output": final_output})
    
    return {"final_output": final_output}
```

### 路由逻辑（纯函数，不修改 State）

```python
def route_after_ready(state: WorkflowState) -> str:
    """路由函数：只读 State，返回字符串"""
    if not state["ready_nodes"]:
        return "finalize"
    return "assign_ready_nodes"

def route_after_check(state: WorkflowState) -> str:
    """路由函数：检查是否有节点在等待人工确认"""
    if state.get("has_human_wait"):
        return "update_pause"
    if has_remaining_pending(state):
        return "get_ready"
    return "finalize"

def assign_ready_nodes(state: WorkflowState) -> list[Send]:
    """将就绪节点分发到对应的执行节点（Send 并行）"""
    sends = []
    for node_id in state["ready_nodes"]:
        node = next(n for n in state["dag"]["nodes"] if n["id"] == node_id)
        sends.append(Send("execute_single_node", {
            "node_id": node_id,
            "dag": state["dag"],
            "workflow_id": state["workflow_id"],
            "run_id": state["run_id"],
        }))
    return sends
```

### HITL 恢复 API

```python
@router.post("/workflows/{workflow_id}/runs/{run_id}/resume")
async def resume_workflow_endpoint(
    workflow_id: int,
    run_id: int,
    body: dict,  # {"approved": true/false, "data": {...}}
    db: AsyncSession = Depends(get_db),
):
    """恢复被 HITL 暂停的工作流"""
    run = db.query(WorkflowRun).get(run_id)
    if not run.paused_node:
        raise HTTPException(400, "该工作流未处于暂停状态")
    
    # 清除暂停状态
    run.paused_node = None
    run.pause_config = None
    db.commit()
    
    # 通过 LangGraph Checkpointer 恢复
    graph = build_workflow_graph(str(workflow_id))
    config = {"configurable": {"thread_id": str(run_id)}}
    result = graph.invoke(Command(resume=body), config=config)
    
    return {"status": "resumed", "output": result}

# 查询等待人工确认的工作流
@router.get("/workflows/runs/waiting")
async def list_waiting_runs(db: AsyncSession = Depends(get_db)):
    """查询所有 HITL 暂停的工作流"""
    return db.query(WorkflowRun).filter(
        WorkflowRun.paused_node.isnot(None),
        WorkflowRun.deleted == 0,
    ).all()
```

### 图构建

```python
workflow = StateGraph(WorkflowState)

workflow.add_node("load_dag", load_dag)
workflow.add_node("validate", validate_dag)
workflow.add_node("get_ready", get_ready_nodes)
workflow.add_node("execute_single_node", execute_single_node)
workflow.add_node("update_pause", update_pause_state)
workflow.add_node("finalize", finalize)

workflow.add_edge(START, "load_dag")
workflow.add_edge("load_dag", "validate")
workflow.add_edge("validate", "get_ready")

workflow.add_conditional_edges(
    "get_ready",
    route_after_ready,
    {"assign_ready_nodes": "execute_single_node", "finalize": "finalize"},
)

# execute_single_node 完成后检查状态
workflow.add_conditional_edges(
    "execute_single_node",
    route_after_check,
    {"update_pause": "update_pause", "get_ready": "get_ready", "finalize": "finalize"},
)

workflow.add_edge("update_pause", END)
workflow.add_edge("finalize", END)

workflow_graph = workflow.compile()
```

### Checkpointer 选型

```python
# 项目使用 MySQL，需要自研 MySQL Checkpointer 或使用 Supabase Checkpointer 技能
# 推荐方案：基于 supabase-checkpointer 技能改造为 MySQL 版本

from langgraph.checkpoint.base import BaseCheckpointSaver

class MySQLCheckpointer(BaseCheckpointSaver):
    """基于 MySQL 的 Checkpointer，复用项目现有数据库"""
    
    def put(self, config, checkpoint, metadata, new_versions):
        thread_id = config["configurable"]["thread_id"]
        db.execute(
            """INSERT INTO langgraph_checkpoints (thread_id, checkpoint_ns, checkpoint_id, checkpoint, metadata)
               VALUES (:tid, :ns, :cp_id, :cp, :meta)
               ON DUPLICATE KEY UPDATE checkpoint = :cp, metadata = :meta""",
            {
                "tid": thread_id,
                "ns": checkpoint.get("ns", ""),
                "cp_id": checkpoint["id"],
                "cp": json.dumps(checkpoint),
                "meta": json.dumps(metadata),
            },
        )
    
    def get_tuple(self, config):
        thread_id = config["configurable"]["thread_id"]
        row = db.execute(
            "SELECT checkpoint, metadata FROM langgraph_checkpoints WHERE thread_id = :tid ORDER BY checkpoint_id DESC LIMIT 1",
            {"tid": thread_id},
        ).fetchone()
        if row:
            return json.loads(row.checkpoint), json.loads(row.metadata)
        return None
```

---

## 四、Celery 任务集成层

### 定位
将 LangGraph 图执行封装为 Celery 异步任务，使用 `graph.stream()` 实时推送进度。

### 流程图

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────────┐
│  API 请求    │────▶│ Celery Task │────▶│  graph.stream()      │
│ (FastAPI)    │     │ (异步队列)   │     │  (LangGraph 流式)    │
└─────────────┘     └──────┬──────┘     └──────────┬───────────┘
                           │                       │
                           │            ┌──────────▼───────────┐
                           │            │  逐节点流式输出       │
                           │            │  · on_node_start     │
                           │            │  · on_node_end       │
                           │            │  · WebSocket 实时推送 │
                           │            └──────────┬───────────┘
                           │                       │
                    ┌──────▼──────┐       ┌────────▼────────┐
                    │  失败重试    │◀──────│  异常捕获        │
                    │  (指数退避)  │       │  (3次重试上限)    │
                    └──────┬──────┘       └────────┬────────┘
                           │                       │
                    ┌──────▼───────────────────────▼──────┐
                    │         结果存储                      │
                    │  · MySQL workflow_runs               │
                    │  · MySQL workflow_step_runs          │
                    │  · MySQL subagent_runs               │
                    │  · MySQL rag_query_logs              │
                    │  · WebSocket 实时推送                 │
                    └─────────────────────────────────────┘
```

### Celery Task 定义

```python
from celery import shared_task
from langgraph.types import Command

@shared_task(
    bind=True,
    name="workflow.execute",
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=60,
    time_limit=300,                # 5分钟超时
    soft_time_limit=270,           # 软超时 4.5 分钟
    acks_late=True,
    reject_on_worker_lost=True,
)
def execute_workflow(self, workflow_id: str, run_id: str, trigger_type: str = "manual"):
    """执行 LangGraph 工作流，使用 graph.stream() 实时推送"""
    try:
        save_workflow_run(workflow_id, run_id, status=1)  # 运行中
        ws_broadcast("workflow_progress", {"run_id": run_id, "status": "running"})
        
        graph = build_workflow_graph(workflow_id)
        config = {"configurable": {"thread_id": run_id}}
        initial_state = {"workflow_id": workflow_id, "run_id": run_id}
        
        # 使用 graph.stream() 流式执行，逐节点获取输出
        for event in graph.stream(initial_state, config=config):
            for node_name, node_output in event.items():
                # 每个节点完成时实时推送
                ws_broadcast("workflow_progress", {
                    "run_id": run_id,
                    "node": node_name,
                    "status": "completed",
                    "output": truncate(str(node_output), 500),
                })
                
                # 检查是否有 HITL 暂停
                if isinstance(node_output, dict) and node_output.get("has_human_wait"):
                    save_workflow_run(workflow_id, run_id, status=1, paused_node=node_output["human_wait_node"])
                    ws_broadcast("workflow_progress", {
                        "run_id": run_id,
                        "status": "human_wait",
                        "node": node_output["human_wait_node"],
                    })
                    return {"status": "human_wait", "run_id": run_id}
        
        # 正常完成
        save_workflow_run(workflow_id, run_id, status=2)
        ws_broadcast("workflow_complete", {"run_id": run_id, "status": "completed"})
        return {"status": "completed", "run_id": run_id}
        
    except SoftTimeLimitExceeded:
        save_workflow_run(workflow_id, run_id, status=5)  # 超时
        ws_broadcast("workflow_complete", {"run_id": run_id, "status": "timeout"})
        raise
        
    except Exception as exc:
        save_workflow_run(workflow_id, run_id, status=3, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="subagent.execute",
    max_retries=2,
    time_limit=180,                # 3分钟超时
    soft_time_limit=150,
    acks_late=True,
)
def execute_subagent_task(self, definition_id: int, task_input: str, parent_run_id: str = None):
    """执行子代理任务，带超时和取消机制"""
    try:
        # 加载子代理定义
        agent_def = db.query(SubagentDefinition).get(definition_id)
        
        sub_run_id = save_subagent_definition_run(
            definition_id=definition_id,
            parent_run_id=parent_run_id,
            task_input=task_input,
            status=1,
        )
        
        # 构建 Agent 并执行
        tools = load_tools_for_agent(agent_def.tools or [])
        agent = create_react_agent(
            model=get_llm(agent_def.llm_model, float(agent_def.temperature or 0.7)),
            tools=tools,
            prompt=agent_def.system_prompt or "",
        )
        
        result = agent.invoke({"messages": [HumanMessage(content=task_input)]})
        output = result["messages"][-1].content
        
        save_subagent_definition_run(sub_run_id, status=2, output_json={"output": output})
        
        # 推送完成事件
        ws_broadcast("subagent_status", {
            "run_id": sub_run_id,
            "definition_id": definition_id,
            "status": "completed",
        })
        
        return {"status": "completed", "output": output}
        
    except SoftTimeLimitExceeded:
        save_subagent_definition_run(sub_run_id, status=5, error="执行超时")
        raise
    except Exception as exc:
        save_subagent_definition_run(sub_run_id, status=3, error=str(exc))
        raise self.retry(exc=exc)
```

---

## 五、模块间关系总图

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI 路由层                            │
│                                                                 │
│  /api/v1/workflows/*           /api/v1/subagent-definitions/*  │
│  /api/v1/workflow-runs/*       /api/v1/subagent-runs/*         │
│  /api/v1/workflow-templates/*  /api/v1/rag-query-logs/*        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Celery 任务层                               │
│                                                                 │
│  execute_workflow()          execute_subagent_task()            │
│  (graph.stream 流式执行)      (Agent 执行 + 超时取消)             │
└───────────┬─────────────────────────────┬───────────────────────┘
            │                             │
            ▼                             ▼
┌───────────────────────┐   ┌─────────────────────────────────────┐
│  工作流 DAG 引擎       │   │  子代理系统                          │
│  (模块三)              │   │  (模块二)                            │
│                       │   │                                     │
│  load_dag → validate  │   │  load_agents → orchestrator         │
│  → get_ready →        │   │  → worker(带依赖上下文)              │
│  Send(execute_node)   │   │  → synthesizer                      │
│  → check_status →     │   │                                     │
│  HITL/finalize        │   │  独立 subagent_runs 生命周期管理      │
│                       │   │  支持暂停/终止 API                   │
│  Checkpointer:        │   │                                     │
│  MySQLCheckpointer    │   │                                     │
└───────────┬───────────┘   └──────────────┬──────────────────────┘
            │                              │
            │    ┌─────────────────────────┘
            │    │
            ▼    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAG 多跳推理 (模块一)                        │
│                                                                 │
│  classify → decompose → retrieve → evaluate → dedup+synthesize  │
│  (Routing)   (拆解)      (Qdrant)   (够了吗?)   (去重+合成+日志)  │
│                                                                 │
│  记录到 rag_query_logs (conversation_id, 过程详情, 来源)          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      存储层                                      │
│                                                                 │
│  MySQL:                                                          │
│    workflows / workflow_runs(paused_node) / workflow_step_runs  │
│    workflow_templates                                           │
│    subagent_definitions / subagent_runs                         │
│    rag_query_logs                                               │
│                                                                 │
│  Qdrant: knowledge_chunks / memory_vectors / intent_vectors     │
│  Redis: 缓存 + WebSocket 消息队列                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、关键设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| State 管理 | TypedDict + Annotated 累加器 | TypedDict 更轻量，与 LangGraph 原生兼容 |
| 并行执行 | Send() API | LangGraph 原生支持，可靠且可追踪 |
| 人工确认 | interrupt() + Command(resume) | LangGraph HITL 标准模式 |
| HITL 状态查询 | workflow_runs.paused_node 字段 | 轻量方案，不需要额外中间表 |
| Checkpointer | MySQLCheckpointer（自研） | 项目统一用 MySQL，复用现有基础设施 |
| 进度推送 | graph.stream() | 比 Callback 更原生，直接获取节点级输出 |
| 任务队列 | Celery + graph.stream() | Celery 管理异步，graph.stream 获取实时进度 |
| 错误重试 | 指数退避 + 最大3次 | 与项目异常处理规范一致 |
| DAG 存储 | MySQL JSON 字段 | dag_json 整体读写，不拆分查询 |
| 子代理定义 | subagent_definitions 表 | Agent 配置持久化，支持前端管理 |
| 子代理运行 | 独立 subagent_runs 表 | 独立生命周期，支持暂停/终止/查询 |
| RAG 日志 | rag_query_logs 表 | 记录推理过程，支持质量分析和调优 |
| 路由函数 | 纯函数，只读 State | 路由函数不做副作用操作，修改 State 在节点函数中完成 |
| 检索去重 | synthesize 前按 doc_id+chunk_index | 避免不同子问题检索到同一 chunk 导致重复 |
| 子代理超时 | Celery time_limit + soft_time_limit | 防止子代理卡死占用 Worker |

---

> 💡 **下一步**：主人确认设计后，我可以逐模块生成完整的实现代码～
