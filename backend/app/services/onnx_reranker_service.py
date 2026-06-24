"""ONNX Cross-Encoder Reranker — 轻量级 pair-wise 精排服务

借鉴 Hindsight TEMPR + ConvMemory (arXiv 2605.28062) 的精排思路:
  - 在 RRF 粗排后，用 cross-encoder 对 top-K 做 pair-wise 相关性打分
  - 本地 ONNX 推理，CPU 低延迟 (~10-30ms/pair)
  - 模型不存在时优雅降级（返回 None）

模型:
  - cross-encoder/ms-marco-MiniLM-L-6-v2 ONNX 版 (~80MB, 512 tokens)
  - 放在 backend/app/router/models/Qwen3-Reranker-0.6B/
"""
import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_DIR = Path(__file__).resolve().parent.parent / "router" / "models" / "Qwen3-Reranker-0.6B"
_MAX_LENGTH = 512

_instance: Optional["OnnxRerankerService"] = None
_init_lock: Optional[asyncio.Lock] = None


def _get_init_lock() -> asyncio.Lock:
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


class OnnxRerankerService:
    """ONNX Cross-Encoder 精排服务"""

    def __init__(self, model_dir: str = ""):
        self.model_dir = model_dir or str(_MODEL_DIR)
        self._session = None
        self._tokenizer = None
        self._ready = False
        self._use_tokenizers_lib = True

    async def initialize(self) -> bool:
        """加载模型。返回 True 表示就绪，False 表示模型不可用（降级）。"""
        if self._ready:
            return True
        model_path = Path(self.model_dir)
        if not model_path.exists():
            logger.warning(f"[onnx_reranker] 模型目录不存在，降级跳过: {model_path}")
            return False
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model)
            self._ready = True
            logger.info(f"[onnx_reranker] 模型就绪: {self.model_dir}")
            return True
        except Exception as e:
            logger.warning(f"[onnx_reranker] 模型加载失败，降级跳过: {e}")
            return False

    def _load_model(self) -> None:
        """加载模型 — 优先 ONNX，PyTorch 用 optimum 自动转换"""
        model_path = Path(self.model_dir)

        # 方式 1: 原生 ONNX 文件
        onnx_file = model_path / "onnx" / "model.onnx"
        if not onnx_file.exists():
            onnx_file = model_path / "model.onnx"

        if onnx_file.exists():
            import onnxruntime as ort
            from tokenizers import Tokenizer
            logger.info(f"[onnx_reranker] ONNX 模型加载: {onnx_file}")
            self._session = ort.InferenceSession(
                str(onnx_file), providers=["CPUExecutionProvider"],
            )
            tokenizer_file = model_path / "tokenizer.json"
            if tokenizer_file.exists():
                self._tokenizer = Tokenizer.from_file(str(tokenizer_file))
                self._tokenizer.enable_truncation(max_length=_MAX_LENGTH)
                pad_id = self._tokenizer.token_to_id("[PAD]") or self._tokenizer.token_to_id("<pad>") or 0
                self._tokenizer.enable_padding(pad_id=pad_id)
                self._use_tokenizers_lib = True
            else:
                from transformers import AutoTokenizer
                self._tokenizer = AutoTokenizer.from_pretrained(str(model_path))
                self._use_tokenizers_lib = False
            self._use_optimum = False
            logger.info("[onnx_reranker] ONNX 模型加载完成")
            return

        # 方式 2: PyTorch 模型，用 optimum 自动转 ONNX 推理
        safetensors = list(model_path.glob("*.safetensors")) + list(model_path.glob("*.bin"))
        if safetensors:
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer
            logger.info(f"[onnx_reranker] PyTorch 模型，optimum 自动 ONNX 转换: {model_path}")
            self._optimum_model = ORTModelForSequenceClassification.from_pretrained(
                str(model_path), export=True, provider="CPUExecutionProvider",
            )
            self._tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            self._use_optimum = True
            logger.info("[onnx_reranker] optimum 模型加载完成")
            return

        raise FileNotFoundError(f"找不到模型文件: {model_path}")

    async def rerank(self, query: str, candidates: List[str]) -> List[float]:
        """对候选文本做 pair-wise 精排

        Args:
            query: 查询文本
            candidates: 候选文本列表

        Returns:
            每个 candidate 的相关性分数 [0, 1]
        """
        if not self._ready:
            ok = await self.initialize()
            if not ok:
                return [0.5] * len(candidates)  # 降级：返回中性分数
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._rerank_sync, query, candidates)

    def _rerank_sync(self, query: str, candidates: List[str]) -> List[float]:
        """同步推理（线程池调用）"""
        if not candidates:
            return []

        # 过滤空文本，记录原始索引以还原顺序
        indexed = [(i, c) for i, c in enumerate(candidates) if c and c.strip()]
        if not indexed:
            return [0.5] * len(candidates)

        orig_indices = [i for i, _ in indexed]
        filtered_candidates = [c for _, c in indexed]

        # ── optimum 模式: 直接用 transformers 推理 ──
        if getattr(self, '_use_optimum', False):
            import torch
            pairs = [(query, c[:_MAX_LENGTH]) for c in filtered_candidates]
            encoded = self._tokenizer(
                [q for q, c in pairs], [c for q, c in pairs],
                padding=True, truncation=True, max_length=_MAX_LENGTH, return_tensors="pt",
            )
            with torch.no_grad():
                outputs = self._optimum_model(**encoded)
            logits = outputs.logits.numpy()
            if logits.ndim == 2 and logits.shape[1] >= 2:
                scores = logits[:, -1].astype(np.float64)
            elif logits.ndim == 2 and logits.shape[1] == 1:
                scores = logits[:, 0].astype(np.float64)
            else:
                scores = logits.flatten().astype(np.float64)
            filtered_scores = (1.0 / (1.0 + np.exp(-scores))).tolist()
            # 还原原始顺序，空文本补 0.5
            result = [0.5] * len(candidates)
            for idx, score in zip(orig_indices, filtered_scores):
                result[idx] = score
            return result

        # ── ONNX 模式: onnxruntime 推理 ──
        pairs = [(query, c[:_MAX_LENGTH]) for c in filtered_candidates]

        if self._use_tokenizers_lib:
            encodings = self._tokenizer.encode_batch(pairs)
            input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
            attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
            token_type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)
        else:
            texts_a = [q for q, c in pairs]
            texts_b = [c for q, c in pairs]
            encoded = self._tokenizer(
                texts_a, texts_b,
                padding=True, truncation=True,
                max_length=_MAX_LENGTH, return_tensors="np",
            )
            input_ids = encoded["input_ids"].astype(np.int64)
            attention_mask = encoded["attention_mask"].astype(np.int64)
            token_type_ids = encoded.get("token_type_ids")
            if token_type_ids is not None:
                token_type_ids = token_type_ids.astype(np.int64)

        inputs = {}
        for inp in self._session.get_inputs():
            name = inp.name
            if name == "input_ids":
                inputs[name] = input_ids
            elif name == "attention_mask":
                inputs[name] = attention_mask
            elif name == "token_type_ids" and token_type_ids is not None:
                inputs[name] = token_type_ids

        outputs = self._session.run(None, inputs)
        logits = outputs[0]

        if logits.ndim == 2 and logits.shape[1] >= 2:
            scores = logits[:, -1].astype(np.float64)
        elif logits.ndim == 2 and logits.shape[1] == 1:
            scores = logits[:, 0].astype(np.float64)
        else:
            scores = logits.flatten().astype(np.float64)

        sigmoid_scores = 1.0 / (1.0 + np.exp(-scores))
        filtered_scores = sigmoid_scores.tolist()
        # 还原原始顺序，空文本补 0.5
        result = [0.5] * len(candidates)
        for idx, score in zip(orig_indices, filtered_scores):
            result[idx] = score
        return result

    @property
    def is_ready(self) -> bool:
        return self._ready


# ── 全局单例 ──────────────────────────────────────────────

async def get_onnx_reranker_service(model_dir: str = "") -> Optional[OnnxRerankerService]:
    """获取全局单例。模型不可用时返回 None（降级）。"""
    global _instance
    if _instance is not None:
        if _instance.is_ready:
            return _instance
        # 之前尝试过但失败了，允许重试
        return None

    async with _get_init_lock():
        if _instance is not None:
            return _instance if _instance.is_ready else None
        svc = OnnxRerankerService(model_dir=model_dir)
        ok = await svc.initialize()
        if ok:
            _instance = svc
            return svc
        # 不缓存失败实例，允许下次重试
        return None
