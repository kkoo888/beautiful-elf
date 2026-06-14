"""InjectionGuard — 检索注入防御

所有外部内容（RAG 检索结果、工具输出、网页抓取）用 <untrusted> 标签包裹，
内部做 XML escape，防止 LLM 把外部内容当指令执行。
"""
from __future__ import annotations

import re

# ── XML 转义 ──────────────────────────────────────────────

_XML_ESCAPE_TABLE = str.maketrans({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&apos;",
})


def xml_escape(text: str) -> str:
    """XML 转义，防止注入标签"""
    return text.translate(_XML_ESCAPE_TABLE)


# ── 核心函数 ──────────────────────────────────────────────

def wrap_untrusted(content: str, source: str = "") -> str:
    """将外部内容包裹在 <untrusted> 标签中

    Args:
        content: 外部内容（RAG 检索结果、工具输出等）
        source: 来源标识（如 "rag:doc_id=123"）

    Returns:
        包裹后的安全内容

    示例:
        >>> wrap_untrusted("这是一段检索结果", source="rag:doc_id=42")
        "<untrusted source='rag:doc_id=42'>这是一段检索结果</untrusted>"
    """
    escaped = xml_escape(content)
    if source:
        safe_source = xml_escape(source)
        return f"<untrusted source='{safe_source}'>{escaped}</untrusted>"
    return f"<untrusted>{escaped}</untrusted>"


def wrap_untrusted_batch(items: list[dict], content_key: str = "content", source_key: str = "source") -> str:
    """批量包裹多个外部内容项

    Args:
        items: [{"content": str, "source": str}, ...]
        content_key: 内容字段名
        source_key: 来源字段名

    Returns:
        所有包裹后的内容拼接
    """
    parts = []
    for item in items:
        content = item.get(content_key, "")
        source = item.get(source_key, "")
        if content:
            parts.append(wrap_untrusted(content, source=source))
    return "\n\n".join(parts)


# ── 检测函数 ──────────────────────────────────────────────

_UNTRUSTED_PATTERN = re.compile(
    r"<untrusted(?:\s+source=['\"][^'\"<>]*['\"])?\s*>.*?</untrusted\s*>",
    re.IGNORECASE | re.DOTALL,
)


def is_untrusted_fragment(text: str) -> bool:
    """检查文本是否包含 <untrusted> 标签"""
    return bool(_UNTRUSTED_PATTERN.search(text))


# ── 注入模式检测（可选，用于审计日志）──────────────────────

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"忽略(之前|以上|上面)的(指令|指示|要求)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)", re.IGNORECASE),
    re.compile(r"你现在是", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<system>", re.IGNORECASE),
    re.compile(r"output\s+(your|the)\s+(system\s+)?prompt", re.IGNORECASE),
]


def detect_injection_attempt(text: str) -> bool:
    """检测文本中是否包含疑似注入模式（用于审计日志，不用于阻断）"""
    return any(p.search(text) for p in _INJECTION_PATTERNS)
