# Beautiful-Elf 架构升级方案

> 以图灵的精确思维审视现有系统，修补控制流缺失，将"传话筒"进化为真正的智能体。

---

## 一、现状诊断

### 1.1 系统状态判定

```
输入字母表: {用户消息, 文档上传, 工作流定义, 工具配置}
输出字母表: {LLM回复, 文档列表, 工作流结果}

状态集合:
  S0: 初始化          ✅ 完整（Docker Compose + FastAPI 启动）
  S1: 用户对话        ⚠️ 部分实现（纯转发LLM，无Agent能力）
  S2: 知识库          ❌ 模型已有，管道全空（4个TODO接口）
  S3: 工作流          ❌ 模型已有，执行器全空
  S4: 工具调用        ❌ 模型已有，调用链全空
  S5: 记忆系统        ❌ 模型已有，集成全空
```

**结论：骨架完整，神经系统缺失。** 数据结构层完备，控制流（Agent逻辑）和数据流（RAG管道）几乎全部是 TODO。

### 1.2 已有资产盘点（不需要重写的部分）

| 组件 | 状态 | 位置 | 备注 |
|------|------|------|------|
| FastAPI 框架 | ✅ 完整 | `backend/main.py` | 生命周期、CORS、异常处理、trace中间件 |
| SQLAlchemy ORM | ✅ 完整 | `backend/app/models/` | 20+ 个业务模型 |
| Alembic 迁移 | ✅ 完整 | `backend/alembic/` | 数据库版本管理 |
| MySQL | ✅ 运行中 | Docker Compose | 异步连接池已配置 |
| Redis | ✅ 运行中 | Docker Compose | 客户端已封装 |
| Qdrant | ✅ 运行中 | Docker Compose | QdrantMapper 已有完整CRUD |
| Celery | ✅ 已配置 | `backend/app/tasks/` | 异步任务框架 |
| JWT 认证 | ✅ 完整 | `backend/app/core/security.py` | PyJWT + bcrypt |
| WebSocket 管理器 | ✅ 完整 | `backend/app/core/websocket_manager.py` | 按channel分组、广播 |
| Ollama 客户端 | ✅ 完整 | `backend/app/services/ollama_service.py` | chat + stream + **embeddings** |
| LLM 多供应商 | ✅ 完整 | `backend/app/services/llm_chat_service.py` | OpenAI兼容 + Ollama |
| QdrantMapper | ✅ 完整 | `backend/app/mappers/qdrant_mapper.py` | ensure_collection + upsert + search |
| React + Electron | ✅ 完整 | `web/` | Ant Design + Zustand + ReactFlow |
| 知识库模型 | ✅ 完整 | `backend/app/models/knowledge.py` | KnowledgeDocument + KnowledgeChunk |
| 记忆模型 | ✅ 完整 | `backend/app/models/memory.py` | MemoryEntry + qdrant_point_id |
| 工具模型 | ✅ 完整 | `backend/app/models/tool.py` | Tool + ToolStats |
| 工作流模型 | ✅ 完整 | `backend/app/models/workflow.py` | Workflow + WorkflowRun + WorkflowStepRun |

**关键发现：Ollama 服务已有 `embeddings()` 方法，QdrantMapper 已有 `ensure_collection()` + `upsert()` + `search()`。基础设施全部就绪，缺的只是把它们串起来的管道。**

---

## 二、问题清单（按优先级排序）

### 🔴 P0 — 不修则系统无法工作

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P0-1 | Chat 是纯转发，无 Agent 循环 | `llm_chat_service.py` | 系统不是智能体，只是API代理 |
| P0-2 | 知识库 API 全是 TODO | `api/v1/knowledge.py` | RAG 不可用 |
| P0-3 | 没有 Embedding 管道 | 不存在 | 文本无法转为向量 |
| P0-4 | 没有文档解析器 | 不存在 | 上传文件无法处理 |
| P0-5 | Tool Calling 闭环缺失 | `llm_chat_service.py` | LLM 无法调用工具 |

### 🟡 P1 — 影响质量和可维护性

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P1-1 | LLMChatService 每次 new httpx.AsyncClient | `llm_chat_service.py` | 高并发下耗尽文件描述符 |
| P1-2 | 流式响应中消息保存不在事务内 | `chat.py` | 保存失败则消息丢失 |
| P1-3 | 用户消息未自动保存 | `chat.py` | LLM 看不到历史对话 |
| P1-4 | JWT 密钥硬编码默认值 | `security.py` | 部署时等于无认证 |
| P1-5 | 对话上下文无窗口管理 | `chat.py` | 长对话超出 context window |
| P1-6 | 记忆系统未集成到对话流 | 不存在 | Agent 无长期记忆，用户回来后无法唤醒上下文 |
| P1-7 | 只有向量检索，无混合检索+重排序 | 不存在 | 检索准确率低 |
| P1-8 | Agent 无 token 预算控制 | `engine.py` | 成本和延迟不可控 |
| P1-9 | 工具调用无风险分级和审批 | `tool_registry.py` | 高风险操作可能误执行 |
| P1-10 | 无降级策略 | 全局 | 任一服务不可用则整体崩溃 |

### 🟢 P2 — 提升体验

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| P2-1 | WebSocket 只是 echo | `websocket.py` | 无实时对话体验 |
| P2-2 | Workflow 无执行引擎 | 不存在 | 工作流不可用 |
| P2-3 | 多 Agent 编排缺失 | 不存在 | ExpertTeam 不可用 |
| P2-4 | API 无限流中间件 | `main.py` | 无防刷保护 |

---

## 三、修复方案总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                        接入层（已有，增强）                           │
│         REST API + WebSocket + Electron Desktop App                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API 编排层（已有，增强）                           │
│   FastAPI + 认证 + 限流 + 路由 + 会话管理 + SSE 流式响应            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│               ★ Agent 引擎层（新增 — 核心）                          │
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐    │
│   │              LangGraph StateGraph                         │    │
│   │                                                           │    │
│   │   [用户输入] → [上下文构建] → [LLM调用] → [工具判断]       │    │
│   │                      ↑                    ↓               │    │
│   │                      │            [工具执行] ──→ 回到LLM   │    │
│   │                      │                                     │    │
│   │                      └── [记忆保存] ← [最终输出]           │    │
│   └───────────────────────────────────────────────────────────┘    │
│                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│   │ Context      │  │ Tool         │  │ Memory       │            │
│   │ Builder      │  │ Executor     │  │ Manager      │            │
│   │ (RAG+记忆    │  │ (工具注册表  │  │ (两层记忆    │            │
│   │  +降级策略)  │  │  +风险审批)  │  │  +定时任务)  │            │
│   └──────────────┘  └──────────────┘  └──────────────┘            │
│                                                                     │
│   ┌──────────────┐  ┌──────────────┐                              │
│   │ Tracing      │  │ Eval         │                              │
│   │ (LangFuse)   │  │ Pipeline     │                              │
│   └──────────────┘  └──────────────┘                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   RAG 管道        │ │   工具注册表      │ │   两层记忆        │
│   (新增)          │ │   (新增)          │ │   (新增)          │
│                  │ │                  │ │                  │
│  文档解析         │ │  内置工具:        │ │  会话内: Redis   │
│  分块+Embedding  │ │  - 网页搜索       │ │  长期: Qdrant    │
│  Qdrant 存储     │ │  - 代码执行       │ │                  │
│  混合检索         │ │  - 文件操作       │ │  Qdrant 两个集合：│
│  重排序           │ │  - 数据库查询     │ │  - detail(每小时) │
│                  │ │                  │ │  - summary(30min) │
│  已有:            │ │  已有:            │ │                  │
│  - Ollama.embed  │ │  - Tool 模型      │ │  已有:            │
│  - QdrantMapper  │ │  - ToolStats      │ │  - MemoryEntry   │
│  - Knowledge模型 │ │                  │ │  - Redis客户端   │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 四、详细设计

### 4.1 P0-1: Agent 引擎（核心中的核心）

**目标：** 将 `LLMChatService` 从"传话筒"重构为 LangGraph 驱动的 Agent 引擎。

**新增文件：** `backend/app/agent/engine.py`

