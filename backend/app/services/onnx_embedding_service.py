"""ONNX Embedding 服务 — 轻量级本地向量生成（替代 Ollama Embedding）

优势:
  - 无需 Ollama 服务常驻（省 ~2GB 内存 + 一个进程）
  - 直接用 onnxruntime 推理，CPU/GPU 均可
  - 模型首次加载 ~3-5s，后续推理 ~5-20ms/句（CPU）

模型:
  - Qwen3-Embedding-0.6B（1024 维，支持 MRL 维度裁剪）
  - ONNX 版本放在 backend/app/router/models/Qwen3-Embedding-0.6B-ONNX/
"""
import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# 模型路径（相对于 backend/ 目录）
_MODEL_DIR = Path(__file__).resolve().parent.parent / "router" / "models" / "Qwen3-Embedding-0.6B-ONNX"
_DEFAULT_DIMENSION = 1024
_DEFAULT_MAX_LENGTH = 32768

# 模块级单例（避免重复加载）
_instance: Optional["OnnxEmbeddingService"] = None
_init_lock = asyncio.Lock()


class OnnxEmbeddingService:
    """ONNX Embedding 服务 — 用 onnxruntime 直接推理"""

    def __init__(self, model_dir: str = "", dimension: int = _DEFAULT_DIMENSION):
        self.model_dir = model_dir or str(_MODEL_DIR)
        self.dimension = dimension
        self._model = None
        self._tokenizer = None
        self._ready = False

    async def initialize(self) -> None:
        """加载模型"""
        if self._ready:
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model)
        self._ready = True
        logger.info(f"[onnx_embedding] 模型就绪: {self.model_dir} dim={self.dimension}")

    def _load_model(self) -> None:
        """同步加载（在线程池中执行）"""
        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_path = Path(self.model_dir)

        # 优先找 onnx/model.onnx（onnx-community 格式），其次 model.onnx（平铺格式）
        onnx_file = model_path / "onnx" / "model.onnx"
        if not onnx_file.exists():
            onnx_file = model_path / "model.onnx"
        if not onnx_file.exists():
            raise FileNotFoundError(f"找不到 ONNX 模型文件: {model_path}")

        logger.info(f"[onnx_embedding] 正在加载: {onnx_file}")
        self._session = ort.InferenceSession(
            str(onnx_file),
            providers=["CPUExecutionProvider"],
        )

        # 加载 tokenizer（优先 tokenizers 库，降级 transformers）
        tokenizer_file = model_path / "tokenizer.json"
        if tokenizer_file.exists():
            self._tokenizer = Tokenizer.from_file(str(tokenizer_file))
            self._tokenizer.enable_truncation(max_length=_DEFAULT_MAX_LENGTH)
            pad_id = self._tokenizer.token_to_id("[PAD]") or self._tokenizer.token_to_id("<pad>") or 0
            self._tokenizer.enable_padding(pad_id=pad_id)
            self._use_tokenizers_lib = True
        else:
            from transformers import AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            self._use_tokenizers_lib = False

        logger.info("[onnx_embedding] 模型加载完成")

    async def get_embedding(self, text: str) -> List[float]:
        """获取单条文本的 embedding 向量"""
        if not self._ready:
            await self.initialize()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode_sync, text)

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取 embedding 向量"""
        if not self._ready:
            await self.initialize()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode_batch_sync, texts)

    def _encode_sync(self, text: str) -> List[float]:
        """同步编码单条文本"""
        if self._use_tokenizers_lib:
            encoding = self._tokenizer.encode(text)
            input_ids = np.array([encoding.ids], dtype=np.int64)
            attention_mask = np.array([encoding.attention_mask], dtype=np.int64)
        else:
            encoded = self._tokenizer(text, padding=True, truncation=True, max_length=_DEFAULT_MAX_LENGTH, return_tensors="np")
            input_ids = encoded["input_ids"].astype(np.int64)
            attention_mask = encoded["attention_mask"].astype(np.int64)

        inputs = {
            self._session.get_inputs()[0].name: input_ids,
            self._session.get_inputs()[1].name: attention_mask,
        }
        outputs = self._session.run(None, inputs)
        token_embeddings = outputs[0]

        # Mean pooling
        mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
        sum_emb = np.sum(token_embeddings * mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(mask_expanded, axis=1), 1e-9, None)
        sentence_emb = sum_emb / sum_mask

        # L2 归一化
        norm = np.linalg.norm(sentence_emb, axis=1, keepdims=True)
        sentence_emb = sentence_emb / np.clip(norm, 1e-9, None)

        vec = sentence_emb[0].tolist()
        if self.dimension < len(vec):
            vec = vec[:self.dimension]
        return vec

    def _encode_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """同步批量编码"""
        if self._use_tokenizers_lib:
            encodings = self._tokenizer.encode_batch(texts)
            input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
            attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
        else:
            encoded = self._tokenizer(texts, padding=True, truncation=True, max_length=_DEFAULT_MAX_LENGTH, return_tensors="np")
            input_ids = encoded["input_ids"].astype(np.int64)
            attention_mask = encoded["attention_mask"].astype(np.int64)

        inputs = {
            self._session.get_inputs()[0].name: input_ids,
            self._session.get_inputs()[1].name: attention_mask,
        }
        outputs = self._session.run(None, inputs)
        token_embeddings = outputs[0]

        mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
        sum_emb = np.sum(token_embeddings * mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(mask_expanded, axis=1), 1e-9, None)
        sentence_embs = sum_emb / sum_mask

        norms = np.linalg.norm(sentence_embs, axis=1, keepdims=True)
        sentence_embs = sentence_embs / np.clip(norms, 1e-9, None)

        result = sentence_embs.tolist()
        if self.dimension < len(result[0]):
            result = [vec[:self.dimension] for vec in result]
        return result

    @property
    def is_ready(self) -> bool:
        return self._ready


# ── LlamaIndex 适配器（RAG 管道需要） ────────────────────

class OnnxLlamaIndexEmbedding:
    """LlamaIndex 兼容的 ONNX Embedding 适配器

    实现 VectorStoreIndex 所需的 embed_model 接口。
    """

    def __init__(self, service: OnnxEmbeddingService):
        self._service = service
        self.model_name = service.model_dir

    async def aget_text_embedding(self, text: str) -> List[float]:
        return await self._service.get_embedding(text)

    async def aget_text_embedding_batch(self, texts: List[str], **kwargs) -> List[List[float]]:
        return await self._service.get_embeddings(texts)

    async def aget_query_embedding(self, query: str) -> List[float]:
        return await self._service.get_embedding(query)

    def get_text_embedding(self, text: str) -> List[float]:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, self._service.get_embedding(text)).result()
        return asyncio.run(self._service.get_embedding(text))

    def get_query_embedding(self, query: str) -> List[float]:
        return self.get_text_embedding(query)


# ── 全局单例 ──────────────────────────────────────────────

async def get_onnx_embedding_service(
    model_dir: str = "",
    dimension: int = _DEFAULT_DIMENSION,
) -> OnnxEmbeddingService:
    """获取全局单例（线程安全）"""
    global _instance
    if _instance is not None and _instance.is_ready:
        return _instance
    async with _init_lock:
        if _instance is not None and _instance.is_ready:
            return _instance
        _instance = OnnxEmbeddingService(model_dir=model_dir, dimension=dimension)
        await _instance.initialize()
        return _instance
