"""消息清理器 — 畸形 JSON 修复 + Unicode 代理处理（对标 Hermes Agent）

解决本地模型（Ollama/MiMo）常见的输出质量问题：
- 畸形 JSON 工具参数（尾逗号、未闭合括号、控制字符）
- Unicode 代理对（导致 json.dumps 崩溃）
- 非 ASCII 字符（极端编码环境降级）
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Unicode 代理对 ────────────────────────────────────────
_SURROGATE_RE = re.compile(r'[\ud800-\udfff]')


def sanitize_surrogates(text: str) -> str:
    """替换无效 Unicode 代理对为 U+FFFD（替换字符）

    代理对在 UTF-8 中无效，会导致 json.dumps() 崩溃。
    MiMo/Kimi/GLM 等模型的 reasoning 输出中可能出现。
    """
    if _SURROGATE_RE.search(text):
        return _SURROGATE_RE.sub('\ufffd', text)
    return text


def sanitize_messages(messages: list) -> bool:
    """清理消息列表中的代理对（就地修改）

    遍历所有字符串字段：content、name、tool_calls、reasoning 等。
    返回 True 表示有替换发生。
    """
    found = False
    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # content 字段
        content = msg.get("content")
        if isinstance(content, str) and _SURROGATE_RE.search(content):
            msg["content"] = _SURROGATE_RE.sub('\ufffd', content)
            found = True
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str) and _SURROGATE_RE.search(text):
                        part["text"] = _SURROGATE_RE.sub('\ufffd', text)
                        found = True

        # name 字段
        name = msg.get("name")
        if isinstance(name, str) and _SURROGATE_RE.search(name):
            msg["name"] = _SURROGATE_RE.sub('\ufffd', name)
            found = True

        # tool_calls 字段
        tool_calls = msg.get("tool_calls")
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function")
                if isinstance(fn, dict):
                    fn_args = fn.get("arguments")
                    if isinstance(fn_args, str) and _SURROGATE_RE.search(fn_args):
                        fn["arguments"] = _SURROGATE_RE.sub('\ufffd', fn_args)
                        found = True

        # 其他字段（reasoning_content 等）
        for key, value in msg.items():
            if key in {"content", "name", "tool_calls", "role"}:
                continue
            if isinstance(value, str) and _SURROGATE_RE.search(value):
                msg[key] = _SURROGATE_RE.sub('\ufffd', value)
                found = True
            elif isinstance(value, (dict, list)):
                if _sanitize_structure_surrogates(value):
                    found = True

    return found


def _sanitize_structure_surrogates(payload: Any) -> bool:
    """递归清理嵌套结构中的代理对"""
    found = False

    def _walk(node):
        nonlocal found
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str) and _SURROGATE_RE.search(value):
                    node[key] = _SURROGATE_RE.sub('\ufffd', value)
                    found = True
                elif isinstance(value, (dict, list)):
                    _walk(value)
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                if isinstance(value, str) and _SURROGATE_RE.search(value):
                    node[idx] = _SURROGATE_RE.sub('\ufffd', value)
                    found = True
                elif isinstance(value, (dict, list)):
                    _walk(value)

    _walk(payload)
    return found


# ── 畸形 JSON 修复 ───────────────────────────────────────

def repair_tool_arguments(raw_args: str, tool_name: str = "?") -> str:
    """尝试修复畸形的 tool_call 参数 JSON

    本地模型（Ollama/MiMo/GLM）常见的畸形输出：
    - 尾逗号: {"a": 1, "b": 2,}
    - 未闭合括号: {"a": 1
    - Python None: None
    - 控制字符: JSON 字符串内含 literal tab/newline
    - 空字符串: ""

    所有修复都记录 WARNING 日志。如果无法修复，返回 "{}" 空对象
    （比崩溃整个会话更好）。
    """
    raw_stripped = raw_args.strip() if isinstance(raw_args, str) else ""

    # 快速路径：空 → 空对象
    if not raw_stripped:
        logger.warning("sanitize: 空 tool_call 参数 → {} (%s)", tool_name)
        return "{}"

    # Python None → {}
    if raw_stripped == "None":
        logger.warning("sanitize: Python None → {} (%s)", tool_name)
        return "{}"

    # 尝试 strict=False 解析（接受控制字符）
    try:
        parsed = json.loads(raw_stripped, strict=False)
        reserialized = json.dumps(parsed, separators=(",", ":"))
        if reserialized != raw_stripped:
            logger.warning("sanitize: 修复控制字符 (%s)", tool_name)
        return reserialized
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # 常见 JSON 修复
    fixed = raw_stripped

    # 1. 移除尾逗号
    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)

    # 2. 闭合未闭合的结构
    open_curly = fixed.count('{') - fixed.count('}')
    open_bracket = fixed.count('[') - fixed.count(']')
    if open_curly > 0:
        fixed += '}' * open_curly
    if open_bracket > 0:
        fixed += ']' * open_bracket

    # 3. 移除多余的闭合括号
    for _ in range(50):
        try:
            json.loads(fixed)
            break
        except json.JSONDecodeError:
            if fixed.endswith('}') and fixed.count('}') > fixed.count('{'):
                fixed = fixed[:-1]
            elif fixed.endswith(']') and fixed.count(']') > fixed.count('['):
                fixed = fixed[:-1]
            else:
                break

    try:
        json.loads(fixed)
        logger.warning("sanitize: 修复畸形 JSON (%s): %s → %s", tool_name, raw_stripped[:80], fixed[:80])
        return fixed
    except json.JSONDecodeError:
        pass

    # 4. 转义控制字符
    try:
        escaped = _escape_control_chars(fixed)
        if escaped != fixed:
            json.loads(escaped)
            logger.warning("sanitize: 修复控制字符 JSON (%s)", tool_name)
            return escaped
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    # 最后手段：返回空对象
    logger.warning("sanitize: 无法修复 tool_call 参数 → {} (%s): %s", tool_name, raw_stripped[:80])
    return "{}"


def _escape_control_chars(raw: str) -> str:
    """转义 JSON 字符串值内的未转义控制字符"""
    out: list[str] = []
    in_string = False
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if in_string:
            if ch == "\\" and i + 1 < n:
                out.append(ch)
                out.append(raw[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
                out.append(ch)
            elif ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04x}")
            else:
                out.append(ch)
        else:
            if ch == '"':
                in_string = True
            out.append(ch)
        i += 1
    return "".join(out)