```python
"""Agent 引擎 — LangGraph StateGraph 驱动"""
from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator
import time

from app.core.logging import get_logger
from app.agent.tool_registry import tool_registry, RiskLevel
from app.agent.memory_manager import MemoryManager
from app.agent.rag_pipeline import RAGPipeline
from app.services.llm_chat_service import LLMChatService

logger = get_logger(__name__)

# 全局实例（由 app 启动时初始化）
memory_manager: MemoryManager = None
rag_pipeline: RAGPipeline = None
llm_client: LLMChatService = None


def init_agent_services(memory: MemoryManager, rag: RAGPipeline, llm: LLMChatService):
    """App 启动时调用，注入依赖"""
    global memory_manager, rag_pipeline, llm_client
    memory_manager = memory
    rag_pipeline = rag
    llm_client = llm


def build_system_prompt(context: str) -> str:
    """将检索到的上下文注入系统提示词"""
    base = "你是一个智能助手，能够使用工具回答用户问题。请基于提供的上下文信息回答。"
    if context:
        return f"{base}\n\n{context}"
    return base


class AgentState(TypedDict):
    """Agent 状态"""
    conversation_id: int
    user_id: int
    messages: Annotated[list, operator.add]     # 对话历史（追加模式）
    context: str                                 # RAG 检索结果
    memory_context: str                          # 记忆检索结果
    tool_calls: list                             # 待执行的工具调用
    tools_used: list                             # 已使用的工具
    final_answer: Optional[str]                  # 最终回复
    iterations: int                              # 循环次数（防死循环）
    token_budget: int                            # 总 token 预算
    tokens_used: int                             # 已消耗 token
    needs_approval: bool                         # 是否有工具等待用户审批
    pending_tool_call: Optional[dict]            # 等待审批的工具调用


def build_agent_graph() -> StateGraph:
    """构建 Agent 工作流图"""

    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("llm_call", llm_call_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("memory_saver", memory_saver_node)

    # 定义边
    graph.set_entry_point("context_builder")
    graph.add_edge("context_builder", "llm_call")
    graph.add_conditional_edges(
        "llm_call",
        should_use_tools,          # 判断是否需要调用工具
        {
            "use_tools": "tool_executor",  # 需要工具 → 执行
            "finish": "memory_saver",       # 不需要 → 保存记忆
        }
    )
    graph.add_edge("tool_executor", "llm_call")  # 工具结果回传LLM
    graph.add_edge("memory_saver", END)

    return graph.compile()


# ── 节点实现 ──────────────────────────────────────────────

async def context_builder_node(state: AgentState) -> dict:
    """上下文构建：检索记忆 + RAG"""
    t0 = time.time()

    # 1. 检索相关记忆
    memory_context = await memory_manager.search(
        query=state["messages"][-1]["content"],
        conversation_id=state["conversation_id"],
        limit=5,
    )

    # 2. RAG 知识库检索
    rag_context = await rag_pipeline.search(
        query=state["messages"][-1]["content"],
        limit=5,
    )

    # 3. 合并上下文
    context_parts = []
    if memory_context:
        context_parts.append(f"【相关记忆】\n{memory_context}")
    if rag_context:
        context_parts.append(f"【知识库参考】\n{rag_context}")

    elapsed = time.time() - t0
    logger.info(f"[context_builder] memory={'yes' if memory_context else 'no'} rag={'yes' if rag_context else 'no'} elapsed={elapsed:.2f}s")

    return {
        "context": "\n\n".join(context_parts),
        "memory_context": memory_context,
    }


async def llm_call_node(state: AgentState) -> dict:
    """LLM 调用：拼装上下文 + 对话历史 → 调用 LLM"""
    t0 = time.time()
    system_prompt = build_system_prompt(state["context"])

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(state["messages"])

    # 调用 LLM（支持 tool_calls）
    response = await llm_client.chat_with_tools(
        messages=messages,
        tools=tool_registry.get_tool_schemas(),
    )

    elapsed = time.time() - t0
    has_tools = bool(response.tool_calls)
    usage = getattr(response, "usage", {})
    prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
    completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
    total_tokens = prompt_tokens + completion_tokens
    logger.info(f"[llm_call] tool_calls={has_tools} elapsed={elapsed:.2f}s tokens={total_tokens} iterations={state.get('iterations', 0)}")

    if response.tool_calls:
        return {
            "messages": [{"role": "assistant", "content": response.content, "tool_calls": response.tool_calls}],
            "tool_calls": response.tool_calls,
            "tokens_used": state.get("tokens_used", 0) + total_tokens,
        }
    else:
        return {
            "messages": [{"role": "assistant", "content": response.content}],
            "final_answer": response.content,
            "tool_calls": [],
            "tokens_used": state.get("tokens_used", 0) + total_tokens,
        }


async def tool_executor_node(state: AgentState) -> dict:
    """工具执行：解析 tool_call → 风险检查 → 执行/请求审批（含错误恢复）"""
    results = []
    tools_succeeded = []
    needs_approval = False
    pending_tool = None

    for tc in state["tool_calls"]:
        risk = tool_registry.get_risk_level(tc.name)

        # 高风险工具 → 返回审批请求，不执行
        if risk == RiskLevel.HIGH:
            needs_approval = True
            pending_tool = {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
            results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps({
                    "needs_approval": True,
                    "tool": tc.name,
                    "arguments": tc.arguments,
                    "message": f"⚠️ {tc.name} 是高风险操作，需要你确认后才能执行。请回复「确认执行」或「取消」。",
                }),
            })
            continue

        try:
            result = await tool_registry.execute(tc.name, tc.arguments)
            results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })
            tools_succeeded.append(tc.name)
        except Exception as e:
            logger.warning(f"工具 {tc.name} 执行失败: {e}")
            results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps({"error": str(e), "tool": tc.name, "hint": "工具执行失败，请尝试其他工具或直接回答"}),
                "is_error": True,
            })

    return {
        "messages": results,
        "tools_used": state.get("tools_used", []) + tools_succeeded,
        "tool_calls": [],
        "iterations": state.get("iterations", 0) + 1,
        "needs_approval": needs_approval,
        "pending_tool_call": pending_tool,
    }


async def memory_saver_node(state: AgentState) -> dict:
    """记忆保存：更新会话缓存（定时任务负责存 Qdrant）"""
    if state.get("final_answer"):
        await memory_manager.update_session_cache(
            conversation_id=state["conversation_id"],
            messages=state["messages"] + [{"role": "assistant", "content": state["final_answer"]}],
        )
    return {}


# ── 条件路由 ──────────────────────────────────────────────

def should_use_tools(state: AgentState) -> str:
    """判断是否需要调用工具"""
    # 防死循环：最多 5 轮工具调用
    if state.get("iterations", 0) >= 5:
        logger.warning(f"[agent] 工具调用达到上限(5轮)，强制结束")
        return "finish"
    # Token 预算检查
    if state.get("tokens_used", 0) >= state.get("token_budget", 32000):
        logger.warning(f"[agent] token 预算耗尽 ({state.get('tokens_used', 0)}/{state.get('token_budget', 32000)})")
        return "finish"
    # 有待审批工具 → 先让用户确认
    if state.get("needs_approval"):
        return "finish"
    if state.get("tool_calls"):
        return "use_tools"
    return "finish"
```

**新增文件：** `backend/app/agent/__init__.py`

```python
from .engine import build_agent_graph, init_agent_services
from .context_builder import ContextBuilder
from .tool_registry import ToolRegistry
from .memory_manager import MemoryManager
from .rag_pipeline import RAGPipeline

__all__ = ["build_agent_graph", "init_agent_services", "ContextBuilder", "ToolRegistry", "MemoryManager", "RAGPipeline"]
```

**在 `backend/main.py` 的 lifespan 中初始化：**

```python
from app.agent import init_agent_services
from app.agent.memory_manager import MemoryManager
from app.agent.rag_pipeline import RAGPipeline
from app.services.llm_chat_service import LLMChatService

@asynccontextmanager
async def lifespan(app: FastAPI):
    memory = MemoryManager()
    rag = RAGPipeline()
    llm = LLMChatService()
    init_agent_services(memory, rag, llm)
    yield
    await llm.close()
```

---

### 4.2 P0-2 & P0-3: RAG 管道

**目标：** 实现文档上传 → 解析 → 分块 → Embedding → Qdrant 存储 → 检索的完整管道。

