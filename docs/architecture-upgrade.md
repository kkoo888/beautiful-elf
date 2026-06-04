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
| P1-6 | 记忆系统未集成到对话流 | 不存在 | Agent 无长期记忆 |

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
│   │ (RAG+记忆)   │  │ (工具注册表)  │  │ (三层记忆)   │            │
│   └──────────────┘  └──────────────┘  └──────────────┘            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   RAG 管道        │ │   工具注册表      │ │   三层记忆        │
│   (新增)          │ │   (新增)          │ │   (新增)          │
│                  │ │                  │ │                  │
│  文档解析         │ │  内置工具:        │ │  短期: Redis     │
│  分块+Embedding  │ │  - 网页搜索       │ │  中期: MySQL     │
│  Qdrant 存储     │ │  - 代码执行       │ │  长期: Qdrant    │
│  混合检索         │ │  - 文件操作       │ │                  │
│  重排序           │ │  - 数据库查询     │ │  自动提取+检索   │
│                  │ │  - API调用        │ │  定期摘要压缩    │
│  已有:            │ │                  │ │                  │
│  - Ollama.embed  │ │  已有:            │ │  已有:            │
│  - QdrantMapper  │ │  - Tool 模型      │ │  - MemoryEntry   │
│  - Knowledge模型 │ │  - ToolStats      │ │  - Redis客户端   │
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


class AgentState(TypedDict):
    """Agent 状态"""
    conversation_id: int
    messages: Annotated[list, operator.add]     # 对话历史（追加模式）
    context: str                                 # RAG 检索结果
    memory_context: str                          # 记忆检索结果
    tool_calls: list                             # 待执行的工具调用
    tools_used: list                             # 已使用的工具
    final_answer: Optional[str]                  # 最终回复
    iterations: int                              # 循环次数（防死循环）


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

    return {
        "context": "\n\n".join(context_parts),
        "memory_context": memory_context,
    }


async def llm_call_node(state: AgentState) -> dict:
    """LLM 调用：拼装上下文 + 对话历史 → 调用 LLM"""
    system_prompt = build_system_prompt(state["context"])

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(state["messages"])

    # 调用 LLM（支持 tool_calls）
    response = await llm_client.chat_with_tools(
        messages=messages,
        tools=tool_registry.get_tool_schemas(),
    )

    if response.tool_calls:
        return {
            "messages": [{"role": "assistant", "content": response.content, "tool_calls": response.tool_calls}],
            "tool_calls": response.tool_calls,
        }
    else:
        return {
            "messages": [{"role": "assistant", "content": response.content}],
            "final_answer": response.content,
            "tool_calls": [],
        }


async def tool_executor_node(state: AgentState) -> dict:
    """工具执行：解析 tool_call → 执行 → 返回结果"""
    results = []
    for tc in state["tool_calls"]:
        result = await tool_registry.execute(tc.name, tc.arguments)
        results.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": str(result),
        })

    return {
        "messages": results,
        "tools_used": state.get("tools_used", []) + [tc.name for tc in state["tool_calls"]],
        "tool_calls": [],
        "iterations": state.get("iterations", 0) + 1,
    }


async def memory_saver_node(state: AgentState) -> dict:
    """记忆保存：提取关键信息 → 存入记忆系统"""
    if state.get("final_answer"):
        await memory_manager.extract_and_save(
            conversation_id=state["conversation_id"],
            messages=state["messages"],
            answer=state["final_answer"],
        )
    return {}


# ── 条件路由 ──────────────────────────────────────────────

def should_use_tools(state: AgentState) -> str:
    """判断是否需要调用工具"""
    # 防死循环：最多 5 轮工具调用
    if state.get("iterations", 0) >= 5:
        return "finish"
    if state.get("tool_calls"):
        return "use_tools"
    return "finish"
```

**新增文件：** `backend/app/agent/__init__.py`

```python
from .engine import build_agent_graph
from .context_builder import ContextBuilder
from .tool_registry import ToolRegistry
from .memory_manager import MemoryManager
from .rag_pipeline import RAGPipeline

