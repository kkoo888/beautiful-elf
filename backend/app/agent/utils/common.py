"""公共工具函数 — 无业务依赖，可被所有模块复用"""
from typing import List, Dict, Union
import json
import time

from app.core.logging import get_logger
from app.agent.state import _content_blocks_to_str

logger = get_logger(__name__)

# ── 通用常量 ─────────────────────────────────────────────
MAX_MESSAGE_WINDOW = 30


# ── 错误契约 ──────────────────────────────────────────────

class CircuitBreaker:
    """简单熔断器 — 防止工具级联故障

    三态：closed（正常）→ open（熔断，快速失败）→ half-open（试探恢复）
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self._failure_count: Dict[str, int] = {}
        self._last_failure_time: Dict[str, float] = {}
        self._state: Dict[str, str] = {}  # tool_name -> state
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

    def is_available(self, tool_name: str) -> bool:
        """工具是否可用"""
        state = self._state.get(tool_name, "closed")
        if state == "closed":
            return True
        if state == "open":
            elapsed = time.time() - self._last_failure_time.get(tool_name, 0)
            if elapsed >= self._recovery_timeout:
                self._state[tool_name] = "half-open"
                logger.info(f"[circuit_breaker] {tool_name} 进入 half-open 状态，试探恢复")
                return True
            return False
        return True

    def record_success(self, tool_name: str):
        self._failure_count[tool_name] = 0
        self._state[tool_name] = "closed"

    def record_failure(self, tool_name: str):
        count = self._failure_count.get(tool_name, 0) + 1
        self._failure_count[tool_name] = count
        self._last_failure_time[tool_name] = time.time()
        if count >= self._threshold:
            self._state[tool_name] = "open"
            logger.warning(f"[circuit_breaker] {tool_name} 熔断！连续失败 {count} 次，{self._recovery_timeout}s 后恢复")

    def get_state(self, tool_name: str) -> str:
        return self._state.get(tool_name, "closed")


# 全局熔断器实例
_circuit_breaker = CircuitBreaker()


class ErrorContract:
    @staticmethod
    def retryable(tool_name: str, error: str, attempt: int) -> dict:
        return {"success": False, "error": {"code": "TOOL_TRANSIENT_ERROR", "message": f"工具 {tool_name} 暂时不可用: {error}", "retryable": True, "user_facing": False, "attempt": attempt}}

    @staticmethod
    def user_facing(tool_name: str, error: str, user_tip: str) -> dict:
        return {"success": False, "error": {"code": "TOOL_USER_ERROR", "message": f"工具 {tool_name}: {error}", "retryable": False, "user_facing": True, "user_tip": user_tip}}

    @staticmethod
    def escalate(tool_name: str, error: str) -> dict:
        return {"success": False, "error": {"code": "TOOL_SYSTEM_ERROR", "message": f"工具 {tool_name} 系统异常: {error}", "retryable": False, "user_facing": False, "escalate": True}}


# ── 消息工具 ──────────────────────────────────────────────

def _content_to_str(content) -> str:
    """将消息 content 统一转为字符串。委托给 state._content_blocks_to_str。"""
    return _content_blocks_to_str(content)


def _build_message_dicts(state) -> List[dict]:
    result = []
    for m in state.get("messages", []):
        if isinstance(m, dict):
            result.append({"role": m.get("role", "user"), "content": _content_to_str(m.get("content", ""))})
        else:
            result.append({"role": getattr(m, "role", "user"), "content": _content_to_str(getattr(m, "content", ""))})
    return result


def _trim_messages(messages: list, max_count: int) -> list:
    if len(messages) <= max_count:
        return messages
    trimmed = messages[-max_count:]
    logger.info(f"[message_trim] {len(messages)} → {len(trimmed)} 条消息")
    return trimmed


def _format_tool_result_json(result: Union[str, dict, list, tuple, None], tool_name: str, last_error: str = None) -> str:
    """格式化工具结果为 JSON 字符串（MCP 规范: content[text] 序列化 JSON）"""
    if result is None:
        return json.dumps(ErrorContract.retryable(tool_name, last_error or "未知错误", attempt=2), ensure_ascii=False)
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, default=str)
    if isinstance(result, (list, tuple)):
        return json.dumps(result, ensure_ascii=False, default=str)
    return json.dumps({"result": str(result)}, ensure_ascii=False)
