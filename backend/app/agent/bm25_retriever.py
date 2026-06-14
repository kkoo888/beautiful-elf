"""BM25 检索 — SQLite FTS5 + substring fallback

零外部依赖，Python 内置 sqlite3 实现。
FTS5 对单字 CJK 匹配差，substring fallback 兜底。
"""
from __future__ import annotations

import re
import sqlite3

from app.core.logging import get_logger
from app.agent.rrf_fusion import Hit

log = get_logger(__name__)


def _stringify(value) -> str:
    """防御性字符串化，防止 metadata 中的 list/dict 炸掉 SQLite"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(_stringify(v) for v in value)
    if isinstance(value, dict):
        return " ".join(f"{k} {_stringify(v)}" for k, v in value.items())
    return str(value)


class BM25Retriever:
    """SQLite FTS5 全文检索 + substring 兜底

    用法:
        retriever = BM25Retriever()
        retriever.index(chunks)  # 批量入库
        hits = retriever.search("查询文本", top_n=20)
    """

    def __init__(self):
        self._conn: sqlite3.Connection | None = None
        self._chunks: list[dict] = []
        self._indexed = False

    def _ensure_db(self):
        """懒初始化 FTS5 虚拟表"""
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts "
            "USING fts5(chunk_id, filename, content, tokenize='unicode61')"
        )

    def index(self, chunks: list[dict]):
        """批量索引文档分块

        Args:
            chunks: [{"chunk_id": str, "filename": str, "content": str, ...}, ...]
        """
        self._ensure_db()
        self._chunks = list(chunks)

        # 清空旧数据重建（FTS5 不支持 DELETE 高效批量）
        self._conn.execute("DELETE FROM chunks_fts")

        for i, chunk in enumerate(chunks):
            self._conn.execute(
                "INSERT INTO chunks_fts(rowid, chunk_id, filename, content) VALUES (?, ?, ?, ?)",
                (
                    i,
                    _stringify(chunk.get("chunk_id", str(i))),
                    _stringify(chunk.get("filename", "")),
                    _stringify(chunk.get("content", "")),
                ),
            )
        self._conn.commit()
        self._indexed = True
        log.info(f"[bm25] 索引完成: {len(chunks)} 个分块")

    def add_chunk(self, chunk: dict):
        """增量添加单个分块"""
        self._ensure_db()
        idx = len(self._chunks)
        self._chunks.append(chunk)
        self._conn.execute(
            "INSERT INTO chunks_fts(rowid, chunk_id, filename, content) VALUES (?, ?, ?, ?)",
            (
                idx,
                _stringify(chunk.get("chunk_id", str(idx))),
                _stringify(chunk.get("filename", "")),
                _stringify(chunk.get("content", "")),
            ),
        )
        self._conn.commit()

    def remove_by_doc_id(self, doc_id: str):
        """删除指定文档的所有分块"""
        if not self._indexed:
            return
        # 标记删除（FTS5 不支持高效 DELETE by column，重建更安全）
        self._chunks = [c for c in self._chunks if str(c.get("document_id")) != str(doc_id)]
        self.index(self._chunks)  # 重建索引

    def search(self, query: str, top_n: int = 20) -> list[Hit]:
        """检索：FTS5 优先，失败降级 substring"""
        if not self._indexed or not self._chunks:
            return []
        if not query or not query.strip():
            return []

        hits = self._fts_search(query, top_n)
        if not hits:
            hits = self._substring_search(query, top_n)
        return hits

    def _fts_search(self, query: str, top_n: int) -> list[Hit]:
        """FTS5 BM25 检索"""
        try:
            # 分词：提取单词 + 保留中文字符
            tokens = re.findall(r"[\w\u4e00-\u9fff]+", query.lower())
            if not tokens:
                return []

            # FTS5 查询：OR 连接各 token
            fts_query = " OR ".join(tokens)
            rows = self._conn.execute(
                "SELECT rowid, rank FROM chunks_fts "
                "WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
                (fts_query, top_n),
            ).fetchall()

            if not rows:
                return []

            # rank 是负数（越小越好），取反归一化
            raw = [(r[0], -r[1]) for r in rows if r[0] < len(self._chunks)]
            if not raw:
                return []
            max_score = max(s for _, s in raw) if raw else 1.0
            if max_score <= 0:
                max_score = 1.0

            return [
                Hit(
                    doc_id=str(self._chunks[idx].get("chunk_id", idx)),
                    rank=i + 1,
                    score=score / max_score,
                )
                for i, (idx, score) in enumerate(raw[:top_n])
            ]
        except Exception as exc:
            log.debug(f"[bm25] FTS5 检索失败: {exc}")
            return []

    def _substring_search(self, query: str, top_n: int) -> list[Hit]:
        """substring 兜底（CJK 单字 / FTS5 失败时）"""
        tokens = list(set(re.findall(r"[\w\u4e00-\u9fff]+", query.lower())))
        if not tokens:
            return []

        scored: list[tuple[int, float]] = []
        for i, chunk in enumerate(self._chunks):
            haystack = (
                f"{_stringify(chunk.get('filename', ''))} "
                f"{_stringify(chunk.get('content', ''))}"
            ).lower()
            hits = sum(1 for t in tokens if t in haystack)
            if hits > 0:
                scored.append((i, hits / len(tokens)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            Hit(
                doc_id=str(self._chunks[idx].get("chunk_id", idx)),
                rank=i + 1,
                score=score,
            )
            for i, (idx, score) in enumerate(scored[:top_n])
        ]

    @property
    def is_ready(self) -> bool:
        return self._indexed and len(self._chunks) > 0

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
