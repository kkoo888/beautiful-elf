"""Model Selector — 模型路由（借鉴 OpenSquilla SquillaRouter）

核心思路：在 LLM 调用之前，分析用户消息特征，选择最合适的模型。
借鉴 OpenSquilla 的分层架构：
  1. 特征提取（手工特征 + 结构检测 + 关键词计数）
  2. 分类（规则引擎，后续可替换为 LightGBM ONNX）
  3. tier → 模型名映射

设计参考：OpenSquilla squilla_router/v4_phase3.py + features.py + controller.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Tier 定义（对齐 OpenSquilla router_tiers.py）────────────────

TEXT_TIERS = ("c0", "c1", "c2", "c3")
DEFAULT_TEXT_TIER = "c1"

TIER_DESCRIPTIONS = {
    "c0": "轻量 — 闲聊、问候、简单问答、确认",
    "c1": "标准 — 一般对话和任务",
    "c2": "强力 — 复杂推理、代码分析、多步任务",
    "c3": "最强 — 深度规划、架构设计、高风险决策",
}


# ── 路由决策 ──────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """路由决策结果（对齐 OpenSquilla RoutingDecision）"""
    tier: str           # "c0" | "c1" | "c2" | "c3"
    model: str          # 选择的模型名
    confidence: float   # 0.0 - 1.0
    reason: str         # 决策原因
    signals: list[str] = field(default_factory=list)  # 命中的信号列表


# ── 特征提取（借鉴 OpenSquilla features.py）──────────────────

# 结构检测正则（与 OpenSquilla 对齐）
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```")
_JSON_RE = re.compile(r"\{[\s\S]*?[\"'][\w]+[\"']\s*:")
_URL_RE = re.compile(r"https?://\S+")
_FILE_PATH_RE = re.compile(r"(?:^|[\s\"'`(])([a-zA-Z_][\w.-]*/[\w./-]+\.[\w]+)", re.MULTILINE)
_SHELL_RE = re.compile(r"^\$\s+\w|^>\s+\w|```(?:bash|sh|shell)", re.MULTILINE)
_TRACEBACK_RE = re.compile(r"Traceback \(most recent|stderr:|\.py\", line \d+")
_BULLET_RE = re.compile(r"^[\s]*[-*]\s", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^[\s]*\d+[.)]\s", re.MULTILINE)

# 关键词列表（与 OpenSquilla 对齐）
_DEBUG_KW = ["error", "bug", "exception", "traceback", "failed", "root cause",
             "报错", "根因", "修复", "stack trace", "debug"]
_RESEARCH_KW = ["调研", "research", "对比", "compare", "survey", "分析报告",
                "competitive analysis", "综述"]
_ARCH_KW = ["architecture", "架构", "重构", "refactor", "monorepo", "codebase",
            "module", "dependency", "微服务", "分库分表", "高可用", "分布式"]
_PLANNING_KW = ["plan", "规划", "roadmap", "设计方案", "workflow", "pipeline",
                "步骤", "step by step", "第.*步", "首先.*然后"]
_HIGH_RISK_KW = ["deploy", "rollback", "migration", "delete", "overwrite",
                 "production", "生产", "部署", "删除", "客户", "法务", "财务"]
_TEACHING_KW = ["how does", "explain", "what is", "why does", "how to",
                "教我", "解释", "为什么", "怎么", "是什么", "介绍", "说明"]
_IMPLEMENT_KW = ["implement", "write function", "write a", "create a",
                 "写个", "实现", "用法", "帮我写", "生成代码", "写一个", "编写"]
_STRICT_FMT_KW = ["JSON", "YAML", "CSV", "schema", "只返回", "不要解释",
                  "按格式", "only return", "no explanation"]
_CONSTRAINT_KW = ["必须", "不能", "不要", "只能", "must", "shall",
                  "required", "forbidden", "不允许", "至少", "最多"]
_TESTING_KW = ["写.*测试", "单元测试", "集成测试", "test case", "TDD", "BDD"]
_REVIEW_KW = ["review", "审查", "审计", "code review", "安全审计"]


def _keyword_count(text: str, keywords: list[str]) -> int:
    """统计关键词命中数（与 OpenSquilla 对齐）"""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def _char_type_ratios(text: str) -> tuple[float, float, float]:
    """中/英/代码字符比例（与 OpenSquilla 对齐）"""
    if not text:
        return 0.0, 0.0, 0.0
    n = len(text)
    zh = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    en = sum(1 for c in text if c.isascii() and c.isalpha())
    code_chars = sum(1 for c in text if c in "{}[]();=<>|&!@#$%^*~`\\")
    return zh / n, en / n, code_chars / n


@dataclass
class MessageFeatures:
    """消息特征（简化版 OpenSquilla hand-crafted features）"""
    # 文本统计
    char_count: int = 0
    word_count: int = 0
    line_count: int = 0
    zh_ratio: float = 0.0
    en_ratio: float = 0.0
    code_ratio: float = 0.0

    # 结构检测
    has_code_block: bool = False
    has_json: bool = False
    has_url: bool = False
    has_file_path: bool = False
    has_shell: bool = False
    has_traceback: bool = False
    bullet_count: int = 0
    numbered_count: int = 0

    # 关键词计数
    debug_kw_count: int = 0
    research_kw_count: int = 0
    arch_kw_count: int = 0
    planning_kw_count: int = 0
    high_risk_kw_count: int = 0
    teaching_kw_count: int = 0
    implement_kw_count: int = 0
    strict_fmt_kw_count: int = 0
    constraint_kw_count: int = 0
    testing_kw_count: int = 0
    review_kw_count: int = 0

    # 历史信号
    history_turn_count: int = 0
    has_tool_history: bool = False


def extract_features(text: str, history: list[dict] | None = None) -> MessageFeatures:
    """提取消息特征（借鉴 OpenSquilla features.py）

    与 OpenSquilla 的区别：
      - OpenSquilla 用 51 维手工特征 + 100 维 TF-IDF + 64 维 BGE
      - 我们先用简化版（~25 维），后续可接入 ML 模型
    """
    clean = text.strip()
    zh_ratio, en_ratio, code_ratio = _char_type_ratios(clean)

    features = MessageFeatures(
        # 文本统计
        char_count=len(clean),
        word_count=len(clean.split()),
        line_count=clean.count("\n") + 1,
        zh_ratio=zh_ratio,
        en_ratio=en_ratio,
        code_ratio=code_ratio,

        # 结构检测
        has_code_block=bool(_CODE_BLOCK_RE.search(clean)),
        has_json=bool(_JSON_RE.search(clean)),
        has_url=bool(_URL_RE.search(clean)),
        has_file_path=bool(_FILE_PATH_RE.search(clean)),
        has_shell=bool(_SHELL_RE.search(clean)),
        has_traceback=bool(_TRACEBACK_RE.search(clean)),
        bullet_count=len(_BULLET_RE.findall(clean)),
        numbered_count=len(_NUMBERED_RE.findall(clean)),

        # 关键词计数
        debug_kw_count=_keyword_count(clean, _DEBUG_KW),
        research_kw_count=_keyword_count(clean, _RESEARCH_KW),
        arch_kw_count=_keyword_count(clean, _ARCH_KW),
        planning_kw_count=_keyword_count(clean, _PLANNING_KW),
        high_risk_kw_count=_keyword_count(clean, _HIGH_RISK_KW),
        teaching_kw_count=_keyword_count(clean, _TEACHING_KW),
        implement_kw_count=_keyword_count(clean, _IMPLEMENT_KW),
        strict_fmt_kw_count=_keyword_count(clean, _STRICT_FMT_KW),
        constraint_kw_count=_keyword_count(clean, _CONSTRAINT_KW),
        testing_kw_count=_keyword_count(clean, _TESTING_KW),
        review_kw_count=_keyword_count(clean, _REVIEW_KW),

        # 历史信号
        history_turn_count=len(history) if history else 0,
        has_tool_history=_check_tool_history(history),
    )
    return features


def _check_tool_history(history: list[dict] | None) -> bool:
    """检查历史中是否有工具调用"""
    if not history:
        return False
    for msg in history[-3:]:
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, str) and ("tool_call" in content or "工具" in content):
                return True
    return False


# ── 分类器（规则引擎，后续可替换为 LightGBM）────────────────

def classify_from_features(features: MessageFeatures) -> tuple[str, float, str, list[str]]:
    """基于特征分类（规则引擎版）

    对齐 OpenSquilla 的分类逻辑：
      1. 规则快筛（c0 闲聊 / c3 高风险）
      2. 信号匹配（c2 复杂任务）
      3. 特征打分（c0/c1/c2/c3）

    后续升级路径：
      - 收集线上数据 → 训练 LightGBM → 打包 ONNX
      - 替换此函数为 model.predict(features_390)
    """
    f = features
    signals: list[str] = []

    # ── Layer 1: c0 快筛（闲聊/问候/确认）──
    if f.char_count < 20 and f.debug_kw_count == 0 and f.arch_kw_count == 0:
        if f.teaching_kw_count == 0 and f.implement_kw_count == 0:
            # 短消息、无复杂关键词 → 可能是 c0
            if f.char_count < 10:
                signals.append("short_message")
                return "c0", 0.8, "short_message", signals

    # ── Layer 2: c3 高风险信号 ──
    if f.high_risk_kw_count >= 2:
        signals.append(f"high_risk:{f.high_risk_kw_count}")
        return "c3", 0.9, "high_risk", signals

    # ── Layer 3: c2 复杂任务信号 ──
    c2_score = 0.0
    c2_reasons = []

    # 代码相关
    if f.has_code_block:
        c2_score += 0.3
        c2_reasons.append("code_block")
    if f.debug_kw_count >= 2:
        c2_score += 0.25
        c2_reasons.append(f"debug:{f.debug_kw_count}")
    if f.testing_kw_count >= 1:
        c2_score += 0.2
        c2_reasons.append("testing")
    if f.review_kw_count >= 1:
        c2_score += 0.2
        c2_reasons.append("review")

    # 架构相关
    if f.arch_kw_count >= 2:
        c2_score += 0.3
        c2_reasons.append(f"arch:{f.arch_kw_count}")
    if f.planning_kw_count >= 2:
        c2_score += 0.25
        c2_reasons.append(f"planning:{f.planning_kw_count}")
    if f.research_kw_count >= 1:
        c2_score += 0.2
        c2_reasons.append("research")

    # 结构复杂度
    if f.char_count > 500:
        c2_score += 0.2
        c2_reasons.append("long_input")
    if f.line_count > 10:
        c2_score += 0.15
        c2_reasons.append(f"multiline:{f.line_count}")
    if f.has_traceback:
        c2_score += 0.2
        c2_reasons.append("traceback")
    if f.has_json or f.has_shell:
        c2_score += 0.15
        c2_reasons.append("structured_input")

    # 历史信号
    if f.history_turn_count > 6:
        c2_score += 0.1
        c2_reasons.append(f"deep_history:{f.history_turn_count}")
    if f.has_tool_history:
        c2_score += 0.15
        c2_reasons.append("tool_history")

    # 约束/格式要求
    if f.strict_fmt_kw_count >= 1:
        c2_score += 0.15
        c2_reasons.append("strict_format")
    if f.constraint_kw_count >= 2:
        c2_score += 0.1
        c2_reasons.append(f"constraints:{f.constraint_kw_count}")

    if c2_score >= 0.5:
        signals.extend([f"c2:{r}" for r in c2_reasons])
        tier = "c3" if c2_score >= 0.8 else "c2"
        return tier, min(c2_score, 1.0), "+".join(c2_reasons[:3]), signals

    # ── Layer 4: c1 标准任务 ──
    if f.implement_kw_count >= 1 or f.teaching_kw_count >= 1:
        signals.append("standard_task")
        return "c1", 0.7, "standard_task", signals

    if f.char_count > 100:
        signals.append("medium_input")
        return "c1", 0.6, "medium_input", signals

    # ── Layer 5: 默认 c0 ──
    signals.append("default")
    return "c0", 0.5, "default", signals


# ── Model Selector（主类）───────────────────────────────────

class ModelSelector:
    """模型选择器（借鉴 OpenSquilla ModelSelector + SquillaRouter）

    核心职责：
      1. 维护 tier → 模型名映射
      2. 接收用户消息 → 提取特征 → 分类 → 返回模型名
      3. 支持运行时更新映射（热切换）

    与 OpenSquilla 的区别：
      - OpenSquilla 用 LightGBM ONNX 模型分类（390 维特征）
      - 我们先用规则引擎（~25 维特征），后续可接入 ML
      - OpenSquilla 通过 override_model + resolve 切换 provider
      - 我们通过 get_llm(model_name) 返回对应的 LLM 实例
    """

    def __init__(self, default_model: str = ""):
        self._default_model = default_model
        self._tier_models: dict[str, str] = {}  # tier → model_name
        self._llm_registry: dict[str, object] = {}  # model_name → LLM instance

    def register_tier(self, tier: str, model_name: str):
        """注册 tier → 模型名映射"""
        self._tier_models[tier] = model_name
        logger.info(f"[model_selector] 注册 {tier} → {model_name}")

    def register_llm(self, model_name: str, llm: object):
        """注册模型名 → LLM 实例映射"""
        self._llm_registry[model_name] = llm
        logger.info(f"[model_selector] 注册 LLM: {model_name}")

    def get_llm(self, model_name: str) -> object:
        """按模型名获取 LLM 实例

        降级策略：指定模型 → 默认模型 → 第一个可用的
        """
        llm = self._llm_registry.get(model_name)
        if llm:
            return llm

        # 降级到默认模型
        if self._default_model:
            llm = self._llm_registry.get(self._default_model)
            if llm:
                logger.warning(f"[model_selector] {model_name} 未注册，降级到 {self._default_model}")
                return llm

        # 降级到第一个可用的
        if self._llm_registry:
            first_name, first_llm = next(iter(self._llm_registry.items()))
            logger.warning(f"[model_selector] {model_name} 未注册，降级到 {first_name}")
            return first_llm

        raise RuntimeError(f"[model_selector] 没有任何已注册的 LLM（请求 model={model_name}）")

    def classify(
        self,
        user_message: str,
        history: list[dict] | None = None,
    ) -> RoutingDecision:
        """分类用户消息 → 选择模型

        流程（对齐 OpenSquilla）：
          1. 提取特征
          2. 分类得到 tier
          3. tier → 模型名
          4. 返回 RoutingDecision

        Args:
            user_message: 用户输入文本
            history: 对话历史（可选）

        Returns:
            RoutingDecision(tier, model, confidence, reason, signals)
        """
        if not user_message or not user_message.strip():
            model = self._tier_models.get(DEFAULT_TEXT_TIER, self._default_model)
            return RoutingDecision(
                tier=DEFAULT_TEXT_TIER, model=model,
                confidence=1.0, reason="empty_input", signals=[],
            )

        # 1. 提取特征
        features = extract_features(user_message, history)

        # 2. 分类
        tier, confidence, reason, signals = classify_from_features(features)

        # 3. tier → 模型名
        model = self._tier_models.get(tier, self._default_model)

        return RoutingDecision(
            tier=tier, model=model,
            confidence=confidence, reason=reason, signals=signals,
        )

    @property
    def registered_tiers(self) -> list[str]:
        """返回所有已注册的 tier 列表"""
        return list(self._tier_models.keys())

    @property
    def registered_models(self) -> list[str]:
        """返回所有已注册的模型名列表"""
        return list(self._llm_registry.keys())