__all__ = ["build_agent_graph", "ContextBuilder", "ToolRegistry", "MemoryManager", "RAGPipeline"]
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

            # 3. 分块
            chunks = self._split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)

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

    @staticmethod
    def _split_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
        """
        智能分块：优先按段落分割，其次按句子，最后按字符
        """
        if not text.strip():
            return []

        chunks = []

        # 按段落分割
        paragraphs = text.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 单段落超过 chunk_size，按句子细分
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

        # 添加重叠
        if overlap > 0 and len(chunks) > 1:
            overlapped = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_tail = chunks[i - 1][-overlap:]
                overlapped.append(prev_tail + " " + chunks[i])
            chunks = overlapped

        return chunks

    # ── 检索 ──────────────────────────────────────────────

    async def search(self, query: str, limit: int = 5, score_threshold: float = 0.3) -> str:
        """
        语义检索：query → Embedding → Qdrant 搜索 → 拼装上下文
        """
        # 1. Query Embedding
        query_vector = await self.embedder.embeddings(query)

        # 2. Qdrant 向量搜索
        results = self.qdrant.search(
            collection=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )

        if not results:
            return ""

        # 3. 拼装上下文
        context_parts = []
        for i, r in enumerate(results, 1):
            content = r.payload.get("content", "")
            filename = r.payload.get("filename", "未知")
            score = r.score
            context_parts.append(f"[来源: {filename} | 相关度: {score:.2f}]\n{content}")

        return "\n\n---\n\n".join(context_parts)
```

---

### 4.3 P0-4: 文档解析器

已集成在 4.2 的 RAGPipeline 中。支持格式：TXT、Markdown、PDF、DOCX、CSV、JSON。

**需要新增的依赖：**

```txt
# backend/requirements.txt 新增
pymupdf>=1.24.0        # PDF 解析
python-docx>=1.1.0     # Word 解析
```

---

### 4.4 P0-5: Tool Calling 闭环

**新增文件：** `backend/app/agent/tool_registry.py`

```python
"""工具注册表 — 管理和执行 Agent 工具"""
import json
import importlib
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolSchema:
    """工具 Schema（OpenAI Function Calling 格式）"""
    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: dict


class ToolRegistry:
    """工具注册表 — 注册、查询、执行工具"""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, ToolSchema] = {}

    def register(self, name: str, func: Callable, description: str, parameters: dict):
        """注册一个工具"""
        self._tools[name] = func
        self._schemas[name] = ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
        )
        logger.info(f"工具已注册: {name}")

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

    async def execute(self, name: str, arguments: dict) -> Any:
        """执行工具"""
        if name not in self._tools:
            return {"error": f"工具 '{name}' 不存在"}

        try:
            func = self._tools[name]
            result = await func(**arguments) if asyncio.iscoroutinefunction(func) else func(**arguments)
            return result
        except Exception as e:
            logger.error(f"工具执行失败: {name}, error={e}")
            return {"error": str(e)}


# ── 内置工具 ──────────────────────────────────────────────

async def web_search(query: str, max_results: int = 5) -> dict:
    """网页搜索"""
    # 实现：调用 Brave Search / DuckDuckGo API
    ...

async def execute_code(language: str, code: str) -> dict:
    """代码执行（沙箱）"""
    # 实现：在沙箱中执行 Python/JS 代码
    ...

async def read_file(path: str) -> dict:
    """读取文件"""
    # 实现：读取工作空间文件
    ...

async def query_database(sql: str) -> dict:
    """数据库查询（只读）"""
    # 实现：执行 SELECT 查询
    ...


# 全局注册表
tool_registry = ToolRegistry()

