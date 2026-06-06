# Beautiful-Elf 架构升级方案

> 以 LlamaIndex + LangChain + LangGraph 生态为核心，构建完整的 Agent 系统。
> 本文档是 Agent 层的详细开发标准，代码实现以本文档为准。
>
> **文档关系**：
> - `architecture-upgrade.md`（本文档）— Agent 层详细功能执行方案，**开发标准**
> - `backend-architecture.md` — 项目初期后端分层架构设计，功能实现后需按实际回改
> - `dev-doc-no-code.md` — 项目初期功能概览，功能实现后需按实际回改
> - `database-architecture.md` — 数据库设计，功能实现后需按实际回改

---

## 技术栈

| 技术 | 用途 | 角色 |
|------|------|------|
| **LlamaIndex** | RAG 框架 | 文档解析 → 分块 → Embedding → 检索 → 重排序 |
| **LangGraph** | Agent 引擎 | 状态图驱动的 Agent 循环（LangChain 生态） |
| **LangChain** | LLM 抽象层 | 统一 LLM 调用 + Tool Calling + 多供应商切换 |
| **FastAPI** | Web 框架 | REST API + WebSocket + SSE |
| **Qdrant** | 向量数据库 | 所有向量数据的唯一存储 |
| **MySQL** | 关系数据库 | 仅存业务关系数据 |
| **Redis** | 缓存 + 消息 | 会话缓存 + Celery Broker + 语义缓存 |
| **Ollama** | 本地模型 | LLM 推理 + Embedding 生成 |
| **Celery** | 异步任务 | 文档处理 + 定时任务 |
| **LangFuse** | 可观测性 | Agent tracing |

### 本地模型

| 模型 | 用途 | 说明 |
|------|------|------|
| `dengcao/Qwen3-Embedding-0.6B:Q8_0` | Embedding | 0.6B 参数，轻量高效，Q8 量化，本地 Ollama 运行 |
| `qwen3.5:7b` | LLM 推理 | 对话 + 查询改写 + 摘要压缩 |

### 依赖清单

```txt
# 核心框架
llama-index>=0.12.0
llama-index-vector-stores-qdrant>=0.4.0
llama-index-embeddings-ollama>=0.5.0
llama-index-llms-ollama>=0.5.0
llama-index-postprocessor-rerank>=0.3.0
langgraph>=0.2.0
langchain>=0.3.0
langchain-ollama>=0.2.0
langchain-openai>=0.2.0          # OpenAI 兼容供应商（DeepSeek/Kimi 等）

# 存储
sqlalchemy[asyncio]>=2.0.0
alembic>=1.14.0
aioredis>=2.0.0
qdrant-client>=1.12.0

# 工具
duckduckgo-search>=6.0.0
pymupdf>=1.24.0
python-docx>=1.1.0

# 可观测 + 限流
langfuse>=2.0.0
slowapi>=0.1.9

# 工具参数校验
jsonschema>=4.23.0
```

---

## 一、现状诊断

### 1.1 系统状态

```
S0: 初始化          ✅ Docker Compose + FastAPI 启动正常
S1: 用户对话        ⚠️ 纯转发 LLM，无 Agent 能力
S2: 知识库          ❌ 模型已有，RAG 管道全空
S3: 工作流          ❌ 模型已有，执行器全空
S4: 工具调用        ❌ 模型已有，调用链全空
S5: 记忆系统        ❌ 模型已有，集成全空
S6: 意图识别        ❌ 模型已有，向量和路由全空
```

### 1.2 已有资产（不重写）

| 组件 | 状态 | 位置 |
|------|------|------|
| FastAPI 框架 | ✅ | `backend/main.py` |
| SQLAlchemy ORM + Alembic | ✅ | `backend/app/models/` |
| MySQL / Redis / Qdrant | ✅ 运行中 | Docker Compose |
| Celery 异步任务框架 | ✅ | `backend/app/tasks/` |
| JWT 认证 | ✅ | `backend/app/core/security.py` |
| WebSocket 管理器 | ✅ | `backend/app/core/websocket_manager.py` |
| Ollama 客户端 | ✅ chat + embeddings | `backend/app/services/ollama_service.py` |
| LLM 多供应商 | ✅ | `backend/app/services/llm_chat_service.py` |
| QdrantMapper | ✅ CRUD 完整 | `backend/app/mappers/qdrant_mapper.py` |
| React + Electron 前端 | ✅ | `web/` |

---

## 二、数据归属

```
┌─────────────────────────────────────────────────────────┐
│                    MySQL（关系数据）                       │
│                                                         │
│  用户 / 对话 / 消息 / 日程 / 剪贴板 / 代码片段            │
│  知识库文档元数据 / 工作流定义 / 技能配置 / 宠物属性       │
│  系统设置 / Prompt 版本 / 操作日志 / 意图定义             │
│                                                         │
│  ❌ 不存：任何向量、Embedding、语义索引                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    Qdrant（向量数据）                     │
│                                                         │
│  Collection: knowledge_chunks   ← 知识库文档分块向量     │
│  Collection: memory_vectors     ← 对话记忆向量           │
│  Collection: intent_vectors     ← 意图识别向量           │
│                                                         │
│  通过 point_id 关联 MySQL 记录                           │
│  MySQL 宕机 → 向量仍可检索（降级模式可用）                │
│  Qdrant 宕机 → MySQL 数据不受影响                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    Redis（缓存 + 消息）                   │
│                                                         │
│  会话上下文缓存（TTL 1h）                                │
│  Celery Broker                                          │
│  WebSocket 消息队列                                      │
│  语义缓存（热门问答，embedding 相似度 < 0.05 → 命中）     │
│                                                         │
│  ❌ 不存：持久化数据（丢了可以从 MySQL + Qdrant 重建）    │
└─────────────────────────────────────────────────────────┘
```

---

## 三、系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                       接入层                                  │
│            REST API + WebSocket + SSE + Electron Desktop      │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    API 编排层                                  │
│        FastAPI + 认证 + 限流 + 会话管理                       │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                   ★ 意图路由层（新增）                         │
│                                                              │
│  用户输入 → Embedding → Qdrant intent_vectors 相似度检索     │
│  → 命中意图 → 路由到对应模块/技能/工具                        │
│  → 未命中 → 进入 Agent 通用对话                              │
│                                                              │
│  意图定义存 MySQL intents 表，向量存 Qdrant intent_vectors   │
│  技能触发词、工具推荐、快捷回复均通过意图层路由               │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│               ★ Agent 引擎层（LangGraph）                     │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  LangGraph StateGraph                                │    │
│  │                                                      │    │
│  │  [用户输入] → [上下文构建] → [LLM 调用] → [工具判断]  │    │
│  │                 ↑                       ↓            │    │
│  │                 │               [工具执行] → 回到 LLM │    │
│  │                 └── [记忆保存] ← [最终输出]           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Context      │  │ Tool         │  │ Memory       │       │
│  │ Builder      │  │ Executor     │  │ Manager      │       │
│  │ (LlamaIndex  │  │ (风险分级     │  │ (Redis 缓存  │       │
│  │  RAG + 记忆) │  │  + 审批流)   │  │  + Qdrant)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Context      │  │ LangFuse     │  │ Eval         │       │
│  │ Manager      │  │ Tracing      │  │ Pipeline     │       │
│  │ (窗口裁剪)   │  │              │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────┬────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│  LlamaIndex RAG  │ │  工具注册表   │ │  两层记忆         │
│                  │ │              │ │                  │
│  SimpleDirectory │ │  web_search  │ │  Redis: 会话缓存 │
│  Reader → 分块   │ │  execute_code│ │  Qdrant:         │
│  → Ollama Embed  │ │  read_file   │ │   memory_vectors │
│  → Qdrant 存储   │ │  query_db    │ │                  │
│  → 混合检索      │ │              │ │  定时归档:        │
│  → Reranker      │ │  风险分级:    │ │   每小时 → 详细  │
│                  │ │  LOW/MED/HIGH│ │   30min空 → 摘要 │
└──────────────────┘ └──────────────┘ └──────────────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
              ┌─────────────────────────┐
              │   MySQL    │   Qdrant   │
              │  关系数据   │   向量数据  │
              │            │            │
              │   Redis    │  Ollama    │
              │  缓存+消息  │  本地模型   │
              └─────────────────────────┘
