"""DecisionLog — 结构化决策日志

每轮对话记录 RAG 检索决策、路由决策、token 用量等结构化信息。
JSONL 格式，便于后续分析和评估。
"""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class RAGDecision:
    """RAG 检索决策记录"""
    strategy: str = "hybrid"          # lexical | semantic | hybrid
    bm25_hits: int = 0                # BM25 返回结果数
    vector_hits: int = 0              # 向量返回结果数
    rrf_fused: int = 0                # RRF 融合后结果数
    reranked: int = 0                 # Rerank 后结果数
    budget_trimmed: int = 0           # Budget 裁剪掉的结果数
    context_chars: int = 0            # 最终上下文字符数
    latency_ms: int = 0               # 检索耗时


@dataclass
class RouterDecision:
    """路由决策记录"""
    routed_model: str = ""            # 实际使用的模型
    baseline_model: str = ""          # 基线模型
    routing_confidence: float = 0.0   # 路由置信度
    tier: str = ""                    # 路由 tier


@dataclass
class DecisionEntry:
    """单轮决策日志"""
    timestamp: str = ""
    session_id: str = ""
    turn_id: str = ""
    query_hash: str = ""              # query 的 SHA256（不记录原文）
    rag: Optional[RAGDecision] = None
    router: Optional[RouterDecision] = None
    token_usage: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        data = asdict(self)
        # 去掉 None 值
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data, ensure_ascii=False, default=str)


class DecisionLogger:
    """决策日志记录器

    用法:
        logger = DecisionLogger(log_dir="/path/to/logs")
        entry = DecisionEntry(
            timestamp=datetime.utcnow().isoformat(),
            session_id="abc",
            rag=RAGDecision(strategy="hybrid", bm25_hits=10, vector_hits=8),
        )
        logger.log(entry)
    """

    def __init__(self, log_dir: str = "logs"):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def _log_file(self) -> Path:
        """当天的日志文件"""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        return self._log_dir / f"decisions-{date_str}.jsonl"

    def log(self, entry: DecisionEntry):
        """写入一条决策日志（best-effort，不阻塞主流程）"""
        try:
            with open(self._log_file(), "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception as exc:
            log.debug(f"[decision_log] 写入失败: {exc}")

    @staticmethod
    def hash_query(query: str) -> str:
        """对 query 做 SHA256 哈希（不记录原文，保护隐私）"""
        return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
