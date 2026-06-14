# Beautiful-Elf 迁移及操作手册

> 生成时间：2026-06-14 18:35
> 环境：服务器 iZ2zegpoa6uklmupce9o61Z → 本地 Windows 开发环境
> 分支：dev

---

## 一、本次修复汇总（5 个问题）

### 1.1 scikit-learn 依赖遗漏

**问题：** `backend/app/router/features.py` 和 `v4_features.py` 直接 import sklearn，但 requirements.txt 从未声明。

**修复：**
- 文件：`backend/requirements.txt`
- 新增：`scikit-learn==1.8.0`
- 版本锁定 1.8.0，对齐模型 bundle 序列化版本

**本地操作：**
```bash
pip install scikit-learn==1.8.0
```

### 1.2 tokenizers 依赖遗漏

**问题：** ONNX embedding 和 BGE 推理需要 `tokenizers` 库，requirements.txt 从未声明。

**修复：**
- 文件：`backend/requirements.txt`
- 新增：`tokenizers>=0.15.0`

**本地操作：**
```bash
pip install tokenizers
```

### 1.3 ML 路由参数缺失

**问题：** `model_selector.py` 构建 `InferenceRequest` 时漏传 `prev_assistant_text` 和 `prev_assistant_usage` 两个必填参数。

**修复文件：** `backend/app/router/model_selector.py`

**改动 1 — `classify()` 方法：**
```python
# 从历史中提取上一条助手消息和用量
prev_assistant_text = None
prev_assistant_usage = None
if history:
    for msg in reversed(history):
        if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("content"):
            prev_assistant_text = msg["content"]
            prev_assistant_usage = msg.get("usage") or msg.get("metadata", {}).get("usage")
            break

# 传给 predict
ml = self._ml_strategy.predict(user_message, history=history, history_user_texts=history_user_texts,
                               prev_assistant_text=prev_assistant_text, prev_assistant_usage=prev_assistant_usage)
```

**改动 2 — `predict()` 签名扩展：**
```python
def predict(self, message, history=None, history_user_texts=None,
            prev_assistant_text=None, prev_assistant_usage=None):
```

**改动 3 — `_build_request()` 补全参数：**
```python
def _build_request(self, message, routing_history, *, history_user_texts=None,
                   prev_assistant_text=None, prev_assistant_usage=None):
    ...
    return self._request_type(
        current_user_text=message,
        history_user_texts=history_texts,
        prev_assistant_text=prev_assistant_text,      # 新增
        prev_assistant_usage=prev_assistant_usage,     # 新增
        prev_route_decisions=decisions,
        context_metadata={..., "has_prev_assistant": bool(prev_assistant_text)},
    )
```

### 1.4 ONNX embedding 模型路径错误

**问题：** `onnx_embedding_service.py` 第 22 行路径多跳了一层 parent，导致找不到模型文件。

**修复文件：** `backend/app/services/onnx_embedding_service.py`

```python
# 旧（错误）：parent.parent.parent → backend/
_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "router" / "models" / "Qwen3-Embedding-0.6B-ONNX"

# 新（正确）：parent.parent → backend/app/
_MODEL_DIR = Path(__file__).resolve().parent.parent / "router" / "models" / "Qwen3-Embedding-0.6B-ONNX"
```

### 1.5 OnnxLlamaIndexEmbedding 未继承 BaseEmbedding

**问题：** 普通 Python 类，无法通过 LlamaIndex 的 `isinstance(embed_model, BaseEmbedding)` 检查。

**修复文件：** `backend/app/services/onnx_embedding_service.py`

```python
# 旧
class OnnxLlamaIndexEmbedding:
    def __init__(self, service):
        self._service = service
    async def aget_text_embedding(self, text): ...
    def get_text_embedding(self, text): ...

# 新
from llama_index.core.embeddings import BaseEmbedding

class OnnxLlamaIndexEmbedding(BaseEmbedding):
    _service: OnnxEmbeddingService = None
    class Config:
        arbitrary_types_allowed = True
    def __init__(self, service, **kwargs):
        super().__init__(model_name=service.model_dir, **kwargs)
        object.__setattr__(self, "_service", service)
    async def _aget_text_embedding(self, text): ...  # 注意下划线前缀
    def _get_text_embedding(self, text): ...
```

---

## 二、QueryPipeline → Workflow 迁移

### 2.1 背景