# 注册内置工具
tool_registry.register(
    "web_search", web_search,
    description="搜索互联网获取实时信息",
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

### 4.5 P1-1: httpx 连接池复用

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

### 4.6 P1-2 & P1-3: 对话消息自动保存 + 事务安全

**修改文件：** `backend/app/api/v1/chat.py`

```python
@router.post("/conversations/{conversation_id}/chat")
async def chat(conversation_id: int, data: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. 先保存用户消息
    await _msg_service.create(db, MessageCreate(
        conversation_id=conversation_id,
        role="user",
        content=data.messages[-1].content,  # 最后一条是用户消息
    ))

    # 2. 调用 Agent 引擎
    agent_graph = build_agent_graph()
    result = await agent_graph.ainvoke({
        "conversation_id": conversation_id,
        "messages": [{"role": m.role, "content": m.content} for m in data.messages],
        "context": "",
        "memory_context": "",
        "tool_calls": [],
        "tools_used": [],
        "final_answer": None,
        "iterations": 0,
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

    return ApiResult(data=ChatResponse(content=result["final_answer"]))
```

---

### 4.7 P1-4: JWT 密钥强制校验

**修改文件：** `backend/app/core/security.py`

```python
from app.core.config import get_settings

settings = get_settings()

# 移除硬编码默认值，强制要求环境变量
JWT_SECRET_KEY = settings.JWT_SECRET_KEY  # 必须在 .env 中设置

if not JWT_SECRET_KEY or JWT_SECRET_KEY == "beautiful-elf-secret-change-me":
    raise RuntimeError(
        "JWT_SECRET_KEY 未设置或使用了默认值！"
        "请在 .env 文件中设置一个安全的随机密钥。"
        "生成命令: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
    )
```

---

### 4.8 P1-5: 对话上下文窗口管理

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

### 4.9 P1-6: 记忆系统集成

**新增文件：** `backend/app/agent/memory_manager.py`

```python
"""三层记忆管理器 — 短期(Redis) + 中期(MySQL) + 长期(Qdrant)"""
from typing import List, Optional
import json

from app.services.ollama_service import OllamaClient
from app.mappers.qdrant_mapper import QdrantMapper
from app.core.redis_client import get_redis
from app.repository.memory_repo import MemoryRepository
from app.core.logging import get_logger

logger = get_logger(__name__)

MEMORY_COLLECTION = "memory"


class MemoryManager:
    """三层记忆管理"""

    def __init__(self):
        self.embedder = OllamaClient()
        self.qdrant = QdrantMapper()
        self.memory_repo = MemoryRepository()

        # 确保 Qdrant 集合
        self.qdrant.ensure_collection(MEMORY_COLLECTION, vector_size=1024)

    # ── 短期记忆（Redis）────────────────────────────────

    async def get_short_term(self, conversation_id: int) -> List[dict]:
        """获取短期记忆（最近对话）"""
        redis = get_redis()
        key = f"memory:short:{conversation_id}"
        data = await redis.get(key)
        return json.loads(data) if data else []

    async def save_short_term(self, conversation_id: int, messages: List[dict], ttl: int = 3600):
        """保存短期记忆到 Redis（1小时过期）"""
        redis = get_redis()
        key = f"memory:short:{conversation_id}"
        await redis.set(key, json.dumps(messages, ensure_ascii=False), ex=ttl)

    # ── 长期记忆（Qdrant 语义检索）──────────────────────

    async def search(self, query: str, conversation_id: int = None, limit: int = 5) -> str:
        """语义检索相关记忆"""
        query_vector = await self.embedder.embeddings(query)

        filter_payload = {}
        if conversation_id:
            filter_payload["conversation_id"] = conversation_id

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.35,
            filter_payload=filter_payload if filter_payload else None,
        )

        if not results:
            return ""

        return "\n".join(
            f"- [{r.payload.get('tags', ['记忆'])[0]}] {r.payload.get('summary', '')}"
            for r in results
        )

    # ── 记忆提取与保存 ──────────────────────────────────

    async def extract_and_save(self, conversation_id: int, messages: List[dict], answer: str):
        """从对话中提取关键信息，存入长期记忆"""
        extract_prompt = f"""分析以下对话，提取值得长期记住的关键信息。

用户最后的消息: {messages[-1]['content'] if messages else ''}
助手回复: {answer}

以 JSON 格式输出：
{{"should_save": true/false, "summary": "摘要", "tags": ["标签"], "importance": 1-10}}

如果对话不值得记住，返回 {{"should_save": false}}"""

        result = await self.embedder.chat(
            messages=[{"role": "user", "content": extract_prompt}],
            max_tokens=200,
        )

        try:
            extracted = json.loads(result.get("content", "{}"))
            if not extracted.get("should_save"):
                return

            # 生成 Embedding 并存入 Qdrant
            summary = extracted["summary"]
            vector = await self.embedder.embeddings(summary)

            self.qdrant.upsert(
                collection=MEMORY_COLLECTION,
                point_id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "conversation_id": conversation_id,
                    "summary": summary,
                    "tags": extracted.get("tags", []),
                    "importance": extracted.get("importance", 5),
                },
            )

            # 同步保存到 MySQL
            await self.memory_repo.create_db_entry({
                "conversation_id": conversation_id,
                "summary": summary,
                "tags": extracted.get("tags", []),
                "importance": extracted.get("importance", 5),
            })

            logger.info(f"记忆已保存: {summary[:50]}...")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"记忆提取解析失败: {e}")
```

---

### 4.10 P2-1: WebSocket 接入 Agent 流

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
                "messages": [{"role": "user", "content": user_message}],
                "context": "", "memory_context": "",
                "tool_calls": [], "tools_used": [],
                "final_answer": None, "iterations": 0,
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

### 4.11 P2-2: Workflow 执行引擎

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

### 4.12 P2-4: API 限流中间件

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

## 五、文件清单

### 新增文件

```
backend/app/agent/
├── __init__.py              # 模块导出
├── engine.py                # Agent 引擎（LangGraph StateGraph）
├── context_builder.py       # 上下文构建（RAG + 记忆注入）
├── tool_registry.py         # 工具注册表 + 内置工具
├── memory_manager.py        # 三层记忆管理器
├── rag_pipeline.py          # RAG 完整管道
├── context_manager.py       # 对话上下文窗口管理
└── workflow_engine.py       # 工作流执行引擎
```

### 修改文件

```
backend/app/api/v1/chat.py           # 接入 Agent 引擎 + 自动保存消息
backend/app/api/v1/knowledge.py      # 实现 RAG 管道接口
backend/app/api/v1/websocket.py      # 接入 Agent 流式输出
backend/app/services/llm_chat_service.py  # httpx 连接池复用
backend/app/core/security.py         # JWT 密钥强制校验
backend/main.py                      # 限流中间件
backend/requirements.txt             # 新增依赖
```

### 新增依赖

```txt
# backend/requirements.txt 新增
pymupdf>=1.24.0            # PDF 解析
python-docx>=1.1.0         # Word 解析
slowapi>=0.1.9             # API 限流
```

---

## 六、执行计划

```
Phase 1 — 核心链路（P0，1-2 周）
├── Day 1-2:  RAG 管道（rag_pipeline.py + knowledge.py）
├── Day 3-4:  工具注册表（tool_registry.py）
├── Day 5-7:  Agent 引擎（engine.py + context_builder.py）
├── Day 8:    Tool Calling 闭环调试
└── Day 9-10: 集成测试 + 对话流打通

Phase 2 — 质量加固（P1，1 周）
├── Day 1:    httpx 连接池复用
├── Day 2:    消息自动保存 + 事务安全
├── Day 3:    JWT 密钥强制校验
├── Day 4:    上下文窗口管理
└── Day 5:    记忆系统集成

Phase 3 — 体验增强（P2，1 周）
├── Day 1-2:  WebSocket 接入 Agent 流
├── Day 3-4:  Workflow 执行引擎
└── Day 5:    API 限流 + 压测
```

---

## 七、验证标准

| 模块 | 验收标准 |
|------|----------|
| RAG 管道 | 上传 PDF → 分块 → 向量化 → 搜索返回相关段落 |
| Agent 引擎 | 发送问题 → 自动检索记忆+知识 → 调用工具 → 返回答案 |
| Tool Calling | 问"今天天气" → Agent 调用 web_search 工具 → 返回天气信息 |
| 记忆系统 | 对话后自动提取记忆 → 新对话中能检索到之前的关键信息 |
| 上下文管理 | 发送 50 条消息 → 自动压缩旧消息为摘要 → 不超出 context window |
| WebSocket | 建立连接 → 发送消息 → 实时收到 token 流 + 工具调用状态 |
| 限流 | 1 分钟内请求超过 100 次 → 返回 429 |

---

> 「我们只能看到前方很短的距离，但已经可以看到那里有很多事情需要做。」—— Alan Turing