**新增文件：** `backend/app/agent/rag_pipeline.py`

```python
"""RAG 管道 — 文档解析 + 分块 + 向量化 + 检索"""
import uuid
import hashlib
from typing import List, Optional
from pathlib import Path

from app.services.ollama_service import OllamaClient
from app.mappers.qdrant_mapper import QdrantMapper
from app.repository.knowledge_repo import KnowledgeDocumentRepo, KnowledgeChunkRepo
from app.core.logging import get_logger

logger = get_logger(__name__)

# 常量
COLLECTION_NAME = "knowledge"
CHUNK_SIZE = 512          # 每个分块的目标字符数
CHUNK_OVERLAP = 64        # 分块重叠字符数
EMBEDDING_DIM = 1024      # 向量维度（根据模型调整）


class RAGPipeline:
    """RAG 完整管道"""

    def __init__(self):
        self.embedder = OllamaClient()
        self.qdrant = QdrantMapper()
        self.doc_repo = KnowledgeDocumentRepo()
        self.chunk_repo = KnowledgeChunkRepo()

        # 确保 Qdrant 集合存在
        self.qdrant.ensure_collection(COLLECTION_NAME, vector_size=EMBEDDING_DIM)

    # ── 文档处理管道 ──────────────────────────────────────

    async def process_document(self, db, file_path: str, filename: str, file_type: str) -> dict:
        """
        完整文档处理管道：
        上传 → 解析 → 分块 → Embedding → 存储
        """
        # 1. 创建文档记录
        doc = await self.doc_repo.create(db, {
            "filename": filename,
            "file_type": file_type,
            "file_size": Path(file_path).stat().st_size,
            "status": 1,  # 处理中
        })

        try:
            # 2. 解析文档 → 纯文本
            text = self._parse_document(file_path, file_type)

            # 3. 分块（按文档类型选择策略）
            chunks = self._split_text(text, file_type)

            # 4. 批量 Embedding + 存储
            for i, chunk_text in enumerate(chunks):
                # 生成 Embedding
                vector = await self.embedder.embeddings(chunk_text)

                # 生成确定性 point_id
                point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{doc.id}:{i}"))

                # 存入 Qdrant
                self.qdrant.upsert(
                    collection=COLLECTION_NAME,
                    point_id=point_id,
                    vector=vector,
                    payload={
                        "document_id": doc.id,
                        "chunk_index": i,
                        "content": chunk_text,
                        "filename": filename,
                    },
                )

                # 记录到 MySQL
                await self.chunk_repo.create(db, {
                    "document_id": doc.id,
                    "chunk_index": i,
                    "content_preview": chunk_text[:200],
                    "qdrant_point_id": point_id,
                })

            # 5. 更新文档状态
            await self.doc_repo.update(db, doc.id, {
                "chunk_count": len(chunks),
                "status": 2,  # 完成
            })

            return {"document_id": doc.id, "chunks": len(chunks)}

        except Exception as e:
            await self.doc_repo.update(db, doc.id, {
                "status": 3,  # 失败
                "error_message": str(e)[:1024],
            })
            raise

    # ── 文档解析 ──────────────────────────────────────────

    def _parse_document(self, file_path: str, file_type: str) -> str:
        """解析文档为纯文本"""
        parsers = {
            "txt": self._parse_text,
            "md": self._parse_text,
            "markdown": self._parse_text,
            "pdf": self._parse_pdf,
            "docx": self._parse_docx,
            "csv": self._parse_csv,
            "json": self._parse_json,
        }
        parser = parsers.get(file_type.lower(), self._parse_text)
        return parser(file_path)

    @staticmethod
    def _parse_text(path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _parse_pdf(path: str) -> str:
        """PDF 解析（需要 pip install pymupdf）"""
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        return "\n\n".join(text_parts)

    @staticmethod
    def _parse_docx(path: str) -> str:
        """Word 解析（需要 pip install python-docx）"""
        from docx import Document
        doc = Document(path)
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

    @staticmethod
    def _parse_csv(path: str) -> str:
        import csv
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            return "\n".join(",".join(row) for row in reader)

    @staticmethod
    def _parse_json(path: str) -> str:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), ensure_ascii=False, indent=2)

    # ── 文本分块 ──────────────────────────────────────────

    def _split_text(self, text: str, file_type: str = "txt") -> List[str]:
        """
        按文档类型选择分块策略：
        - 代码文件（py/js/ts/go）→ 按函数/类分块
        - Markdown → 按标题层级分块
        - 其他 → 按段落+字符数分块
        """
        if not text.strip():
            return []

        code_types = {"py", "js", "ts", "go", "java", "cpp", "c", "rs"}
        if file_type.lower() in code_types:
            return self._split_code(text, file_type)
        elif file_type.lower() in {"md", "markdown"}:
            return self._split_markdown(text)
        else:
            return self._split_plain(text)

    @staticmethod
    def _split_code(text: str, lang: str) -> List[str]:
        """代码分块：按函数/类定义切分，保留完整结构"""
        import re
        # 按函数/类定义切分（Python/JS/Go 通用模式）
        patterns = {
            "py": r'(?=^(?:class |def |async def )\w)',
            "js": r'(?=^(?:export )?(?:class |function |const \w+ = (?:async )?\())',
            "ts": r'(?=^(?:export )?(?:class |function |const \w+ = (?:async )?\())',
            "go": r'(?=^func )',
        }
        pattern = patterns.get(lang, patterns["py"])
        parts = re.split(pattern, text, flags=re.MULTILINE)
        chunks = []
        current = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(current) + len(part) > 1024:
                if current:
                    chunks.append(current.strip())
                current = part
            else:
                current += "\n\n" + part if current else part
        if current.strip():
            chunks.append(current.strip())
        return chunks if chunks else [text]

    @staticmethod
    def _split_markdown(text: str) -> List[str]:
        """Markdown 分块：按标题层级切分，保持章节完整性"""
        import re
        sections = re.split(r'(?=^#{1,3} )', text, flags=re.MULTILINE)
        chunks = []
        current = ""
        for section in sections:
            section = section.strip()
            if not section:
                continue
            if len(current) + len(section) > 1024:
                if current:
                    chunks.append(current.strip())
                current = section
            else:
                current += "\n\n" + section if current else section
        if current.strip():
            chunks.append(current.strip())
        return chunks if chunks else [text]

    @staticmethod
    def _split_plain(text: str) -> List[str]:
        """纯文本分块：按段落分割，保留重叠"""
        chunk_size = 512
        overlap = 64
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(para) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                sentences = para.replace("。", "。\n").replace(".", ".\n").split("\n")
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(current_chunk) + len(sent) > chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sent
                    else:
                        current_chunk += "\n" + sent if current_chunk else sent
            else:
                if len(current_chunk) + len(para) + 1 > chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        if overlap > 0 and len(chunks) > 1:
            overlapped = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_tail = chunks[i - 1][-overlap:]
                overlapped.append(prev_tail + " " + chunks[i])
            chunks = overlapped

        return chunks

    # ── 检索（混合检索 + 查询改写 + 重排序）──────────────

    async def search(self, query: str, limit: int = 5, score_threshold: float = 0.3) -> str:
        """
        完整检索链路：查询改写 → 混合检索（向量+BM25）→ RRF 合并 → 重排序 → Top K
        """
        # 1. 查询改写：将模糊查询转为具体检索词
        rewritten = await self._rewrite_query(query)

        # 2. 混合检索：向量 + BM25 并行
        import asyncio
        vector_task = self._vector_search(rewritten, limit=limit * 3)
        bm25_task = self._bm25_search(rewritten, limit=limit * 3)
        vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)

        # 3. RRF 合并
        merged = self._rrf_merge(vector_results, bm25_results, k=60)

        # 4. 重排序（Cross-Encoder）
        reranked = await self._rerank(query, merged, top_k=limit)

        if not reranked:
            return ""

        # 5. 拼装上下文
        context_parts = []
        for r in reranked:
            content = r.get("content", "")
            filename = r.get("filename", "未知")
            score = r.get("score", 0)
            context_parts.append(f"[来源: {filename} | 相关度: {score:.2f}]\n{content}")

        return "\n\n---\n\n".join(context_parts)

    async def _rewrite_query(self, query: str) -> str:
        """查询改写：将模糊/口语化查询转为精确检索词"""
        if len(query) < 10 or "那个" in query or "之前" in query:
            # 短查询或含指代词，需要改写
            try:
                result = await self.embedder.chat(
                    messages=[{"role": "user", "content": f"将以下用户问题改写为适合搜索的关键词短语，只输出改写后的查询，不要解释：\n{query}"}],
                    max_tokens=100,
                )
                rewritten = result.get("content", "").strip()
                return rewritten if rewritten else query
            except Exception:
                return query
        return query

    async def _vector_search(self, query: str, limit: int) -> List[dict]:
        """向量检索"""
        query_vector = await self.embedder.embeddings(query)
        results = self.qdrant.search(
            collection=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.2,
        )
        return [
            {"id": r.id, "content": r.payload.get("content", ""), "filename": r.payload.get("filename", ""), "vector_score": r.score}
            for r in results
        ]

    async def _bm25_search(self, query: str, limit: int) -> List[dict]:
        """BM25 关键词检索（使用 SQLite FTS5，无需外部依赖）"""
        try:
            from app.core.database import get_db_session
            async with get_db_session() as session:
                # 使用 MySQL 全文索引
                sql = """
                    SELECT kc.id, kc.content_preview, kc.document_id, kd.filename,
                           MATCH(kc.content_preview) AGAINST(:query IN NATURAL LANGUAGE MODE) AS score
                    FROM knowledge_chunks kc
                    JOIN knowledge_documents kd ON kc.document_id = kd.id
                    WHERE MATCH(kc.content_preview) AGAINST(:query IN NATURAL LANGUAGE MODE)
                    ORDER BY score DESC
                    LIMIT :limit
                """
                result = await session.execute(sql, {"query": query, "limit": limit})
                return [
                    {"id": row[0], "content": row[1], "filename": row[3], "bm25_score": float(row[4])}
                    for row in result.fetchall()
                ]
        except Exception as e:
            logger.warning(f"BM25 检索失败，降级为纯向量: {e}")
            return []

    @staticmethod
    def _rrf_merge(vector_results: List[dict], bm25_results: List[dict], k: int = 60) -> List[dict]:
        """Reciprocal Rank Fusion 合并两路检索结果"""
        scores = {}
        content_map = {}

        for rank, r in enumerate(vector_results):
            doc_id = r["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            content_map[doc_id] = r

        for rank, r in enumerate(bm25_results):
            doc_id = r["id"]
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
            if doc_id not in content_map:
                content_map[doc_id] = r

        sorted_ids = sorted(scores, key=scores.get, reverse=True)
        merged = []
        for doc_id in sorted_ids:
            item = content_map[doc_id].copy()
            item["rrf_score"] = scores[doc_id]
            merged.append(item)

        return merged

    async def _rerank(self, query: str, candidates: List[dict], top_k: int = 5) -> List[dict]:
        """Cross-Encoder 重排序"""
        if not candidates:
            return []
        try:
            from sentence_transformers import CrossEncoder
            reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
            pairs = [(query, c.get("content", "")[:512]) for c in candidates]
            scores = reranker.predict(pairs)
            for i, score in enumerate(scores):
                candidates[i]["score"] = float(score)
            candidates.sort(key=lambda x: x["score"], reverse=True)
            return candidates[:top_k]
        except ImportError:
            # 没有 sentence-transformers，降级为 RRF 分数排序
            logger.warning("Cross-Encoder 不可用，降级为 RRF 排序")
            for c in candidates:
                c["score"] = c.get("rrf_score", 0)
            return candidates[:top_k]
        except Exception as e:
            logger.warning(f"重排序失败: {e}")
            return candidates[:top_k]
```