```

---

## 四、核心模块设计

### 4.1 LLM 服务抽象（多供应商支持）

**原则**：Agent 不直接 hardcode 任何 LLM，统一通过 `LLMFactory` 获取。复用并升级现有 `llm_chat_service.py`。

```python
"""LLM 服务工厂 — 统一多供应商接入，Agent 和 RAG 共用"""
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"           # OpenAI 兼容（DeepSeek/Kimi/硅基流动等）
    OPENROUTER = "openrouter"


class LLMConfig(BaseModel):
    """LLM 配置（从 MySQL settings 表读取）"""
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "qwen3.5:7b"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


class EmbeddingConfig(BaseModel):
    """Embedding 配置
    dengcao/Qwen3-Embedding-0.6B:Q8_0 输出维度 1024（支持自定义，此处用默认最大值）
    上下文长度 32k，支持 100+ 语言
    """
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "dengcao/Qwen3-Embedding-0.6B:Q8_0"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    dimensions: int = 1024


class LLMFactory:
    """
    LLM 工厂 — 根据配置创建 LangChain 兼容的 LLM 实例。
    Agent 引擎、RAG 查询改写、摘要压缩等全部通过此工厂获取 LLM。
    """

    @staticmethod
    def create_llm(config: LLMConfig):
        """创建 LLM 实例（LangChain 兼容，支持 Tool Calling）"""
        if config.provider == LLMProvider.OLLAMA:
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=config.model,
                base_url=config.base_url,
                temperature=config.temperature,
                num_predict=config.max_tokens,
            )
        elif config.provider in (LLMProvider.OPENAI, LLMProvider.OPENROUTER):
            from langchain_openai import ChatOpenAI
            base_url = config.base_url
            if config.provider == LLMProvider.OPENROUTER:
                base_url = "https://openrouter.ai/api/v1"
            return ChatOpenAI(
                model=config.model,
                base_url=base_url,
                api_key=config.api_key,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        else:
            raise ValueError(f"不支持的 LLM 供应商: {config.provider}")

    @staticmethod
    def create_embedding(config: EmbeddingConfig):
        """创建 Embedding 实例（LlamaIndex 兼容）"""
        if config.provider == LLMProvider.OLLAMA:
            from llama_index.embeddings.ollama import OllamaEmbedding
            return OllamaEmbedding(
                model_name=config.model,
                base_url=config.base_url,
            )
        elif config.provider in (LLMProvider.OPENAI, LLMProvider.OPENROUTER):
            from llama_index.embeddings.openai import OpenAIEmbedding
            return OpenAIEmbedding(
                model=config.model,
                api_key=config.api_key,
                base_url=config.base_url,
            )
        else:
            raise ValueError(f"不支持的 Embedding 供应商: {config.provider}")

    @staticmethod
    def create_llama_index_llm(config: LLMConfig):
        """创建 LlamaIndex LLM 实例（用于 RAG 查询改写等）"""
        if config.provider == LLMProvider.OLLAMA:
            from llama_index.llms.ollama import Ollama as OllamaLLM
            return OllamaLLM(
                model=config.model,
                base_url=config.base_url,
            )
        elif config.provider in (LLMProvider.OPENAI, LLMProvider.OPENROUTER):
            from llama_index.llms.openai import OpenAI
            return OpenAI(
                model=config.model,
                api_key=config.api_key,
                base_url=config.base_url,
            )
        else:
            raise ValueError(f"不支持的 LLM 供应商: {config.provider}")


# ── 默认配置（启动时从 MySQL settings 表加载，支持热更新）──

_default_llm_config = LLMConfig()
_default_embedding_config = EmbeddingConfig()


def get_llm_config() -> LLMConfig:
    """获取当前 LLM 配置（优先读 MySQL settings，fallback 默认值）"""
    # TODO: 从 MySQL settings 表读取，支持运行时热更新
    return _default_llm_config.model_copy()


def get_embedding_config() -> EmbeddingConfig:
    """获取当前 Embedding 配置"""
    # TODO: 从 MySQL settings 表读取
    return _default_embedding_config.model_copy()


def get_llm():
    """快捷方法：获取当前配置的 LangChain LLM"""
    return LLMFactory.create_llm(get_llm_config())


def get_llama_index_llm():
    """快捷方法：获取当前配置的 LlamaIndex LLM"""
    return LLMFactory.create_llama_index_llm(get_llm_config())


def get_embedding():
    """快捷方法：获取当前配置的 Embedding 模型"""
    return LLMFactory.create_embedding(get_embedding_config())
```

### 4.2 意图路由层

**原则**：意图识别是用户消息进入系统的第一道门，用向量相似度快速匹配，不走 LLM 推理，延迟低。

```python
"""意图路由层 — 向量相似度快速匹配意图，命中则路由，未命中进 Agent"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.core.logging import get_logger
from app.mappers.qdrant_mapper import QdrantMapper

logger = get_logger(__name__)

INTENT_COLLECTION = "intent_vectors"
INTENT_SCORE_THRESHOLD = 0.75  # 意图相似度阈值（余弦相似度），高于此值认为命中意图
# 注意：语义缓存阈值见 _check_semantic_cache 中的 score_threshold=0.95
# 两者含义不同：意图匹配 0.75 是"大致相关"，语义缓存 0.95 是"几乎相同的问题"


class IntentMatch(BaseModel):
    """意图匹配结果"""
    intent_id: int
    intent_name: str
    score: float
    target_type: str        # "skill" | "tool" | "module" | "faq"
    target_config: dict     # 路由目标配置
    trigger_words: List[str] = []


class IntentRouter:
    """
    意图路由：
    1. 用户消息 Embedding → Qdrant intent_vectors 检索
    2. 相似度 >= 阈值 → 命中意图 → 路由到对应目标
    3. 未命中 → 进入 Agent 通用对话

    意图定义存 MySQL intents 表，向量存 Qdrant intent_vectors。
    技能触发词、工具推荐、快捷回复均通过意图层路由。
    """

    def __init__(self, qdrant_mapper: QdrantMapper, embedding_func):
        self.qdrant = qdrant_mapper
        self.embedding_func = embedding_func
        self.qdrant.ensure_collection(INTENT_COLLECTION, vector_size=1024)

    async def route(self, user_message: str, user_id: int = 0) -> Optional[IntentMatch]:
        """
        意图路由：
        1. 语义缓存检查（热门问答，直接返回缓存回答）
        2. 意图向量检索
        3. 命中 → 返回 IntentMatch
        4. 未命中 → 返回 None（进入 Agent）
        """
        # 1. 语义缓存检查
        cached = await self._check_semantic_cache(user_message)
        if cached:
            return IntentMatch(
                intent_id=-1,
                intent_name="semantic_cache_hit",
                score=cached["score"],
                target_type="cache",
                target_config={"answer": cached["answer"]},
            )

        # 2. 意图向量检索
        vector = await self.embedding_func(user_message)
        results = self.qdrant.search(
            collection=INTENT_COLLECTION,
            query_vector=vector,
            limit=1,
            score_threshold=INTENT_SCORE_THRESHOLD,
        )

        if not results:
            return None

        top = results[0]
        payload = top.payload

        return IntentMatch(
            intent_id=payload.get("intent_id", 0),
            intent_name=payload.get("intent_name", "unknown"),
            score=top.score,
            target_type=payload.get("target_type", "agent"),
            target_config=payload.get("target_config", {}),
            trigger_words=payload.get("trigger_words", []),
        )

    async def _check_semantic_cache(self, query: str) -> Optional[dict]:
        """语义缓存：热门问答 embedding 相似度 < 0.05 → 命中"""
        try:
            import redis.asyncio as aioredis
            from app.core.redis_client import get_redis

            redis = get_redis()
            vector = await self.embedding_func(query)

            # 从 Redis 检索热门缓存（存储最近 1000 条问答的 embedding）
            # 简化实现：直接查 Qdrant 的一个 cache 集合
            results = self.qdrant.search(
                collection="semantic_cache",
                query_vector=vector,
                limit=1,
                score_threshold=0.95,  # 余弦相似度 >= 0.95 才命中（等价于距离 < 0.05）
            )

            if results and results[0].score >= 0.95:
                return {
                    "answer": results[0].payload.get("answer", ""),
                    "score": results[0].score,
                }
        except Exception as e:
            logger.debug(f"语义缓存检查失败（非致命）: {e}")

        return None

    async def sync_intents_from_db(self, db):
        """从 MySQL intents 表同步意图向量到 Qdrant（技能/意图变更时调用）"""
        from app.repository.intent_repo import IntentRepository
        repo = IntentRepository(db)
        intents = await repo.get_all_active()

        for intent in intents:
            # 为每个意图的触发词生成向量
            trigger_text = " ".join(intent.trigger_words)
            vector = await self.embedding_func(trigger_text)

            self.qdrant.upsert(
                collection=INTENT_COLLECTION,
                point_id=f"intent_{intent.id}",
                vector=vector,
                payload={
                    "intent_id": intent.id,
                    "intent_name": intent.name,
                    "target_type": intent.target_type,
                    "target_config": intent.target_config or {},
                    "trigger_words": intent.trigger_words,
                },
            )

        logger.info(f"意图向量同步完成: {len(intents)} 个意图")
```

### 4.3 RAG 管道（LlamaIndex）

```python
"""RAG 管道 — LlamaIndex 驱动，Qdrant 存储"""
from pathlib import Path
from typing import List, Optional

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import QueryBundle
import qdrant_client

from app.core.logging import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "knowledge_chunks"


class RAGPipeline:
    """LlamaIndex 驱动的 RAG 管道"""

    def __init__(self, qdrant_url: str, embedding_model, llm_model=None):
        """
        Args:
            qdrant_url: Qdrant 连接地址
            embedding_model: LlamaIndex 兼容的 Embedding 实例
            llm_model: LlamaIndex 兼容的 LLM 实例（用于查询改写，可选）
        """
        self.qdrant_client = qdrant_client.QdrantClient(url=qdrant_url)
        self.embed_model = embedding_model
        self.llm = llm_model  # 查询改写用

        # 向量存储
        self.vector_store = QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=COLLECTION_NAME,
        )

        # 索引（从已有 Qdrant 数据加载）
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.embed_model,
        )

        # 分块器
        self.node_parser = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=64,
        )

        # 检索器
        self.retriever = self.index.as_retriever(similarity_top_k=10)

        # 重排序器（延迟初始化）
        self._reranker = None

    def init_reranker(self):
        """启动时调用一次，加载重排序模型"""
        try:
            from llama_index.core.postprocessor import SentenceTransformerRerank
            self._reranker = SentenceTransformerRerank(
                model="BAAI/bge-reranker-v2-m3",
                top_n=5,
            )
            logger.info("重排序模型加载成功")
        except Exception as e:
            logger.warning(f"重排序模型加载失败，降级为不重排: {e}")
            self._reranker = None

    # ── 文档入库（Celery 任务调用）────────────────────────

    async def ingest_document(self, file_path: str, filename: str, doc_id: int) -> dict:
        """文档入库：SimpleDirectoryReader → 分块 → Embedding → Qdrant"""
        from llama_index.core import SimpleDirectoryReader

        # 1. 加载文档
        reader = SimpleDirectoryReader(input_files=[file_path])
        documents = reader.load_data()

        # 2. 附加元数据
        for doc in documents:
            doc.metadata.update({
                "document_id": doc_id,
                "filename": filename,
                "file_type": Path(file_path).suffix.lstrip("."),
            })

        # 3. 分块
        nodes = self.node_parser.get_nodes_from_documents(documents)

        # 4. 存入 Qdrant（LlamaIndex 内部处理 Embedding）
        self.index.insert_nodes(nodes)

        logger.info(f"文档入库完成: {filename}, {len(nodes)} 个分块")
        return {"document_id": doc_id, "chunks": len(nodes)}

    # ── 检索 ─────────────────────────────────────────────

    async def search(self, query: str, limit: int = 5) -> str:
        """检索链路：查询改写 → 向量检索 → 重排序 → 拼装上下文"""
        import asyncio

        # 1. 查询改写
        rewritten = await self._rewrite_query(query)

        # 2. 向量检索（LlamaIndex retrieve 是同步的，用线程包装避免阻塞）
        nodes = await asyncio.to_thread(self.retriever.retrieve, rewritten)

        # 3. 重排序
        if self._reranker:
            query_bundle = QueryBundle(query_str=rewritten)
            nodes = self._reranker.postprocess_nodes(nodes, query_bundle=query_bundle)

        # 4. Top K
        nodes = nodes[:limit]

        if not nodes:
            return ""

        # 5. 拼装上下文
        context_parts = []
        for node in nodes:
            score = node.score or 0
            filename = node.metadata.get("filename", "未知")
            context_parts.append(f"[来源: {filename} | 相关度: {score:.2f}]\n{node.text}")

        return "\n\n---\n\n".join(context_parts)

    async def _rewrite_query(self, query: str) -> str:
        """查询改写：短查询或含指代词时用 LLM 改写"""
        if len(query) >= 10 and "那个" not in query and "之前" not in query:
            return query

        if not self.llm:
            return query

        try:
            import asyncio
            response = await asyncio.to_thread(
                self.llm.complete,
                f"将以下用户问题改写为适合搜索的关键词短语，只输出改写结果：\n{query}"
            )
            return str(response).strip() or query
        except Exception:
            return query
```

### 4.4 Agent 引擎（LangGraph）

```python
"""Agent 引擎 — LangGraph StateGraph 驱动"""
from typing import TypedDict, Annotated, Optional, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import operator
import time

from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    conversation_id: int
    user_id: int
    messages: Annotated[list, operator.add]
    context: str
    tool_calls: list
    tools_used: list
    final_answer: Optional[str]
    iterations: int
    token_budget: int
    tokens_used: int
    needs_approval: bool
    pending_tool_call: Optional[dict]


def build_agent_graph(rag_pipeline, memory_manager, tool_registry, llm, context_manager) -> StateGraph:
    """构建 Agent 工作流图（全部依赖注入）"""

    # 绑定工具到 LLM
    llm_with_tools = llm.bind_tools(tool_registry.get_langchain_tools())

    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("context_builder", _make_context_builder(rag_pipeline, memory_manager))
    graph.add_node("llm_call", _make_llm_caller(llm_with_tools, context_manager))
    graph.add_node("tool_executor", _make_tool_executor(tool_registry))
    graph.add_node("memory_saver", _make_memory_saver(memory_manager))

    # 定义边
    graph.set_entry_point("context_builder")
    graph.add_edge("context_builder", "llm_call")
    graph.add_conditional_edges("llm_call", _should_use_tools, {
        "use_tools": "tool_executor",
        "finish": "memory_saver",
    })
    graph.add_edge("tool_executor", "llm_call")
    graph.add_edge("memory_saver", END)

    return graph.compile()


# ── 节点工厂 ──────────────────────────────────────────────

def _make_context_builder(rag_pipeline, memory_manager):
    """上下文构建：RAG + 记忆检索，含降级"""

    async def context_builder_node(state: AgentState) -> dict:
        import asyncio
        t0 = time.time()
        context_parts = []
        degraded = []

        query = state["messages"][-1].content if state["messages"] else ""

        # 并行检索记忆 + 知识库
        try:
            memory_task = memory_manager.search(query=query, user_id=state["user_id"], limit=5)
            rag_task = rag_pipeline.search(query=query, limit=5)
            memory_context, rag_context = await asyncio.gather(
                memory_task, rag_task, return_exceptions=True
            )

            if isinstance(memory_context, Exception):
                degraded.append(f"记忆检索: {memory_context}")
                memory_context = ""
            if isinstance(rag_context, Exception):
                degraded.append(f"RAG 检索: {rag_context}")
                rag_context = ""

            if memory_context:
                context_parts.append(f"【相关记忆】\n{memory_context}")
            if rag_context:
                context_parts.append(f"【知识库参考】\n{rag_context}")

        except Exception as e:
            degraded.append(f"上下文构建: {e}")

        elapsed = time.time() - t0
        if degraded:
            logger.warning(f"[context_builder] 降级: {', '.join(degraded)} elapsed={elapsed:.2f}s")
        else:
            logger.info(f"[context_builder] elapsed={elapsed:.2f}s")

        return {"context": "\n\n".join(context_parts)}

    return context_builder_node


def _make_llm_caller(llm_with_tools, context_manager):
    """LLM 调用：上下文裁剪 + 调用 LLM"""

    async def llm_call_node(state: AgentState) -> dict:
        t0 = time.time()

        # 拼装系统提示
        system_prompt = "你是一个智能助手，能够使用工具回答用户问题。"
        if state.get("context"):
            system_prompt += f"\n\n{state['context']}"

        # 裁剪消息（防超出 context window）
        raw_messages = []
        for m in state["messages"]:
            if hasattr(m, "role"):
                raw_messages.append({"role": m.role, "content": m.content})
            elif isinstance(m, dict):
                raw_messages.append(m)

        trimmed = await context_manager.trim_messages(raw_messages, system_prompt)

        # 转为 LangChain 消息格式
        messages = []
        for m in trimmed:
            role = m.get("role", "user") if isinstance(m, dict) else getattr(m, "role", "user")
            content = m.get("content", "") if isinstance(m, dict) else getattr(m, "content", "")
            if role == "system":
                messages.append(SystemMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))

        # 调用 LLM
        response = await llm_with_tools.ainvoke(messages)

        elapsed = time.time() - t0
        has_tools = bool(response.tool_calls)
        logger.info(f"[llm_call] tool_calls={has_tools} elapsed={elapsed:.2f}s iterations={state.get('iterations', 0)}")

        if response.tool_calls:
            return {
                "messages": [AIMessage(content=response.content or "", tool_calls=response.tool_calls)],
                "tool_calls": response.tool_calls,
            }
        else:
            return {
                "messages": [AIMessage(content=response.content)],
                "final_answer": response.content,
                "tool_calls": [],
            }

    return llm_call_node


def _make_tool_executor(tool_registry):
    """工具执行：风险审批 + 错误重试"""

    async def tool_executor_node(state: AgentState) -> dict:
        from app.agent.tool_registry import RiskLevel
        results = []
        tools_succeeded = []
        needs_approval = False
        pending_tool = None

        for tc in state["tool_calls"]:
            tool_name = tc.get("name", "") if isinstance(tc, dict) else tc.name
            tool_args = tc.get("args", {}) if isinstance(tc, dict) else tc.args
            tool_id = tc.get("id", "") if isinstance(tc, dict) else tc.id

            risk = tool_registry.get_risk_level(tool_name)

            # 高风险 → 请求审批
            if risk == RiskLevel.HIGH:
                needs_approval = True
                pending_tool = {"id": tool_id, "name": tool_name, "arguments": tool_args}
                results.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": f"⚠️ {tool_name} 是高风险操作，需要用户确认",
                })
                continue

            # 执行（含 1 次重试）
            result = None
            for attempt in range(2):
                try:
                    result = await tool_registry.execute(tool_name, tool_args)
                    # 检查是否执行失败（execute 返回 {"error": "xxx"} 表示失败）
                    if isinstance(result, dict) and result.get("error") is not None:
                        if attempt == 0:
                            logger.warning(f"工具 {tool_name} 第1次失败，重试: {result['error']}")
                            import asyncio
                            await asyncio.sleep(2)
                            continue
                    tools_succeeded.append(tool_name)
                    break
                except Exception as e:
                    if attempt == 0:
                        logger.warning(f"工具 {tool_name} 异常，重试: {e}")
                        import asyncio
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"工具 {tool_name} 重试后仍失败: {e}")
                        result = {"error": str(e)}

            results.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": str(result),
            })

        return {
            "messages": results,
            "tools_used": state.get("tools_used", []) + tools_succeeded,
            "tool_calls": [],
            "iterations": state.get("iterations", 0) + 1,
            "needs_approval": needs_approval,
            "pending_tool_call": pending_tool,  # 高风险工具待审批，调用方需持久化并通知用户
        }

    return tool_executor_node


def _make_memory_saver(memory_manager):
    """记忆保存"""

    async def memory_saver_node(state: AgentState) -> dict:
        if state.get("final_answer"):
            await memory_manager.update_session_cache(
                conversation_id=state["conversation_id"],
                messages=state["messages"] + [
                    {"role": "assistant", "content": state["final_answer"]}
                ],
            )
        return {}

    return memory_saver_node


def _should_use_tools(state: AgentState) -> str:
    if state.get("iterations", 0) >= 5:
        logger.warning("[agent] 工具调用达到上限(5轮)，强制结束")
        return "finish"
    if state.get("needs_approval"):
        # 高风险工具需要审批：pending_tool_call 已保存在 state 中
        # 调用方（对话 API）需将 pending_tool_call 持久化到 MySQL
        # 并通过 WebSocket 通知前端弹出审批对话框
        # 用户批准后，重新调用 Agent 并传入 approved_tool_call
        logger.info(f"[agent] 高风险工具待审批: {state.get('pending_tool_call')}")
        return "finish"
    if state.get("tool_calls"):
        return "use_tools"
    return "finish"
```

### 4.5 工具注册表

```python
"""工具注册表 — LangChain Tool 兼容 + 风险分级"""
import asyncio
from typing import Any, Callable, Dict
from dataclasses import dataclass
from langchain_core.tools import tool as lc_tool

from app.core.logging import get_logger

logger = get_logger(__name__)


class RiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict
    risk_level: str = RiskLevel.LOW
    func: Callable = None


class ToolRegistry:

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}

    def register(self, name: str, func: Callable, description: str,
                 parameters: dict, risk_level: str = RiskLevel.LOW):
        self._tools[name] = ToolDef(
            name=name, description=description,
            parameters=parameters, risk_level=risk_level, func=func,
        )

    def get_langchain_tools(self) -> list:
        tools = []
        for t in self._tools.values():
            tools.append(lc_tool(t.func, name=t.name, description=t.description))
        return tools

    def get_risk_level(self, name: str) -> str:
        t = self._tools.get(name)
        return t.risk_level if t else RiskLevel.LOW

    async def execute(self, name: str, arguments: dict, approved: bool = False) -> Any:
        """执行工具，失败时抛异常（让调用方决定是否重试）"""
        t = self._tools.get(name)
        if not t:
            raise ValueError(f"工具 '{name}' 不存在")

        # 参数校验（JSON Schema）
        try:
            import jsonschema
            jsonschema.validate(arguments, t.parameters)
        except ImportError:
            pass  # jsonschema 未安装时跳过校验
        except jsonschema.ValidationError as e:
            return {"error": f"参数校验失败: {e.message}"}

        if t.risk_level == RiskLevel.HIGH and not approved:
            return {
                "needs_approval": True, "tool": name,
                "arguments": arguments, "risk_level": t.risk_level,
            }

        if asyncio.iscoroutinefunction(t.func):
            return await t.func(**arguments)
        else:
            return t.func(**arguments)


# ── 内置工具 ──────────────────────────────────────────────

async def web_search(query: str, max_results: int = 5) -> dict:
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
        return {"results": [
            {"title": r["title"], "url": r["href"], "snippet": r["body"]}
            for r in results
        ]}


async def execute_code(language: str, code: str) -> dict:
    sandbox_images = {"python": "python:3.12-slim", "javascript": "node:20-slim"}
    image = sandbox_images.get(language)
    if not image:
        return {"error": f"不支持的语言: {language}"}

    proc = await asyncio.create_subprocess_exec(
        "docker", "run", "--rm",
        "--network=none",           # 禁止网络访问
        "--memory=128m",            # 内存限制
        "--cpus=0.5",               # CPU 限制
        "--read-only",              # 只读文件系统
        "--tmpfs", "/tmp:size=10m", # 临时文件限制
        "--pids-limit", "50",       # 防止 fork 炸弹
        "--security-opt", "no-new-privileges",  # 禁止提权
        image, "sh", "-c", code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
    return {
        "stdout": stdout.decode()[:5000],
        "stderr": stderr.decode()[:2000],
        "exit_code": proc.returncode,
    }


async def read_file(path: str) -> dict:
    from pathlib import Path
    workspace = Path("/workspace").resolve()
    target = (workspace / path).resolve()
    if not str(target).startswith(str(workspace)):
        return {"error": "路径穿越攻击已拦截"}
    if not target.exists():
        return {"error": f"文件不存在: {path}"}
    if target.stat().st_size > 1_000_000:
        return {"error": "文件过大（>1MB）"}
    return {"content": target.read_text(encoding="utf-8", errors="ignore")[:50000]}


async def query_database(sql: str) -> dict:
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return {"error": "只允许 SELECT 查询"}
    if "LIMIT" not in sql_upper:
        sql = sql.rstrip(";") + " LIMIT 100"

    from app.core.database import get_db_session
    async with get_db_session() as session:
        result = await session.execute(sql)
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"columns": columns, "rows": rows, "count": len(rows)}


# 注册
tool_registry = ToolRegistry()

tool_registry.register("web_search", web_search,
    description="搜索互联网获取实时信息",
    risk_level=RiskLevel.LOW,
    parameters={"type": "object", "properties": {
        "query": {"type": "string"}, "max_results": {"type": "integer", "default": 5},
    }, "required": ["query"]},
)

tool_registry.register("execute_code", execute_code,
    description="在沙箱中执行代码",
    risk_level=RiskLevel.HIGH,
    parameters={"type": "object", "properties": {
        "language": {"type": "string", "enum": ["python", "javascript"]},
        "code": {"type": "string"},
    }, "required": ["language", "code"]},
)

tool_registry.register("read_file", read_file,
    description="读取工作空间中的文件",
    risk_level=RiskLevel.LOW,
    parameters={"type": "object", "properties": {
        "path": {"type": "string"},
    }, "required": ["path"]},
)

tool_registry.register("query_database", query_database,
    description="查询数据库（只读 SELECT）",
    risk_level=RiskLevel.MEDIUM,
    parameters={"type": "object", "properties": {
        "sql": {"type": "string"},
    }, "required": ["sql"]},
)
```

### 4.6 记忆系统

```python
"""两层记忆 — Redis 会话缓存 + Qdrant 长期记忆"""
import json
import uuid
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)

MEMORY_COLLECTION = "memory_vectors"


class MemoryManager:

    def __init__(self, qdrant_mapper, embedding_func, llm_client=None):
        """
        Args:
            qdrant_mapper: QdrantMapper 实例
            embedding_func: async embedding 函数
            llm_client: LlamaIndex LLM 实例（用于摘要压缩）
        """
        self.qdrant = qdrant_mapper
        self.embedding_func = embedding_func
        self.llm = llm_client
        self.qdrant.ensure_collection(MEMORY_COLLECTION, vector_size=1024)

    # ── Redis 会话缓存 ──────────────────────────────────

    async def get_session_cache(self, conversation_id: int) -> dict:
        from app.core.redis_client import get_redis
        redis = get_redis()
        data = await redis.get(f"memory:session:{conversation_id}")
        return json.loads(data) if data else {"messages": [], "last_active": None}

    async def update_session_cache(self, conversation_id: int, messages: list):
        from app.core.redis_client import get_redis
        redis = get_redis()
        await redis.set(
            f"memory:session:{conversation_id}",
            json.dumps({
                "messages": messages[-50:],
                "last_active": datetime.utcnow().isoformat(),
            }, ensure_ascii=False),
            ex=3600,
        )

    # ── 长期记忆存入 Qdrant ─────────────────────────────

    async def save_detail(self, conversation_id: int, user_id: int, messages: list):
        """详细日志（每小时 Celery 触发）"""
        if not messages:
            return

        text = "\n".join(f"[{m.get('role')}] {m.get('content', '')}" for m in messages)
        vector = await self.embedding_func(text[:2000])
        point_id = str(uuid.uuid4())

        self.qdrant.upsert(
            collection=MEMORY_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload={
                "type": "detail",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "messages": messages,
                "saved_at": datetime.utcnow().isoformat(),
            },
        )

    async def save_summary(self, conversation_id: int, user_id: int, messages: list):
        """压缩摘要（30 分钟无互动时触发）"""
        if not messages:
            return

        text = "\n".join(f"{m.get('role')}: {m.get('content', '')}" for m in messages)

        # LLM 压缩
        summary = text[:500]  # fallback
        if self.llm:
            try:
                import asyncio
                response = await asyncio.to_thread(
                    self.llm.complete,
                    f"将以下对话压缩为结构化摘要（200字内），保留：用户核心需求、关键话题、待办事项。\n\n{text[:3000]}"
                )
                summary = str(response).strip() or summary
            except Exception as e:
                logger.warning(f"LLM 摘要生成失败，降级为截取: {e}")

        vector = await self.embedding_func(summary)
        point_id = str(uuid.uuid4())

        self.qdrant.upsert(
            collection=MEMORY_COLLECTION,
            point_id=point_id,
            vector=vector,
            payload={
                "type": "summary",
                "conversation_id": conversation_id,
                "user_id": user_id,
                "summary": summary,
                "saved_at": datetime.utcnow().isoformat(),
            },
        )

    # ── 语义检索 ────────────────────────────────────────

    async def search(self, query: str, user_id: int, limit: int = 5) -> str:
        """检索相关记忆（摘要优先）"""
        query_vector = await self.embedding_func(query)

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        results = self.qdrant.search(
            collection=MEMORY_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            score_threshold=0.35,
            filter_payload=Filter(must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id))
            ]),
        )

        if not results:
            return ""

        parts = []
        for r in results:
            ptype = r.payload.get("type", "detail")
            if ptype == "summary":
                parts.append(f"[摘要 | {r.payload.get('saved_at', '')}] {r.payload.get('summary', '')}")
            else:
                msg_count = len(r.payload.get("messages", []))
                parts.append(f"[详细日志 | {r.payload.get('saved_at', '')} | {msg_count}条消息]")

        return "\n".join(parts)
```

### 4.7 上下文窗口管理

```python
"""对话上下文窗口管理 — 滑动窗口 + 摘要压缩"""

MAX_CONTEXT_MESSAGES = 20


class ContextManager:

    def __init__(self, llm_client=None):
        self.llm = llm_client

    async def trim_messages(self, messages: list, system_prompt: str = "") -> list:
        """超过阈值时压缩旧消息为摘要"""
        if len(messages) <= MAX_CONTEXT_MESSAGES:
            result = []
            if system_prompt:
                result.append({"role": "system", "content": system_prompt})
            result.extend(messages)
            return result

        old_messages = messages[:-MAX_CONTEXT_MESSAGES]
        recent_messages = messages[-MAX_CONTEXT_MESSAGES:]

        summary = await self._summarize(old_messages)

        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        result.append({"role": "system", "content": f"【历史对话摘要】\n{summary}"})
        result.extend(recent_messages)
        return result

    async def _summarize(self, messages: list) -> str:
        conversation = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        prompt = f"将以下对话压缩为200字摘要，保留关键信息和用户意图：\n\n{conversation}"

        if self.llm:
            try:
                import asyncio
                result = await asyncio.to_thread(self.llm.complete, prompt)
                return str(result).strip()
            except Exception:
                pass
        # 降级：截取最近几条消息而非完全丢弃
        recent = messages[-5:]
        fallback = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')[:200]}" for m in recent)
        return f"（共 {len(messages)} 条历史消息，以下为最近摘要）\n{fallback}"
```

### 4.8 工作流执行引擎

```python
"""工作流执行引擎 — DAG 拓扑排序 + 逐步执行"""
from typing import Dict, List
from datetime import datetime

from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowEngine:

    def __init__(self):
        self._handlers: Dict[str, callable] = {}

    def register_handler(self, node_type: str, handler: callable):
        self._handlers[node_type] = handler

    async def execute(self, db, workflow_id: int, input_data: dict = None) -> dict:
        from app.repository.workflow_repo import WorkflowRepository
        repo = WorkflowRepository()

        workflow = await repo.find_by_id(db, workflow_id)
        dag = workflow.dag_json

        run = await repo.create_run(db, {
            "workflow_id": workflow_id, "status": 1,
            "input_json": input_data, "started_at": datetime.utcnow(),
        })

        try:
            order = self._topological_sort(dag)
            context = input_data or {}

            for step_name in order:
                step_def = dag["nodes"][step_name]
                step_type = step_def.get("type", "default")

                step_run = await repo.create_step_run(db, {
                    "run_id": run.id, "step_name": step_name,
                    "step_type": step_type, "status": 1,
                    "input_json": context, "started_at": datetime.utcnow(),
                })

                try:
                    handler = self._handlers.get(step_type)
                    if not handler:
                        raise ValueError(f"未注册的节点类型: {step_type}")

                    result = await handler(step_def, context)
                    context[step_name] = result

                    await repo.update_step_run(db, step_run.id, {
                        "status": 2, "output_json": result,
                        "finished_at": datetime.utcnow(),
                    })
                except Exception as e:
                    await repo.update_step_run(db, step_run.id, {
                        "status": 3, "error_message": str(e),
                        "finished_at": datetime.utcnow(),
                    })
                    raise

            await repo.update_run(db, run.id, {
                "status": 2, "output_json": context,
                "finished_at": datetime.utcnow(),
            })
            return context

        except Exception as e:
            await repo.update_run(db, run.id, {
                "status": 3, "error_message": str(e),
                "finished_at": datetime.utcnow(),
            })
            raise

    def _topological_sort(self, dag: dict) -> List[str]:
        nodes = dag.get("nodes", {})
        edges = dag.get("edges", [])

        in_degree = {name: 0 for name in nodes}
        adjacency = {name: [] for name in nodes}

        for edge in edges:
            src, dst = edge["from"], edge["to"]
            in_degree[dst] += 1
            adjacency[src].append(dst)

        queue = [n for n, d in in_degree.items() if d == 0]
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

## 五、辅助模块

### 5.1 应用初始化（main.py lifespan）

**设计决策**：Agent 引擎采用**懒加载**，不在启动时初始化。

原因：
- 模型由用户在前端选择（provider_id + model_name），启动时无法确定
- 启动时不依赖 LLM 服务可用性，加快启动速度
- 用户切换模型时，下次对话自动用新模型重建 Agent

启动时只初始化**非 LLM 服务**（RAG、记忆、意图路由等），Agent 引擎在首次对话时按用户选择的模型懒加载。

```python
# ── main.py lifespan：只初始化非 LLM 服务 ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化 RAG、记忆、意图路由等（不含 LLM）
    # Agent 引擎懒加载，不在这里初始化
    yield
    # 清理资源

# ── agent_service.py：懒加载 ──
class AgentService:
    async def chat(self, ..., provider_id: int, model_name: str):
        if not self.is_ready:
            # 首次对话：用前端传来的 provider_id + model_name 初始化
            # 后端从 DB 查供应商配置，创建 LLM 实例，构建 Agent 图
            await self._lazy_init(provider_id, model_name)
        ...

    def reset(self):
        """用户切换模型时重置，下次对话自动用新模型重建"""
        self._graph = None

# ── chat.py：前端透传 ──
@router.post("/conversations/{conversation_id}/chat")
async def chat(data: ChatRequest, ...):
    # 前端传 provider_id + model_name，透传给 agent_service
    result = await agent_service.chat(
        provider_id=data.provider_id,
        model_name=data.model_name,
    )
```

### 5.2 对话 API（意图路由 + Agent + 消息持久化）

```python
# backend/app/api/v1/chat.py
from pydantic import BaseModel
from typing import List, Optional

class ChatResponse(BaseModel):
    content: str
    tools_used: List[str] = []
    sources: List[str] = []
    tokens_used: int = 0
    needs_approval: bool = False
    pending_tool: Optional[dict] = None
    intent_hit: Optional[str] = None  # 命中的意图名（可选）

@router.post("/conversations/{conversation_id}/chat")
async def chat(
    conversation_id: int,
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    request: Request,
):
    user_message = data.messages[-1].content

    # 1. 意图路由（快速路径）
    intent = await request.app.state.intent_router.route(user_message)

    if intent and intent.target_type == "cache":
        # 语义缓存命中，直接返回
        return ApiResult(data=ChatResponse(
            content=intent.target_config["answer"],
            intent_hit="semantic_cache",
        ))

    if intent and intent.target_type == "skill":
        # 技能命中，路由到对应技能处理
        # TODO: 调用技能处理链
        pass

    # 2. 保存用户消息
    await _msg_service.create(db, MessageCreate(
        conversation_id=conversation_id, role="user", content=user_message,
    ))

    # 3. 调用 Agent
    agent_graph = request.app.state.agent_graph
    result = await agent_graph.ainvoke({
        "conversation_id": conversation_id,
        "user_id": current_user.id,
        "messages": [{"role": m.role, "content": m.content} for m in data.messages],
        "context": "",
        "tool_calls": [],
        "tools_used": [],
        "final_answer": None,
        "iterations": 0,
        "token_budget": 32000,
        "tokens_used": 0,
        "needs_approval": False,
        "pending_tool_call": None,
    })

    # 4. 保存助手回复 + 工具调用记录（同一事务）
    await _msg_service.create(db, MessageCreate(
        conversation_id=conversation_id, role="assistant",
        content=result["final_answer"],
    ))
    for tool_name in result.get("tools_used", []):
        await _msg_service.create(db, MessageCreate(
            conversation_id=conversation_id, role="tool",
            content=f"[工具调用] {tool_name}",
        ))

    return ApiResult(data=ChatResponse(
        content=result["final_answer"],
        tools_used=result.get("tools_used", []),
        tokens_used=result.get("tokens_used", 0),
        needs_approval=result.get("needs_approval", False),
        pending_tool=result.get("pending_tool_call"),
        intent_hit=intent.intent_name if intent else None,
    ))
```

### 5.3 SSE 流式响应（REST 端点）

```python
# backend/app/api/v1/chat.py
from fastapi.responses import StreamingResponse
import json

@router.post("/conversations/{conversation_id}/chat/stream")
async def chat_stream(
    conversation_id: int,
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    request: Request,
):
    """SSE 流式对话（不适合 WebSocket 的客户端用这个）"""

    async def event_generator():
        agent_graph = request.app.state.agent_graph

        # 保存用户消息
        await _msg_service.create(db, MessageCreate(
            conversation_id=conversation_id, role="user",
            content=data.messages[-1].content,
        ))

        # 流式输出
        final_answer = ""
        tools_used = []

        async for event in agent_graph.astream_events({
            "conversation_id": conversation_id,
            "user_id": current_user.id,
            "messages": [{"role": m.role, "content": m.content} for m in data.messages],
            "context": "", "tool_calls": [], "tools_used": [],
            "final_answer": None, "iterations": 0,
            "token_budget": 32000, "tokens_used": 0,
            "needs_approval": False, "pending_tool_call": None,
        }):
            if event["event"] == "on_chat_model_stream":
                token = event["data"]["chunk"].content
                if token:
                    final_answer += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            elif event["event"] == "on_tool_start":
                tool_name = event["name"]
                tools_used.append(tool_name)
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"

            elif event["event"] == "on_tool_end":
                yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['name']})}\n\n"

        # 保存助手回复
        if final_answer:
            await _msg_service.create(db, MessageCreate(
                conversation_id=conversation_id, role="assistant",
                content=final_answer,
            ))

        yield f"data: {json.dumps({'type': 'done', 'tools_used': tools_used})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 5.4 WebSocket 接入 Agent 流

```python
# backend/app/api/v1/websocket.py
@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: int):
    # TODO: WebSocket 鉴权 — 从 query 参数 ?token=<jwt> 提取 user_id
    # 验证失败返回 403 关闭连接，token 过期需客户端重新获取
    # 验证成功后需校验 conversation_id 是否属于该 user_id（防越权）
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

            await websocket.send_json({"type": "start"})

            agent_graph = websocket.app.state.agent_graph

            async for event in agent_graph.astream_events({
                "conversation_id": conversation_id,
                "user_id": 0,
                "messages": [{"role": "user", "content": user_message}],
                "context": "", "tool_calls": [], "tools_used": [],
                "final_answer": None, "iterations": 0,
                "token_budget": 32000, "tokens_used": 0,
                "needs_approval": False, "pending_tool_call": None,
            }):
                if event["event"] == "on_chat_model_stream":
                    token = event["data"]["chunk"].content
                    if token:
                        await websocket.send_json({"type": "token", "content": token})
                elif event["event"] == "on_tool_start":
                    await websocket.send_json({"type": "tool_start", "tool": event["name"]})
                elif event["event"] == "on_tool_end":
                    await websocket.send_json({"type": "tool_end", "tool": event["name"]})

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: conversation={conversation_id}")
```

### 5.5 其他辅助模块

**httpx 连接池复用**：

```python
# backend/app/services/llm_chat_service.py
class LLMChatService:
    def __init__(self):
        self._client = None

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

**JWT 密钥强制校验**：

```python
# backend/app/core/security.py
from app.core.config import get_settings
settings = get_settings()
JWT_SECRET_KEY = settings.JWT_SECRET_KEY

if not JWT_SECRET_KEY or JWT_SECRET_KEY == "beautiful-elf-secret-change-me":
    raise RuntimeError(
        "JWT_SECRET_KEY 未设置或使用了默认值！"
        "请在 .env 中设置：python -c 'import secrets; print(secrets.token_urlsafe(64))'"
    )
```

**API 限流**：

```python
# backend/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

**LangFuse 可观测性**：

```python
# backend/app/agent/tracing.py
import os

LANGFUSE_ENABLED = os.getenv("LANGFUSE_PUBLIC_KEY") is not None
_tracer = None

def init_tracing():
    global _tracer
    if not LANGFUSE_ENABLED:
        return
    try:
        from langfuse import Langfuse
        _tracer = Langfuse()
    except ImportError:
        pass

def trace_span(name: str, metadata: dict = None):
    if not _tracer:
        from contextlib import contextmanager
        @contextmanager
        def noop():
            yield
        return noop()
    return _tracer.span(name=name, metadata=metadata or {})
```

### 5.6 Celery 定时任务（完整实现）

```python
# backend/app/tasks/memory_tasks.py
from celery import shared_task
from datetime import datetime, timedelta
import asyncio

# Celery 任务使用 asyncio.run() 创建独立事件循环。
# 仅在 prefork 模式下安全；如果 worker 使用 gevent/eventlet，
# 需要用 gevent.monkey.patch_all() 或 asgiref.sync.async_to_sync() 替代。

@shared_task
def hourly_detail_save():
    """每小时：活跃会话存详细日志"""
    from app.core.database import get_db_session
    from app.core.redis_client import get_redis
    from app.agent.memory_manager import MemoryManager
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.agent.llm_service import get_embedding

    async def _run():
        redis = get_redis()
        qdrant_mapper = QdrantMapper()
        embedding = get_embedding()
        memory = MemoryManager(
            qdrant_mapper=qdrant_mapper,
            embedding_func=lambda q: embedding.aget_text_embedding(q),
        )

        # 扫描 Redis 中所有活跃会话
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="memory:session:*", count=100)
            for key in keys:
                data = await redis.get(key)
                if not data:
                    continue
                import json
                cache = json.loads(data)
                last_active = cache.get("last_active")
                if not last_active:
                    continue

                # 只处理过去 1 小时有活动的会话
                last_dt = datetime.fromisoformat(last_active)
                if datetime.utcnow() - last_dt > timedelta(hours=1):
                    continue

                # 从 key 提取 conversation_id
                conv_id = int(key.split(":")[-1])

                # 保存详细日志
                async with get_db_session() as db:
                    # 获取 user_id（从会话记录查）
                    from app.repository.conversation_repo import ConversationRepository
                    conv_repo = ConversationRepository(db)
                    conv = await conv_repo.find_by_id(conv_id)
                    if conv:
                        await memory.save_detail(
                            conversation_id=conv_id,
                            user_id=conv.user_id,
                            messages=cache.get("messages", []),
                        )

            if cursor == 0:
                break

    asyncio.run(_run())


@shared_task
def check_idle_summaries():
    """每 5 分钟：会话 30 分钟无互动 → 存压缩摘要"""
    from app.core.redis_client import get_redis
    from app.agent.memory_manager import MemoryManager
    from app.mappers.qdrant_mapper import QdrantMapper
    from app.agent.llm_service import get_embedding, get_llama_index_llm

    async def _run():
        redis = get_redis()
        qdrant_mapper = QdrantMapper()
        embedding = get_embedding()
        llama_llm = get_llama_index_llm()
        memory = MemoryManager(
            qdrant_mapper=qdrant_mapper,
            embedding_func=lambda q: embedding.aget_text_embedding(q),
            llm_client=llama_llm,
        )

        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="memory:session:*", count=100)
            for key in keys:
                data = await redis.get(key)
                if not data:
                    continue
                import json
                cache = json.loads(data)
                last_active = cache.get("last_active")
                if not last_active:
                    continue

                last_dt = datetime.fromisoformat(last_active)
                if datetime.utcnow() - last_dt < timedelta(minutes=30):
                    continue

                conv_id = int(key.split(":")[-1])

                # 生成压缩摘要
                from app.core.database import get_db_session
                async with get_db_session() as db:
                    from app.repository.conversation_repo import ConversationRepository
                    conv_repo = ConversationRepository(db)
                    conv = await conv_repo.find_by_id(conv_id)
                    if conv:
                        await memory.save_summary(
                            conversation_id=conv_id,
                            user_id=conv.user_id,
                            messages=cache.get("messages", []),
                        )

                # 删除 Redis 缓存（已归档）
                await redis.delete(key)

            if cursor == 0:
                break

    asyncio.run(_run())
```

### 5.7 评估流水线

```python
# backend/app/agent/eval_pipeline.py
"""评估流水线 — 规则初筛 + LLM 复核"""
from typing import List
from pydantic import BaseModel


class EvalCase(BaseModel):
    id: int
    question: str
    expected_keywords: List[str] = []
    forbidden_patterns: List[str] = []


class EvalResult(BaseModel):
    case_id: int
    passed: bool
    correctness: float
    has_forbidden: bool


class EvalPipeline:
    def __init__(self, agent_graph, llm_client):
        self.agent = agent_graph
        self.llm = llm_client

    async def run_eval(self, cases: List[EvalCase]) -> List[EvalResult]:
        results = []
        for case in cases:
            agent_result = await self.agent.ainvoke({
                "conversation_id": 0, "user_id": 0,
                "messages": [{"role": "user", "content": case.question}],
                "context": "", "tool_calls": [], "tools_used": [],
                "final_answer": None, "iterations": 0,
                "token_budget": 32000, "tokens_used": 0,
                "needs_approval": False, "pending_tool_call": None,
            })
            answer = agent_result.get("final_answer", "")

            # 规则初筛
            has_forbidden = any(p in answer for p in case.forbidden_patterns)
            keyword_hits = sum(1 for kw in case.expected_keywords if kw in answer)
            keyword_ratio = keyword_hits / max(len(case.expected_keywords), 1)

            # 边界 case 用 LLM 复核
            if 0.3 < keyword_ratio < 0.7 and not has_forbidden:
                score = await self._llm_judge(case, answer)
            else:
                score = keyword_ratio

            results.append(EvalResult(
                case_id=case.id,
                passed=score >= 0.7 and not has_forbidden,
                correctness=score,
                has_forbidden=has_forbidden,
            ))
        return results

    async def _llm_judge(self, case: EvalCase, answer: str) -> float:
        import asyncio
        prompt = f"评估回答质量（0-1）：\n问题: {case.question}\n回答: {answer}\n期望关键词: {case.expected_keywords}"
        try:
            result = await asyncio.to_thread(self.llm.complete, prompt)
            return float(str(result).strip())
        except Exception:
            return 0.5
```

---

## 六、降级策略

```
完整模式:  Agent + RAG + 工具 + 记忆 + 意图路由
  ↓ 意图服务不可用
降级模式 0:  跳过意图路由，直接进 Agent（延迟略增）
  ↓ RAG 不可用（Qdrant 宕机 / Embedding 超时）
降级模式 1:  Agent + 工具 + 记忆（无知识库检索）
  ↓ 工具不可用（Docker 不可用 / 搜索限流）
降级模式 2:  Agent + 记忆（纯对话，无外部能力）
  ↓ LLM 不可用（Ollama 宕机 / 云端 API 超时）
降级模式 3:  返回缓存高频回答 + 告知用户服务暂不可用
```

实现在各节点的 try-catch 中：任一组件失败不影响其他组件，降级日志记录到 LangFuse。

---

## 七、文件清单

### 新增

```
backend/app/agent/
├── __init__.py              # 模块导出
├── llm_service.py           # LLM 服务工厂（多供应商 + 配置管理）
├── engine.py                # Agent 引擎（LangGraph + 依赖注入）
├── rag_pipeline.py          # RAG 管道（LlamaIndex + Qdrant）
├── tool_registry.py         # 工具注册表（LangChain Tool 兼容）
├── memory_manager.py        # 两层记忆（Redis + Qdrant memory_vectors）
├── context_manager.py       # 上下文窗口管理
├── intent_router.py         # 意图路由层（向量相似度 + 语义缓存）
├── workflow_engine.py       # 工作流执行引擎
├── tracing.py               # LangFuse 可观测性
└── eval_pipeline.py         # 评估流水线

backend/app/tasks/
└── memory_tasks.py          # Celery 定时任务（记忆归档）

backend/app/repository/
└── intent_repo.py           # 意图数据仓库
```

### 修改

```
backend/app/api/v1/chat.py              # 意图路由 + Agent + 消息持久化 + SSE
backend/app/api/v1/knowledge.py         # 接入 LlamaIndex RAG
backend/app/api/v1/websocket.py         # Agent 流式输出
backend/app/api/v1/intent.py            # 意图 CRUD API（新增路由）
backend/app/services/llm_chat_service.py # httpx 连接池
backend/app/core/security.py            # JWT 强制校验
backend/app/models/intent.py            # 意图模型（已有，确认字段）
backend/main.py                         # 限流 + lifespan 初始化
backend/requirements.txt                # 新增依赖
```

---

## 八、执行计划

```
Phase 1 — 核心链路（P0，1-2 周）
├── Day 1:    LLM 服务工厂（llm_service.py + 多供应商配置）
├── Day 2-3:  RAG 管道（LlamaIndex + Qdrant + 文档入库 + 检索）
├── Day 4-5:  工具注册表（LangChain Tool + 风险分级 + 沙箱）
├── Day 6-8:  Agent 引擎（LangGraph + context_builder + token 预算 + 上下文裁剪）
├── Day 9:    意图路由层（向量检索 + 语义缓存）
└── Day 10:   集成测试 + 对话流打通

Phase 2 — 质量加固（P1，1 周）
├── Day 1:    httpx 连接池 + JWT 校验
├── Day 2:    消息自动保存 + 工具调用记录持久化
├── Day 3:    SSE 流式响应
├── Day 4-5:  记忆系统（Redis + Qdrant memory_vectors + Celery 定时完整实现）

Phase 3 — 生产化（P2，1 周）
├── Day 1:    WebSocket Agent 流
├── Day 2-3:  工作流执行引擎
├── Day 4:    API 限流 + LangFuse tracing
└── Day 5:    评估流水线 + 压测
```

---

## 九、验收标准

| 模块 | 验收标准 |
|------|----------|
| LLM 服务 | 切换 provider 配置 → Agent 自动使用对应供应商，无需改代码 |
| 意图路由 | 输入技能触发词 → 命中意图 → 路由到对应技能；未命中 → 进入 Agent |
| 语义缓存 | 输入几乎相同的问题 → 直接返回缓存回答，不走 LLM |
| RAG | 上传 PDF → LlamaIndex 解析/分块/Embedding → Qdrant 存储 → 检索返回相关段落 |
| Agent | 发送问题 → 检索记忆+知识 → 调用工具 → 返回答案；token 预算耗尽自动停止 |
| Tool Calling | 问"今天天气" → web_search → 返回天气；execute_code 需用户确认才执行 |
| 工具重试 | 工具首次失败 → 自动重试 1 次 → 仍失败则返回错误信息给 LLM |
| 消息持久化 | 对话后 → MySQL messages 表有用户消息 + 助手回复 + 工具调用记录 |
| 上下文管理 | 50 条消息 → 自动压缩旧消息为摘要 → 不超出 context window |
| 记忆 | 1 小时后 → Qdrant 有详细日志；30 分钟无互动 → 有压缩摘要 |
| SSE | POST /chat/stream → 逐 token 输出 + 工具状态事件 |
| WebSocket | 连接 → 发消息 → 实时 token 流 + 工具状态 |
| 降级 | Qdrant 宕机 → Agent 仍能对话；LLM 宕机 → 返回缓存回答 |

---

## 十、与 backend-architecture.md 的关系

`backend-architecture.md` 是前期框架设计文档，描述了分层架构、数据归属、事件推送、安全规约等基础设计。本文档是 Agent 层的详细升级方案。

**继承关系**：

| 内容 | 来源 |
|------|------|
| 分层架构（API/Service/Repository/Mapper） | backend-architecture.md（本文档不重复） |
| CORS / 安全 / 日志 / 命名规约 | backend-architecture.md |
| 健康检查 / 事件推送 / 宠物系统 | backend-architecture.md |
| 数据归属（MySQL/Qdrant/Redis 分工） | 本文档为准（向量全部走 Qdrant） |
| RAG 实现 | 本文档为准（LlamaIndex） |
| Agent 引擎 | 本文档为准（LangGraph + LangChain） |
| 意图路由 | 本文档新增 |
| LLM 多供应商 | 本文档为准（llm_service.py） |
