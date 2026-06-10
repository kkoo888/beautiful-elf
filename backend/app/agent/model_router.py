"""Model Router — 本地模型路由（借鉴 OpenSquilla SquillaRouter）

核心思路：在 LLM 调用之前，用本地规则 + 特征工程判断用户输入复杂度，
选择最合适的模型层级（c0/c1/c2），节省 token 成本，降低延迟。

不调 LLM API，纯本地推理，<1ms。

设计参考：OpenSquilla squilla_router/v4_phase3.py + router_tiers.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Tier 定义（对齐 OpenSquilla router_tiers.py）────────────────

TEXT_TIERS = ("c0", "c1", "c2")
DEFAULT_TIER = "c1"

TIER_DESCRIPTIONS = {
    "c0": "轻量 — 闲聊、问候、简单问答",
    "c1": "标准 — 一般对话和任务",
    "c2": "强力 — 复杂推理、代码分析、多步任务",
}


# ── 路由决策 ──────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """路由决策结果"""
    tier: str           # "c0" | "c1" | "c2"
    confidence: float   # 0.0 - 1.0
    reason: str         # 决策原因
    signals: list[str]  # 命中的信号列表


# ── 规则快筛层（<1ms）───────────────────────────────────────

# c0: 简单意图 — 问候、确认、告别、感谢
_C0_PATTERNS: list[tuple[str, str]] = [
    (r"^(你好|嗨|hi|hello|hey|您好|早上好|下午好|晚上好|早安|晚安)\s*[!！。.？?]*$", "greeting"),
    (r"^(谢谢|感谢|thanks|thank\s*you|多谢|辛苦了)\s*[!！。.？?]*$", "thanks"),
    (r"^(再见|拜拜|bye|goodbye|晚安|回头见)\s*[!！。.？?]*$", "farewell"),
    (r"^(ok|好的|明白|知道了|嗯|行|可以|没问题|收到|了解)\s*[!！。.？?]*$", "acknowledge"),
    (r"^(你是谁|你能做什么|帮助|help|what\s*can\s*you\s*do)\s*[!！。.？?]*$", "capability"),
    (r"^(对|是|不|不是|没错|是的|没有|当然|确实)\s*[!！。.？?]*$", "yes_no"),
]

# c2: 复杂任务信号
_C2_SIGNALS: list[tuple[str, str]] = [
    # 代码相关
    (r"```[\s\S]*```", "code_block"),
    (r"(重构|重写|迁移|migrate|refactor|优化.*代码|优化.*性能)", "refactor"),
    (r"(写.*测试|单元测试|集成测试|test\s*case|TDD|BDD)", "testing"),
    (r"(review|审查|审计|code\s*review|安全审计)", "review"),
    # 架构相关
    (r"(架构|微服务|分库分表|高可用|负载均衡|分布式)", "architecture"),
    (r"(设计模式|SOLID|DDD|领域驱动)", "design_pattern"),
    # 部署相关
    (r"(部署|上线|发布|CI[/\\]?CD|docker|k8s|kubernetes|容器化)", "deployment"),
    # 数据库相关
    (r"(SQL|索引优化|查询优化|慢查询|分库|分表|读写分离)", "database"),
    # 多步骤任务
    (r"(第[一二三四五六七八九十\d]步|首先.*然后.*最后|step\s*\d)", "multi_step"),
    # 长文本输入
    (r".{300,}", "long_input"),
]


def _match_patterns(text: str, patterns: list[tuple[str, str]]) -> Optional[str]:
    """匹配模式列表，返回第一个命中的信号名"""
    for pattern, signal in patterns:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            return signal
    return None


# ── 特征工程层 ────────────────────────────────────────────

def _extract_features(text: str) -> dict[str, float]:
    """提取输入文本的复杂度特征"""
    clean = text.strip()
    return {
        "length": len(clean),
        "word_count": len(clean.split()),
        "has_code": 1.0 if "```" in clean or re.search(r"(def |class |import |function |const |let |var )", clean) else 0.0,
        "has_url": 1.0 if re.search(r"https?://", clean) else 0.0,
        "question_marks": clean.count("?") + clean.count("？"),
        "exclamation": clean.count("!") + clean.count("！"),
        "line_count": clean.count("\n") + 1,
        "has_chinese": 1.0 if re.search(r"[\u4e00-\u9fff]", clean) else 0.0,
    }


def _complexity_score(features: dict[str, float]) -> float:
    """基于特征计算复杂度分数 0.0 - 1.0"""
    score = 0.0

    # 长度权重
    if features["length"] > 500:
        score += 0.35
    elif features["length"] > 200:
        score += 0.2
    elif features["length"] > 100:
        score += 0.1

    # 代码块
    if features["has_code"]:
        score += 0.3

    # URL
    if features["has_url"]:
        score += 0.1

    # 多行（结构化输入）
    if features["line_count"] > 5:
        score += 0.15

    # 问号多 = 复杂问题
    if features["question_marks"] > 2:
        score += 0.1

    return min(score, 1.0)


# ── 对话历史信号 ────────────────────────────────────────────

def _history_signal(history: list[dict] | None) -> float:
    """从对话历史推断复杂度

    - 多轮对话 → 可能是复杂任务的延续
    - 包含工具调用 → 已经在执行复杂流程
    """
    if not history:
        return 0.0

    score = 0.0
    turn_count = len(history)

    # 多轮对话
    if turn_count > 6:
        score += 0.2
    elif turn_count > 3:
        score += 0.1

    # 检查历史中是否有工具调用
    for msg in history[-3:]:  # 只看最近 3 轮
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, str) and ("tool_call" in content or "工具" in content):
                score += 0.15
                break

    return min(score, 0.3)


# ── 主路由函数 ────────────────────────────────────────────

def classify(
    user_message: str,
    history: list[dict] | None = None,
) -> RoutingDecision:
    """本地路由分类（不调 API，<1ms）

    三层判断：
    1. 规则快筛 — 问候/确认/告别 → c0
    2. 信号匹配 — 代码/架构/部署 → c2
    3. 特征打分 — 长度/结构/复杂度 → c0/c1/c2

    Args:
        user_message: 用户输入文本
        history: 对话历史（可选，用于上下文推断）

    Returns:
        RoutingDecision(tier, confidence, reason, signals)
    """
    if not user_message or not user_message.strip():
        return RoutingDecision(
            tier=DEFAULT_TIER, confidence=1.0,
            reason="empty_input", signals=[],
        )

    text = user_message.strip()
    signals: list[str] = []

    # ── Layer 1: 规则快筛 ──
    c0_signal = _match_patterns(text, _C0_PATTERNS)
    if c0_signal:
        signals.append(f"pattern:{c0_signal}")
        return RoutingDecision(
            tier="c0", confidence=0.95,
            reason="pattern_match", signals=signals,
        )

    # ── Layer 2: 复杂任务信号 ──
    c2_signal = _match_patterns(text, _C2_SIGNALS)
    if c2_signal:
        signals.append(f"complex:{c2_signal}")
        return RoutingDecision(
            tier="c2", confidence=0.85,
            reason="complexity_signal", signals=signals,
        )

    # ── Layer 3: 特征打分 ──
    features = _extract_features(text)
    complexity = _complexity_score(features)

    # 叠加历史信号
    hist_score = _history_signal(history)
    total_score = min(complexity + hist_score, 1.0)

    if total_score >= 0.5:
        signals.append(f"score:{total_score:.2f}")
        return RoutingDecision(
            tier="c2", confidence=0.7,
            reason="high_complexity_score", signals=signals,
        )
    elif total_score >= 0.25:
        signals.append(f"score:{total_score:.2f}")
        return RoutingDecision(
            tier="c1", confidence=0.7,
            reason="medium_complexity_score", signals=signals,
        )
    else:
        signals.append(f"score:{total_score:.2f}")
        return RoutingDecision(
            tier="c0", confidence=0.6,
            reason="low_complexity_score", signals=signals,
        )