---

### 4.3 P0-5: Tool Calling 闭环

**新增文件：** `backend/app/agent/context_builder.py`

```python
"""上下文构建器 — 组装 RAG 检索 + 记忆检索 + 对话历史"""
from typing import List, Dict, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContextBuilder:
    """
    将 RAG 检索结果、记忆检索结果、对话历史组装为 LLM 的完整上下文。
    被 engine.py 的 context_builder_node 调用。
    """

    def __init__(self, rag_pipeline, memory_manager):
        self.rag = rag_pipeline
        self.memory = memory_manager

    async def build(
        self,
        query: str,
        user_id: int,
        conversation_id: int,
        system_prompt: str = "",
    ) -> dict:
        """
        构建完整上下文：
        1. 检索相关记忆（压缩摘要优先）
        2. RAG 知识库检索
        3. 组装为 system prompt

        返回: {"context": str, "memory_context": str, "rag_context": str}
        """
        # 并行检索记忆和知识库
        import asyncio
        memory_task = self.memory.search(query=query, user_id=user_id, limit=5)
        rag_task = self.rag.search(query=query, limit=5)

        memory_context, rag_context = await asyncio.gather(
            memory_task, rag_task, return_exceptions=True
        )

        # 异常降级
        if isinstance(memory_context, Exception):
            logger.warning(f"记忆检索失败: {memory_context}")
            memory_context = ""
        if isinstance(rag_context, Exception):
            logger.warning(f"RAG 检索失败: {rag_context}")
            rag_context = ""

        # 组装上下文
        context_parts = []
        if system_prompt:
            context_parts.append(system_prompt)
        if memory_context:
            context_parts.append(f"【相关记忆】\n{memory_context}")
        if rag_context:
            context_parts.append(f"【知识库参考】\n{rag_context}")

        return {
            "context": "\n\n".join(context_parts),
            "memory_context": memory_context or "",
            "rag_context": rag_context or "",
        }
```

**新增文件：** `backend/app/agent/tool_registry.py`