`llama_index.core.query_pipeline` 已从 LlamaIndex 中**彻底移除**（GitHub 404）。
当前版本 `llama-index==0.14.22` 不再包含此模块。

替代方案：**LlamaIndex Workflow**（事件驱动 @step 编排）。

### 2.2 迁移内容

**文件：** `backend/app/agent/rag_pipeline.py`

**改动：**
1. 移除 `from llama_index.core.query_pipeline import QueryPipeline, InputComponent, ArgPackModule`
2. 新增 `_build_rag_workflow()` 函数，使用 Workflow 编排
3. `CompactAndRefine()` 直接实例化 → `get_response_synthesizer(response_mode="compact")`
4. `search()` 方法优先走 Workflow，失败降级手动检索

### 2.3 新架构

```
StartEvent(query_str)
    ↓ @step retrieve
RerankEvent(query_str, nodes)
    ↓ @step rerank
SynthesizeEvent(query_str, nodes)
    ↓ @step synthesize
StopEvent(result)
```

### 2.4 Workflow 核心代码

```python
from llama_index.core.workflow import (
    Workflow, step, StartEvent, StopEvent, Context, Event,
)

class RerankEvent(Event):
    query_str: str
    nodes: list

class SynthesizeEvent(Event):
    query_str: str
    nodes: list

class RAGWorkflow(Workflow):
    @step()
    async def retrieve(self, ctx: Context, ev: StartEvent) -> RerankEvent:
        nodes = await asyncio.to_thread(retriever.retrieve, ev.query_str)
        return RerankEvent(query_str=ev.query_str, nodes=nodes)

    @step()
    async def rerank(self, ctx: Context, ev: RerankEvent) -> SynthesizeEvent:
        nodes = ev.nodes
        if reranker:
            query_bundle = QueryBundle(query_str=ev.query_str)
            nodes = reranker.postprocess_nodes(nodes, query_bundle=query_bundle)
        return SynthesizeEvent(query_str=ev.query_str, nodes=nodes)

    @step()
    async def synthesize(self, ctx: Context, ev: SynthesizeEvent) -> StopEvent:
        if synthesizer:
            response = synthesizer.synthesize(QueryBundle(query_str=ev.query_str), ev.nodes)
            return StopEvent(result=str(response))
        else:
            # 文本拼接降级
            parts = [f"[{n.metadata.get('filename','未知')}]\n{n.text}" for n in ev.nodes[:5]]
            return StopEvent(result="\n\n---\n\n".join(parts))
```

### 2.5 get_response_synthesizer 说明

工厂函数，创建答案合成器。

| response_mode | 行为 | 适用场景 |
|---|---|---|
| `"compact"` | 多个 chunk 压缩到一次 prompt | **默认推荐**，省 token |
| `"refine"` | 逐个 chunk 精炼答案 | 长文档深度分析 |
| `"tree_summarize"` | 递归分层摘要 | 超长文档总结 |
| `"no_text"` | 不合成，只返回原始片段 | 只需原文 |

---

## 三、待做：混合检索 + 直接拼 prompt（借鉴 OpenSquilla）

> 以下为讨论方案，尚未实施，可在新环境继续。

### 3.1 目标

借鉴 OpenSquilla 的 HybridRetriever，将 RAG 从"纯向量检索 + synthesizer 合成"升级为"混合检索 + 直接拼 prompt"。

### 3.2 OpenSquilla 方案分析

```python
class HybridRetriever:
    strategy: "lexical" | "semantic" | "hybrid"
    rrf_k: int = 60  # Reciprocal Rank Fusion 参数
    lexical_top_n: int = 20
    semantic_top_n: int = 20
```

**核心逻辑：**
- **lexical** — BM25 关键词匹配（不需要 embedding 模型）
- **semantic** — 向量余弦相似度（需要 embedding）
- **hybrid** — 两者结果通过 RRF 融合排序
- **自动降级：** embedding 不可用时自动切 lexical-only

