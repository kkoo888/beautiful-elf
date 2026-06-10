"""Router 数据类型 — 轻量级类型定义（无 ML 依赖）

分离出纯数据类型，避免 flags.py 等轻量模块被迫导入 numpy。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContextMetadata:
    """会话和工具上下文，用于上下文感知路由。"""
    turn_index: int = 0
    context_tokens_est: int = 0
    n_tools: int = 0
    tool_result_length: int = 0
    has_code_block: bool = False
    has_file_reference: bool = False
    has_url: bool = False
    has_tool_results: bool = False

    @classmethod
    def from_sample(cls, sample: dict) -> ContextMetadata:
        """从训练数据 JSONL 样本 dict 解析。"""
        sc = sample.get("session_context", {})
        tc = sample.get("tool_context", {})
        return cls(
            turn_index=sc.get("turn_index", 0),
            context_tokens_est=sc.get("context_tokens_est", 0),
            n_tools=len(tc.get("available_tools", [])),
            tool_result_length=tc.get("tool_result_length", 0),
            has_code_block=bool(sc.get("has_code_block", False)),
            has_file_reference=bool(sc.get("has_file_reference", False)),
            has_url=bool(sc.get("has_url", False)),
            has_tool_results=bool(tc.get("has_tool_results", False)),
        )