```python
"""工具注册表 — 管理和执行 Agent 工具"""
import json
import importlib
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


class RiskLevel(str):
    """工具风险等级"""
    LOW = "low"          # 只读操作，可直接执行
    MEDIUM = "medium"    # 有副作用但可逆，记录日志
    HIGH = "high"        # 不可逆操作（写文件/执行代码/修改数据），需用户确认


@dataclass
class ToolSchema:
    """工具 Schema（OpenAI Function Calling 格式）"""
    name: str
    description: str
    parameters: dict  # JSON Schema
    risk_level: str = RiskLevel.LOW


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: dict


class ToolRegistry:
    """工具注册表 — 注册、查询、执行工具（含风险审批）"""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, ToolSchema] = {}

    def register(self, name: str, func: Callable, description: str, parameters: dict, risk_level: str = RiskLevel.LOW):
        """注册一个工具"""
        self._tools[name] = func
        self._schemas[name] = ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
            risk_level=risk_level,
        )
        logger.info(f"工具已注册: {name} (risk={risk_level})")

    def get_tool_schemas(self) -> List[dict]:
        """获取所有工具的 Schema（供 LLM 使用）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": s.name,
                    "description": s.description,
                    "parameters": s.parameters,
                }
            }
            for s in self._schemas.values()
        ]

    def get_risk_level(self, name: str) -> str:
        """查询工具风险等级"""
        schema = self._schemas.get(name)
        return schema.risk_level if schema else RiskLevel.LOW

    async def execute(self, name: str, arguments: dict, approved: bool = False) -> Any:
        """执行工具（高风险操作需审批）"""
        if name not in self._tools:
            return {"error": f"工具 '{name}' 不存在"}

        risk = self.get_risk_level(name)

        # 高风险操作未审批 → 返回审批请求而非执行
        if risk == RiskLevel.HIGH and not approved:
            return {
                "needs_approval": True,
                "tool": name,
                "arguments": arguments,
                "risk_level": risk,
                "message": f"⚠️ 工具 {name} 是高风险操作，需要用户确认后执行",
            }

        try:
            func = self._tools[name]
            result = await func(**arguments) if asyncio.iscoroutinefunction(func) else func(**arguments)
            logger.info(f"工具执行完成: {name} (risk={risk}, approved={approved})")
            return result
        except Exception as e:
            logger.error(f"工具执行失败: {name}, error={e}")
            return {"error": str(e)}


# ── 内置工具 ──────────────────────────────────────────────

async def web_search(query: str, max_results: int = 5) -> dict:
    """网页搜索 — 使用 DuckDuckGo（免费，无需 API Key）"""
    from duckduckgo_search import DDGS
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return {
                "results": [
                    {"title": r["title"], "url": r["href"], "snippet": r["body"]}
                    for r in results
                ]
            }
    except Exception as e:
        return {"error": f"搜索失败: {e}", "results": []}

async def execute_code(language: str, code: str) -> dict:
    """代码执行 — Docker 沙箱隔离，超时10秒"""
    import asyncio
    sandbox_images = {"python": "python:3.12-slim", "javascript": "node:20-slim"}
    image = sandbox_images.get(language)
    if not image:
        return {"error": f"不支持的语言: {language}，仅支持 python/javascript"}

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "--rm", "--network=none", "--memory=128m",
            "--cpus=0.5", image, "sh", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        return {
            "stdout": stdout.decode()[:5000],
            "stderr": stderr.decode()[:2000],
            "exit_code": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {"error": "执行超时（10秒限制）"}
    except Exception as e:
        return {"error": f"沙箱执行失败: {e}"}

async def read_file(path: str) -> dict:
    """读取工作空间文件（限制在 /workspace 内，防路径穿越）"""
    from pathlib import Path
    workspace = Path("/workspace").resolve()
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace)):
        return {"error": "路径穿越攻击已拦截"}
    if not target.exists():
        return {"error": f"文件不存在: {path}"}
    if target.stat().st_size > 1_000_000:
        return {"error": "文件过大（>1MB），请指定具体范围"}
    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
        return {"content": content[:50000], "path": str(path)}
    except Exception as e:
        return {"error": f"读取失败: {e}"}

async def query_database(sql: str) -> dict:
    """数据库查询（只读 SELECT，自动加 LIMIT 防爆）"""
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return {"error": "只允许 SELECT 查询"}
    if "LIMIT" not in sql_stripped:
        sql = sql.rstrip(";") + " LIMIT 100"
    try:
        from app.core.database import get_db_session
        async with get_db_session() as session:
            result = await session.execute(sql)
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return {"columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        return {"error": f"查询失败: {e}"}


# 全局注册表
tool_registry = ToolRegistry()

# 注册内置工具
tool_registry.register(
    "web_search", web_search,
    description="搜索互联网获取实时信息",
    risk_level=RiskLevel.LOW,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "max_results": {"type": "integer", "description": "返回结果数量", "default": 5},
        },
        "required": ["query"],
    },
)

tool_registry.register(
    "execute_code", execute_code,
    description="在沙箱中执行代码",
    risk_level=RiskLevel.HIGH,
    parameters={
        "type": "object",
        "properties": {
            "language": {"type": "string", "enum": ["python", "javascript"]},
            "code": {"type": "string", "description": "要执行的代码"},
        },
        "required": ["language", "code"],
    },
)

tool_registry.register(
    "read_file", read_file,
    description="读取工作空间中的文件内容",
    risk_level=RiskLevel.LOW,
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
        },
        "required": ["path"],
    },
)

tool_registry.register(
    "query_database", query_database,
    description="查询数据库（只读 SELECT）",
    risk_level=RiskLevel.MEDIUM,
    parameters={
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "SQL 查询语句"},
        },
        "required": ["sql"],
    },
)
```

---

### 4.4 P1-1: httpx 连接池复用

**修改文件：** `backend/app/services/llm_chat_service.py`

```python
# 在 LLMChatService 中使用共享连接池，而非每次 new

class LLMChatService:
    def __init__(self):
        self.provider_service = LLMProviderService()
        # 复用模块级共享连接池（同 ollama_service 的模式）
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
                limits=httpx.Limits(max_connections=30, max_keepalive_connections=15),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
```

---

### 4.5 P1-2 & P1-3: 对话消息自动保存 + 事务安全

**修改文件：** `backend/app/api/v1/chat.py`

```python
from app.core.security import JWT_SECRET_KEY  # 密钥已在 security.py 强制校验

@router.post("/conversations/{conversation_id}/chat")
async def chat(conversation_id: int, data: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. 先保存用户消息
    await _msg_service.create(db, MessageCreate(
        conversation_id=conversation_id,
        role="user",
        content=data.messages[-1].content,
    ))

    # 2. 调用 Agent 引擎
    agent_graph = build_agent_graph()
    result = await agent_graph.ainvoke({
        "conversation_id": conversation_id,
        "user_id": current_user.id,  # 从 JWT 中获取
        "messages": [{"role": m.role, "content": m.content} for m in data.messages],
        "context": "",
        "memory_context": "",
        "tool_calls": [],
        "tools_used": [],
        "final_answer": None,
        "iterations": 0,
        "token_budget": 32000,
        "tokens_used": 0,
        "needs_approval": False,
        "pending_tool_call": None,
    })

    # 3. 保存助手回复（在同一事务中）
    await _msg_service.create(db, MessageCreate(
        conversation_id=conversation_id,
        role="assistant",
        content=result["final_answer"],
    ))

    # 4. 保存工具调用记录（如有）
    for tool_name in result.get("tools_used", []):
        await _msg_service.create(db, MessageCreate(
            conversation_id=conversation_id,
            role="tool",
            content=f"[工具调用] {tool_name}",
        ))

    # 5. 更新会话缓存（供记忆系统使用）
    await memory_manager.update_session_cache(
        conversation_id=conversation_id,
        messages=[{"role": m.role, "content": m.content} for m in data.messages]
        + [{"role": "assistant", "content": result["final_answer"]}],
    )

    return ApiResult(data=ChatResponse(
        content=result["final_answer"],
        tools_used=result.get("tools_used", []),
        sources=result.get("sources", []),
        tokens_used=result.get("tokens_used", 0),
        needs_approval=result.get("needs_approval", False),
        pending_tool=result.get("pending_tool_call"),
    ))
```

**结构化输出模型：**

```python
class ChatResponse(BaseModel):
    """Agent 结构化响应"""
    content: str
    tools_used: List[str] = []
    sources: List[str] = []            # 引用了哪些知识库/记忆
    tokens_used: int = 0               # 本次消耗的 token 数
    needs_approval: bool = False       # 是否有工具等待审批
    pending_tool: Optional[dict] = None  # 等待审批的工具详情
```

### 4.6 P1-4: JWT 密钥强制校验

**修改文件：** `backend/app/core/security.py`

```python
from app.core.config import get_settings

settings = get_settings()

JWT_SECRET_KEY = settings.JWT_SECRET_KEY

if not JWT_SECRET_KEY or JWT_SECRET_KEY == "beautiful-elf-secret-change-me":
    raise RuntimeError(
        "JWT_SECRET_KEY 未设置或使用了默认值！"
        "请在 .env 文件中设置一个安全的随机密钥。"
        "生成命令: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
    )
```

---

### 4.7 P1-5: 对话上下文窗口管理

**新增文件：** `backend/app/agent/context_manager.py`

```python
"""对话上下文窗口管理 — 滑动窗口 + 摘要压缩"""
from typing import List, Dict

MAX_CONTEXT_MESSAGES = 20       # 最大保留消息数
MAX_CONTEXT_TOKENS = 4000       # 最大 token 预算
SUMMARY_THRESHOLD = 30          # 超过此数量时触发摘要压缩


class ContextManager:
    """管理对话上下文，防超出 LLM context window"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    async def trim_messages(
        self,
        messages: List[Dict],
        system_prompt: str = "",
    ) -> List[Dict]:
        """
        智能裁剪消息列表：
        1. 保留 system prompt
        2. 保留最近 N 条消息
        3. 对更早的消息生成摘要
        """
        if len(messages) <= MAX_CONTEXT_MESSAGES:
            return messages

        # 分离：需要摘要的旧消息 + 保留的新消息
        old_messages = messages[:-MAX_CONTEXT_MESSAGES]
        recent_messages = messages[-MAX_CONTEXT_MESSAGES:]

        # 对旧消息生成摘要
        summary = await self._summarize(old_messages)

        # 重组：system + summary + recent
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        result.append({
            "role": "system",
            "content": f"【历史对话摘要】\n{summary}",
        })
        result.extend(recent_messages)

        return result

    async def _summarize(self, messages: List[Dict]) -> str:
        """用 LLM 对旧消息生成摘要"""
        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )

        summary_prompt = f"""请将以下对话压缩为简洁的摘要，保留关键信息、用户偏好和重要决策：

{conversation_text}

要求：不超过200字，保留关键事实和用户意图。"""

        if self.llm_client:
            result = await self.llm_client.chat(
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=300,
            )
            return result.get("content", "")
        else:
            # 降级：简单截取最近的关键消息
            return f"（共 {len(messages)} 条历史消息已省略）"
```