**RRF 融合算法：**
```python
def rrf(rankings: list[list[Hit]], k: int = 60) -> list[tuple[str, float]]:
    scores = {}
    for ranked in rankings:
        for hit in ranked:
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + hit.rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### 3.3 迁移计划

| 步骤 | 内容 | 文件 |
|------|------|------|
| 1 | 实现 BM25 检索器（用 `rank_bm25` 或自建倒排索引） | 新建 `backend/app/agent/bm25_retriever.py` |
| 2 | 实现 RRF 融合函数 | 新建 `backend/app/agent/rrf_fusion.py` |
| 3 | 修改 `rag_pipeline.py`，组合向量检索 + BM25 检索 | `rag_pipeline.py` |
| 4 | 移除 synthesizer，检索结果直接拼入 prompt | `rag_pipeline.py` + `context_engine.py` |
| 5 | 添加 `RAG_STRATEGY` 配置项（lexical/semantic/hybrid） | `.env.example` |

### 3.4 预期收益

| 指标 | 当前 | 迁移后 |
|------|------|--------|
| 召回率 | 纯向量，关键词弱 | 向量 + 关键词互补 |
| Token 消耗 | synthesizer 额外消耗 | 无额外消耗 |
| 降级能力 | embedding 挂了就挂 | 自动切 BM25 |
| 响应质量 | 取决于 synthesizer | 取决于主 LLM（更强） |

---

## 四、runtime_src 目录说明

### 4.1 来源

从借鉴项目 `opensquilla` 复制：
```
源：git@github.com:opensquilla/opensquilla.git
路径：src/opensquilla/squilla_router/models/v4.2_phase3_inference/runtime_src/
目标：backend/app/router/models/v4.2_phase3_inference/runtime_src/
```

### 4.2 内容

```
runtime_src/
└── src/router/
    ├── __init__.py
    ├── flags.py          → 特征标志
    ├── predictor.py      → 预测器
    ├── bge_onnx.py       → BGE 向量推理
    ├── features.py       → 特征工程
    ├── v4_features.py    → v4 特征
    ├── trajectory.py     → 轨迹分析
    └── inference/
        ├── core.py       → InferenceCore（主推理引擎）
        ├── types.py      → InferenceRequest 数据结构
        ├── ensemble.py   → 模型融合
        ├── features.py   → 特征构建
        ├── artifacts.py  → 模型加载
        ├── postprocess.py→ 后处理规则
        └── heads.py      → 推理头
```

### 4.3 .gitignore 问题

当前 `.gitignore` 排除了整个 `backend/app/router/models/` 目录（因 ONNX 模型文件太大）。
建议拆分：只排除模型权重文件，不排除源码。

```gitignore
# ONNX 模型权重（体积太大，不入库）
backend/app/router/models/**/*.onnx
backend/app/router/models/**/*.bin
backend/app/router/models/**/bge_onnx/
backend/app/router/models/**/mlp/
backend/app/router/models/**/features/

# 以下需要入库
# backend/app/router/models/**/runtime_src/
# backend/app/router/models/**/*.yaml
# backend/app/router/models/**/*.json
```

---

## 五、本地环境完整依赖安装

```bash
cd C:\Users\CC\Desktop\beautiful-elf\backend
pip install -r requirements.txt

# 本次新增的依赖（如果 requirements.txt 已更新则不需要手动装）
pip install scikit-learn==1.8.0
pip install tokenizers>=0.15.0
```

---

## 六、验证清单

启动后端后检查以下日志：

| 检查项 | 预期日志 | 状态 |
|--------|---------|------|
| ONNX embedding | `[onnx_embedding] 模型就绪: ... dim=1024` | ✅ |
| RAG 管道 | `RAG 管道初始化完成（Workflow v3.0）` | ✅ |
| 记忆管理器 | `记忆管理器就绪` | ✅ |
| 意图路由 | `意图路由就绪` | ✅ |
| ML 路由 | `[ml_strategy] ML 模型加载成功` | ✅ |
| ML 推理 | `[model_selector] ML 推理就绪`（无 InferenceRequest 报错） | ✅ |
| sklearn 版本 | 无 InconsistentVersionWarning | ✅ |
| Agent 引擎 | `Agent 引擎初始化完成 (ML路由=True)` | ✅ |

---

## 七、Git 提交记录

```
64cdea3a fix(path): ONNX embedding 模型路径多跳了一层 parent
a357fea5 fix(deps): 补充 tokenizers 依赖
5cfc6503 fix(router): ML 路由补全 prev_assistant_text/usage 参数 + scikit-learn 版本锁定
80c13693 fix(deps): 补充遗漏的 scikit-learn 依赖
bcd0728b fix(embedding): OnnxLlamaIndexEmbedding 继承 BaseEmbedding
13e241b9 refactor(rag): QueryPipeline → Workflow v3.0
```