---

### 4.8 P1-6: 记忆系统集成

**新增文件：** `backend/app/agent/memory_manager.py`

> 记忆策略：Redis 做会话缓存，Qdrant 做长期记忆（两个集合）。详细版每小时由 Celery 定时任务存一次，压缩版在会话 30 分钟无互动时由 LLM 生成摘要后存入。用户再次调起时，优先检索压缩摘要唤醒上下文，详细版可作为日志追溯。

**新增文件：** `backend/app/tasks/memory_tasks.py`（Celery 定时任务）

```python
"""记忆定时任务 — 每小时存详细日志 + 检测30分钟无互动的会话存压缩版"""
from celery import shared_task
from datetime import datetime, timedelta

@shared_task
def hourly_detail_save():
    """每小时：将活跃会话的对话存为详细日志"""
    # 查询过去1小时内有新消息的会话
    # 对每个会话调用 memory_manager.save_detail_log()

@shared_task
def check_idle_summaries():
    """每5分钟检查：会话30分钟无互动 → 存压缩摘要"""
    # 查询 Redis 中 last_active 超过30分钟的会话
    # 对每个会话调用 memory_manager.save_summary()
    # 然后清除 Redis 缓存（会话已归档）
```

```python
"""两层记忆管理器 — Redis 会话缓存 + Qdrant 长期记忆（详细版+压缩版）"""
from typing import List, Optional
from datetime import datetime, timedelta
import json
import uuid

from app.services.ollama_service import OllamaClient
from app.mappers.qdrant_mapper import QdrantMapper
from app.core.redis_client import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)

# 两个 Qdrant 集合：详细日志 + 压缩摘要
MEMORY_DETAIL_COLLECTION = "memory_detail"    # 每小时存的完整对话日志
MEMORY_SUMMARY_COLLECTION = "memory_summary"  # 30分钟无互动时存的压缩版


class MemoryManager:
    """
    两层记忆：
    1. Redis — 会话内缓存（当前对话的上下文，TTL 1小时）
    2. Qdrant memory_detail — 每小时定时存的详细对话日志（可查可追溯）
    3. Qdrant memory_summary — 30分钟无互动时存的压缩摘要（用户回来时快速唤醒）

    查询优先级：Redis 缓存 → Qdrant 压缩摘要 → Qdrant 详细日志
    """

    def __init__(self):
        self.embedder = OllamaClient()
        self.qdrant = QdrantMapper()

        self.qdrant.ensure_collection(MEMORY_DETAIL_COLLECTION, vector_size=1024)
        self.qdrant.ensure_collection(MEMORY_SUMMARY_COLLECTION, vector_size=1024)

    # ── Redis 会话缓存 ──────────────────────────────────

    async def get_session_cache(self, conversation_id: int) -> dict:
        """获取会话缓存（最近对话 + 上次活跃时间）"""
        redis = get_redis()
        key = f"memory:session:{conversation_id}"
        data = await redis.get(key)
        return json.loads(data) if data else {"messages": [], "last_active": None}

    async def update_session_cache(self, conversation_id: int, messages: list):
        """更新会话缓存"""
        redis = get_redis()
        key = f"memory:session:{conversation_id}"
        await redis.set(key, json.dumps({
            "messages": messages[-50:],  # 最多保留50条
            "last_active": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }, ensure_ascii=False), ex=3600)  # 1小时 TTL

    # ── 详细日志（每小时存一次）─────────────────────────

    async def save_detail_log(self, conversation_id: int, user_id: int, messages: list):
        """
        保存详细对话日志到 Qdrant memory_detail 集合。
        每小时由定时任务触发，或对话结束时触发。
        存的是完整对话记录，用于日后查日志、溯源。
        """
        if not messages:
            return

        # 拼装完整对话文本
        conversation_text = "\n".join(
            f"[{m.get('role', 'unknown')}] {m.get('content', '')}"
            for m in messages
        )

        # 生成 Embedding
        vector = await self.embedder.embeddings(conversation_text[:2000])  # 截取前2000字符做向量

        # 存入 Qdrant
        point_id = str(uuid.uuid4())
        self.qdrant.upsert(
            collection=MEMORY_DETAIL_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "messages": messages,  # 完整对话记录
                "message_count": len(messages),
                "saved_at": datetime.utcnow().isoformat(),
                "save_reason": "hourly_schedule",
            },
        )

        logger.info(f"详细日志已保存: conversation={conversation_id}, messages={len(messages)}")
        return point_id

    # ── 压缩摘要（30分钟无互动时存）─────────────────────

    async def save_summary(self, conversation_id: int, user_id: int, messages: list):
        """
        保存压缩摘要到 Qdrant memory_summary 集合。
        触发条件：会话30分钟无新消息。
        用 LLM 将对话压缩为关键信息摘要，供用户下次回来时快速唤醒上下文。
        """
        if not messages:
            return

        # 用 LLM 压缩对话
        conversation_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in messages
        )

        summary_prompt = f"""请将以下对话压缩为结构化摘要，保留以下信息：
1. 用户的核心需求和偏好
2. 讨论过的关键话题和结论
3. 未完成的待办事项
4. 用户的沟通风格偏好

对话内容：
{conversation_text[:3000]}

要求：200字以内，用中文，直接输出摘要不要前缀。"""

        try:
            result = await self.embedder.chat(
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=300,
            )
            summary = result.get("content", "")
        except Exception as e:
            logger.warning(f"LLM 摘要生成失败，降级为截取: {e}")
            summary = conversation_text[:500] + "..."

        # 生成 Embedding
        vector = await self.embedder.embeddings(summary)

        # 存入 Qdrant
        point_id = str(uuid.uuid4())
        self.qdrant.upsert(
            collection=MEMORY_SUMMARY_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "summary": summary,
                "message_count": len(messages),
                "saved_at": datetime.utcnow().isoformat(),
                "save_reason": "30min_idle",
            },
        )

        # 同步更新 Redis 缓存，标记有摘要可用
        redis = get_redis()
        await redis.set(
            f"memory:summary_available:{conversation_id}",
            point_id,
            ex=86400,  # 24小时
        )

        logger.info(f"压缩摘要已保存: conversation={conversation_id}, summary={summary[:50]}...")
        return point_id

    # ── 语义检索（用户再次调起时用）─────────────────────

    async def search(self, query: str, user_id: int, limit: int = 5) -> str:
        """
        语义检索相关记忆。
        优先搜压缩摘要（更精准），不够再搜详细日志。
        """
        query_vector = await self.embedder.embeddings(query)

        # 先搜压缩摘要
        summaries = self.qdrant.search(
            collection=MEMORY_SUMMARY_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.35,
            filter_payload={"user_id": user_id},
        )

        # 再搜详细日志
        details = self.qdrant.search(
            collection=MEMORY_DETAIL_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.4,  # 详细日志阈值更高，避免噪音
            filter_payload={"user_id": user_id},
        )

        # 合并结果，摘要优先
        parts = []
        for r in summaries:
            parts.append(f"[摘要 | {r.payload.get('saved_at', '')}] {r.payload.get('summary', '')}")
        for r in details:
            msg_count = r.payload.get("message_count", 0)
            parts.append(f"[详细日志 | {r.payload.get('saved_at', '')} | {msg_count}条消息] 可查询完整对话记录")

        return "\n".join(parts) if parts else ""
```

---

### 4.9 P2-1: WebSocket 接入 Agent 流

**修改文件：** `backend/app/api/v1/websocket.py`

```python
@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: int):
    """实时对话 WebSocket — 接入 Agent 引擎"""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            user_message = data.get("content", "")
            if not user_message:
                continue

            # 通知前端：开始处理
            await websocket.send_json({"type": "start"})

            # 调用 Agent 引擎（流式）
            agent_graph = build_agent_graph()

            # 使用 astream_events 流式输出中间过程
            async for event in agent_graph.astream_events({
                "conversation_id": conversation_id,
                "user_id": 0,  # TODO: 从 WebSocket 认证中获取
                "messages": [{"role": "user", "content": user_message}],
                "context": "", "memory_context": "",
                "tool_calls": [], "tools_used": [],
                "final_answer": None, "iterations": 0,
                "token_budget": 32000, "tokens_used": 0,
                "needs_approval": False, "pending_tool_call": None,
            }):
                if event["event"] == "on_chat_model_stream":
                    # 流式 token
                    token = event["data"]["chunk"].content
                    if token:
                        await websocket.send_json({"type": "token", "content": token})

                elif event["event"] == "on_tool_start":
                    # 工具开始执行
                    await websocket.send_json({
                        "type": "tool_start",
                        "tool": event["name"],
                    })

                elif event["event"] == "on_tool_end":
                    # 工具执行完成
                    await websocket.send_json({
                        "type": "tool_end",
                        "tool": event["name"],
                    })

            # 完成
            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info(f"Chat WebSocket 断开: conversation={conversation_id}")
```

---

### 4.10 P2-2: Workflow 执行引擎

**新增文件：** `backend/app/agent/workflow_engine.py`

```python
"""工作流执行引擎 — 解析 DAG → 拓扑排序 → 逐步执行"""
from typing import Dict, Any, List
from datetime import datetime
import asyncio

from app.repository.workflow_repo import WorkflowRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowEngine:
    """DAG 工作流执行引擎"""

    def __init__(self):
        self.repo = WorkflowRepository()
        self._node_handlers: Dict[str, callable] = {}

    def register_handler(self, node_type: str, handler: callable):
        """注册节点类型处理器"""
        self._node_handlers[node_type] = handler

    async def execute(self, db, workflow_id: int, input_data: dict = None) -> dict:
        """执行工作流"""
        # 1. 加载工作流定义
        workflow = await self.repo.find_by_id(db, workflow_id)
        dag = workflow.dag_json

        # 2. 创建运行记录
        run = await self.repo.create_run(db, {
            "workflow_id": workflow_id,
            "status": 1,  # 运行中
            "trigger_type": 0,
            "input_json": input_data,
            "started_at": datetime.utcnow(),
        })

        try:
            # 3. 拓扑排序
            execution_order = self._topological_sort(dag)

            # 4. 逐步执行
            context = input_data or {}
            for step_name in execution_order:
                step_def = dag["nodes"][step_name]
                step_type = step_def.get("type", "default")

                # 创建步骤记录
                step_run = await self.repo.create_step_run(db, {
                    "run_id": run.id,
                    "step_name": step_name,
                    "step_type": step_type,
                    "status": 1,
                    "input_json": context,
                    "started_at": datetime.utcnow(),
                })

                try:
                    handler = self._node_handlers.get(step_type)
                    if not handler:
                        raise ValueError(f"未注册的节点类型: {step_type}")

                    result = await handler(step_def, context)
                    context[step_name] = result

                    await self.repo.update_step_run(db, step_run.id, {
                        "status": 2,  # 完成
                        "output_json": result,
                        "finished_at": datetime.utcnow(),
                    })

                except Exception as e:
                    await self.repo.update_step_run(db, step_run.id, {
                        "status": 3,  # 失败
                        "error_message": str(e),
                        "finished_at": datetime.utcnow(),
                    })
                    raise

            # 5. 更新运行记录
            await self.repo.update_run(db, run.id, {
                "status": 2,  # 完成
                "output_json": context,
                "finished_at": datetime.utcnow(),
            })

            return context

        except Exception as e:
            await self.repo.update_run(db, run.id, {
                "status": 3,  # 失败
                "error_message": str(e),
                "finished_at": datetime.utcnow(),
            })
            raise

    def _topological_sort(self, dag: dict) -> List[str]:
        """DAG 拓扑排序"""
        nodes = dag.get("nodes", {})
        edges = dag.get("edges", [])

        in_degree = {name: 0 for name in nodes}
        adjacency = {name: [] for name in nodes}

        for edge in edges:
            src, dst = edge["from"], edge["to"]
            in_degree[dst] += 1
            adjacency[src].append(dst)

        queue = [name for name, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(nodes):
            raise ValueError("DAG 中存在循环依赖")

        return order
```

---

### 4.11 P2-4: API 限流中间件

**修改文件：** `backend/main.py`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "请求过于频繁，请稍后重试",
            "userTip": "请降低请求频率",
        },
    )
```

**新增依赖：** `slowapi>=0.1.9`

---

### 4.12 降级策略链

当外部服务不可用时，Agent 应自动降级而非崩溃。

```
完整模式: Agent + RAG + 工具 + 记忆
  ↓ RAG 不可用（Qdrant 宕机 / Embedding 服务超时）
降级模式 1: Agent + 工具 + 记忆（无知识库检索）
  ↓ 工具不可用（Docker 不可用 / 搜索 API 限流）
降级模式 2: Agent + 记忆（纯对话，无外部能力）
  ↓ LLM 不可用（Ollama 宕机 / API 超时）
降级模式 3: 返回缓存的高频回答 + 告知用户服务暂时不可用
```

**实现位置：** `context_builder.py` 的 `build()` 方法和 `engine.py` 的 `context_builder_node`

```python
async def context_builder_node(state: AgentState) -> dict:
    """上下文构建：检索记忆 + RAG（含降级）"""
    t0 = time.time()
    context_parts = []
    degraded = []

    # 尝试记忆检索
    try:
        memory_context = await asyncio.wait_for(
            memory_manager.search(query=state["messages"][-1]["content"], user_id=state["user_id"], limit=5),
            timeout=5.0,
        )
        if memory_context:
            context_parts.append(f"【相关记忆】\n{memory_context}")
    except Exception as e:
        degraded.append(f"记忆检索: {e}")
        memory_context = ""

    # 尝试 RAG 检索
    try:
        rag_context = await asyncio.wait_for(
            rag_pipeline.search(query=state["messages"][-1]["content"], limit=5),
            timeout=10.0,
        )
        if rag_context:
            context_parts.append(f"【知识库参考】\n{rag_context}")
    except Exception as e:
        degraded.append(f"RAG 检索: {e}")
        rag_context = ""

    elapsed = time.time() - t0
    if degraded:
        logger.warning(f"[context_builder] 降级: {', '.join(degraded)} elapsed={elapsed:.2f}s")
    else:
        logger.info(f"[context_builder] memory={'yes' if memory_context else 'no'} rag={'yes' if rag_context else 'no'} elapsed={elapsed:.2f}s")

    return {
        "context": "\n\n".join(context_parts),
        "memory_context": memory_context or "",
    }
```

### 4.13 可观测性：LangSmith / LangFuse 集成

在 Agent 引擎中接入 tracing，追踪完整的决策链路。

**新增文件：** `backend/app/agent/tracing.py`

```python
"""Agent 可观测性 — LangFuse 集成（开源，可自部署）"""
import os
from contextlib import contextmanager

# 环境变量配置
LANGFUSE_ENABLED = os.getenv("LANGFUSE_PUBLIC_KEY") is not None
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

_tracer = None

def init_tracing():
    """初始化 LangFuse tracing（仅在配置了密钥时启用）"""
    global _tracer
    if not LANGFUSE_ENABLED:
        logger.info("LangFuse 未配置，tracing 已禁用")
        return
    try:
        from langfuse import Langfuse
        _tracer = Langfuse()
        logger.info(f"LangFuse 已启用: {LANGFUSE_HOST}")
    except ImportError:
        logger.warning("langfuse 包未安装，tracing 已禁用")

@contextmanager
def trace_span(name: str, metadata: dict = None):
    """追踪一个 Agent 节点的执行"""
    if not _tracer:
        yield
        return
    with _tracer.span(name=name, metadata=metadata or {}) as span:
        try:
            yield span
        except Exception as e:
            span.set_status_error(str(e))
            raise

def trace_agent_run(conversation_id: int, query: str, result: dict):
    """记录一次完整的 Agent 运行"""
    if not _tracer:
        return
    _tracer.generation(
        name="agent_run",
        input=query,
        output=result.get("final_answer", ""),
        metadata={
            "conversation_id": conversation_id,
            "tools_used": result.get("tools_used", []),
            "tokens_used": result.get("tokens_used", 0),
            "iterations": result.get("iterations", 0),
        },
    )
```

**在 engine.py 各节点中使用：**

```python
async def llm_call_node(state: AgentState) -> dict:
    with trace_span("llm_call", {"iterations": state.get("iterations", 0)}):
        # ... 原有逻辑
```

### 4.14 评估流水线（Eval Pipeline）

每次改 prompt 或模型后，自动跑评估确认质量不退化。

**新增文件：** `backend/app/agent/eval_pipeline.py`

```python
"""评估流水线 — 自动评估 Agent 回答质量"""
from typing import List, Dict
from pydantic import BaseModel
import json

class EvalCase(BaseModel):
    """评估用例"""
    id: int
    question: str
    expected_keywords: List[str] = []     # 期望包含的关键词
    expected_answer: str = ""             # 参考答案（可选）
    forbidden_patterns: List[str] = []    # 不应出现的内容

class EvalResult(BaseModel):
    """评估结果"""
    case_id: int
    question: str
    actual_answer: str
    correctness: float      # 0-1，正确性
    relevance: float        # 0-1，相关性
    completeness: float     # 0-1，完整性
    has_forbidden: bool     # 是否包含禁止内容
    passed: bool


class EvalPipeline:
    """Agent 评估流水线"""

    def __init__(self, agent_graph, llm_client):
        self.agent = agent_graph
        self.llm = llm_client

    async def run_eval(self, cases: List[EvalCase]) -> List[EvalResult]:
        """跑一轮评估"""
        results = []
        for case in cases:
            # 1. 调用 Agent
            agent_result = await self.agent.ainvoke({
                "conversation_id": 0,  # 评估用虚拟会话
                "user_id": 0,
                "messages": [{"role": "user", "content": case.question}],
                "context": "", "memory_context": "",
                "tool_calls": [], "tools_used": [],
                "final_answer": None, "iterations": 0,
                "token_budget": 32000, "tokens_used": 0,
                "needs_approval": False, "pending_tool_call": None,
            })
            answer = agent_result.get("final_answer", "")

            # 2. LLM-as-judge 评分
            score = await self._judge(case, answer)

            # 3. 检查禁止内容
            has_forbidden = any(p in answer for p in case.forbidden_patterns)

            results.append(EvalResult(
                case_id=case.id,
                question=case.question,
                actual_answer=answer,
                correctness=score["correctness"],
                relevance=score["relevance"],
                completeness=score["completeness"],
                has_forbidden=has_forbidden,
                passed=score["correctness"] >= 0.7 and score["relevance"] >= 0.7 and not has_forbidden,
            ))
        return results

    async def _judge(self, case: EvalCase, answer: str) -> dict:
        """LLM-as-judge 评分"""
        prompt = f"""评估以下回答的质量。

问题: {case.question}
参考答案: {case.expected_answer or "无"}
期望关键词: {', '.join(case.expected_keywords) or "无"}
实际回答: {answer}

以 JSON 格式输出评分（0-1）：
{{"correctness": 0.0, "relevance": 0.0, "completeness": 0.0}}"""

        try:
            result = await self.llm.chat(messages=[{"role": "user", "content": prompt}], max_tokens=100)
            return json.loads(result.get("content", "{}"))
        except Exception:
            return {"correctness": 0.5, "relevance": 0.5, "completeness": 0.5}
```

**评估用例文件：** `backend/app/agent/eval_cases.json`

```json
[
  {
    "id": 1,
    "question": "怎么配置 JWT 密钥？",
    "expected_keywords": ["JWT_SECRET_KEY", ".env", "secrets.token_urlsafe"],
    "forbidden_patterns": ["beautiful-elf-secret-change-me"]
  },
  {
    "id": 2,
    "question": "帮我查一下数据库里有多少用户",
    "expected_keywords": ["SELECT", "COUNT", "users"],
    "forbidden_patterns": ["DELETE", "DROP", "TRUNCATE"]
  }
]
```

---

## 五、文件清单

### 新增文件

```
backend/app/agent/
├── __init__.py              # 模块导出
├── engine.py                # Agent 引擎（LangGraph StateGraph + token预算 + 审批流）
├── context_builder.py       # 上下文构建（RAG + 记忆注入 + 降级策略）
├── tool_registry.py         # 工具注册表 + 内置工具（含沙箱实现 + 风险分级）
├── memory_manager.py        # 两层记忆管理器（Redis + Qdrant detail/summary）
├── rag_pipeline.py          # RAG 完整管道（混合检索 + 查询改写 + 重排序）
├── context_manager.py       # 对话上下文窗口管理
├── workflow_engine.py       # 工作流执行引擎
├── tracing.py               # 可观测性（LangFuse 集成）
└── eval_pipeline.py         # 评估流水线（LLM-as-judge）
```

### 修改文件

```
backend/app/api/v1/chat.py           # 接入 Agent 引擎 + 自动保存消息 + 结构化输出
backend/app/api/v1/knowledge.py      # 实现 RAG 管道接口
backend/app/api/v1/websocket.py      # 接入 Agent 流式输出
backend/app/services/llm_chat_service.py  # httpx 连接池复用
backend/app/core/security.py         # JWT 密钥强制校验
backend/main.py                      # 限流中间件 + Agent 服务初始化（lifespan）
backend/requirements.txt             # 新增依赖
```

### 新增依赖

```txt
# backend/requirements.txt 新增
langgraph>=0.2.0           # Agent 引擎（状态图驱动）
pymupdf>=1.24.0            # PDF 解析
python-docx>=1.1.0         # Word 解析
duckduckgo-search>=6.0.0   # 网页搜索（免费，无需 API Key）
sentence-transformers>=3.0.0  # Cross-Encoder 重排序
slowapi>=0.1.9             # API 限流
langfuse>=2.0.0            # 可观测性 tracing（可选，可自部署）
```

---

## 六、执行计划

```
Phase 1 — 核心链路（P0，1-2 周）
├── Day 1-2:  RAG 管道（rag_pipeline.py + knowledge.py + 混合检索 + 重排序）
├── Day 3-4:  工具注册表（tool_registry.py + 风险分级 + 沙箱实现）
├── Day 5-7:  Agent 引擎（engine.py + context_builder.py + token预算 + 降级策略）
├── Day 8:    Tool Calling 闭环 + 审批流调试
└── Day 9-10: 集成测试 + 对话流打通

Phase 2 — 质量加固（P1，1 周）
├── Day 1:    httpx 连接池复用 + JWT 密钥强制校验
├── Day 2:    消息自动保存 + 事务安全 + 结构化输出
├── Day 3:    上下文窗口管理 + 查询改写
├── Day 4-5:  记忆系统集成（两层 Qdrant + Celery 定时任务）

Phase 3 — 生产化（P2，1 周）
├── Day 1:    WebSocket 接入 Agent 流
├── Day 2-3:  Workflow 执行引擎
├── Day 4:    API 限流 + LangFuse tracing 接入
└── Day 5:    评估流水线 + 压测
```

---

## 七、验证标准

| 模块 | 验收标准 |
|------|----------|
| RAG 管道 | 上传 PDF → 分块 → 向量化 → 混合检索(向量+BM25) → 重排序 → 搜索返回相关段落 |
| Agent 引擎 | 发送问题 → 自动检索记忆+知识 → 调用工具 → 返回答案；token预算耗尽时自动停止 |
| Tool Calling | 问"今天天气" → Agent 调用 web_search → 返回天气信息；execute_code 需用户确认才执行 |
| 工具审批 | LLM 请求 execute_code → 前端弹出确认框 → 用户确认后执行 |
| 记忆系统 | 对话1小时后 → Qdrant memory_detail 有详细日志；30分钟无互动 → Qdrant memory_summary 有压缩摘要；用户再次提问 → 能检索到之前的摘要并注入上下文 |
| 上下文管理 | 发送 50 条消息 → 自动压缩旧消息为摘要 → 不超出 context window |
| WebSocket | 建立连接 → 发送消息 → 实时收到 token 流 + 工具调用状态 |
| 限流 | 1 分钟内请求超过 100 次 → 返回 429 |
| 降级策略 | Qdrant 不可用 → Agent 仍能对话（无 RAG）；LLM 不可用 → 返回缓存回答 |
| 评估流水线 | 跑 10 个标准用例 → 正确性 ≥ 0.7、无禁止内容 → 全部通过 |

---

> 「我们只能看到前方很短的距离，但已经可以看到那里有很多事情需要做。」—— Alan Turing
