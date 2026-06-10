"""Model Selector — ML 模型路由。"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from app.core.logging import get_logger
from app.router.controller import (
    ROUTE_CLASS_TO_TIER,
    TEXT_TIERS,
    DEFAULT_TEXT_TIER,
    TIER_ORDER,
    get_prompt_hint,
    select_localized_prompt_hint,
    thinking_mode_to_level,
)

logger = get_logger(__name__)

_DEFAULT_BUNDLE_DIR = Path(__file__).resolve().parent / "models" / "v4.2_phase3_inference"


@dataclass
class RoutingDecision:
    """路由决策结果。"""
    tier: str
    model: str
    route_class: str
    confidence: float
    reason: str
    thinking_mode: str = "T1"
    prompt_policy: str = "P1"
    prompt_hint: str = ""
    difficulty_score: float = 0.0
    margin: float = 0.0
    flags: dict = field(default_factory=dict)
    probabilities: dict = field(default_factory=dict)
    signals: list[str] = field(default_factory=list)
    source: str = "rules"
    model_version: str = "unknown"
    elapsed_ms: int = 0


class _V4Phase3MLStrategy:
    """V4 Phase 3 ML 推理策略。"""

    def __init__(self, bundle_dir: Path, config: dict):
        self.bundle_dir = bundle_dir
        self._config = config
        self._core = None
        self._request_type = None
        self._model_version = "unknown"
        self._available = False
        try:
            self._init_runtime()
        except Exception as exc:
            logger.warning(f"[ml_strategy] ML 模型初始化失败: {exc}")

    def _init_runtime(self) -> None:
        runtime_yaml = self.bundle_dir / "router.runtime.yaml"
        if runtime_yaml.exists():
            self._config = yaml.safe_load(runtime_yaml.read_text(encoding="utf-8")) or self._config

        for name in ("version.json", "inference_manifest.json"):
            path = self.bundle_dir / name
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                for key in ("version", "model_version", "bundle_version"):
                    value = data.get(key)
                    if value:
                        self._model_version = str(value)
                        break

        required = ("runtime_src", "router.runtime.yaml")
        missing = [name for name in required if not (self.bundle_dir / name).exists()]
        if missing:
            raise FileNotFoundError(f"缺少 bundle 文件: {missing}")

        import sys
        old_path = list(sys.path)
        sys.path.insert(0, str(self.bundle_dir / "runtime_src"))
        try:
            from src.router.inference.core import InferenceCore
            from src.router.inference.types import InferenceRequest
            use_aux = bool(self._config.get("v4", {}).get("aux_head_inference", False))
            self._request_type = InferenceRequest
            self._core = InferenceCore.from_model_dir(
                str(self.bundle_dir), self._config, use_aux_head=use_aux,
            )
        finally:
            sys.path[:] = old_path

        self._available = True
        logger.info(f"[ml_strategy] ML 模型加载成功 (version={self._model_version})")

    @property
    def available(self) -> bool:
        return self._available

    def predict(self, message, history=None, history_user_texts=None):
        if not self._available or self._core is None:
            return None
        try:
            t0 = time.time()
            request = self._build_request(message, history or [], history_user_texts=history_user_texts)
            result = self._core.predict(request)
            elapsed_ms = int((time.time() - t0) * 1000)

            decision = result.decision
            route_class = str(getattr(decision, "route_class", "R1"))
            tier = ROUTE_CLASS_TO_TIER.get(route_class, DEFAULT_TEXT_TIER)
            probabilities = dict(getattr(result, "probabilities", {}) or {})
            confidence = float(probabilities.get(route_class, 0.0))
            thinking_mode = str(getattr(decision, "thinking_mode", "T1"))
            prompt_policy = str(getattr(decision, "prompt_policy", "P1"))
            difficulty = float(getattr(decision, "difficulty_score", 0.0))
            margin_val = float(getattr(decision, "margin", 0.0))
            flags_dict = dict(getattr(decision, "flags", {}) or {})

            policy_cfg = self._config.get("prompt_policies", {}).get(prompt_policy, {})
            prompt_hint = select_localized_prompt_hint(policy_cfg, message) or ""

            return {
                "route_class": route_class, "tier": tier, "confidence": confidence,
                "thinking_mode": thinking_mode, "prompt_policy": prompt_policy,
                "prompt_hint": prompt_hint, "difficulty_score": difficulty,
                "margin": margin_val, "flags": flags_dict, "probabilities": probabilities,
                "selected_model": str(getattr(decision, "selected_model", "")),
                "source": "ml_v4", "model_version": self._model_version, "elapsed_ms": elapsed_ms,
            }
        except Exception as exc:
            logger.warning(f"[ml_strategy] ML 推理失败: {exc}", exc_info=True)
            return None

    def _build_request(self, message, routing_history, *, history_user_texts=None):
        from types import SimpleNamespace
        if history_user_texts is None:
            history_texts = [str(e["text"]) for e in routing_history if e.get("text")]
        else:
            history_texts = [str(t) for t in history_user_texts if t]

        context_tokens_est = max(0, (len(message) + sum(len(t) for t in history_texts)) // 4)
        decisions = []
        for entry in routing_history:
            rc = entry.get("final_route_class") or entry.get("route_class")
            if rc:
                decisions.append(SimpleNamespace(
                    route_class=str(rc),
                    difficulty=float(entry.get("difficulty_score", 0.0) or 0.0),
                    margin=float(entry.get("margin", 0.0) or 0.0),
                ))

        return self._request_type(
            current_user_text=message,
            history_user_texts=history_texts,
            prev_route_decisions=decisions,
            context_metadata={
                "turn_index": len(routing_history),
                "history_user_turn_count": len(history_texts),
                "context_tokens_est": context_tokens_est,
                "has_code_block": "```" in message,
            },
        )


# ── 关键词 ──────────────────────────────────────────────

_DEBUG_KW = ["error", "bug", "exception", "traceback", "failed", "root cause", "报错", "根因", "修复"]
_RESEARCH_KW = ["调研", "research", "对比", "compare", "survey", "分析报告"]
_ARCH_KW = ["architecture", "架构", "重构", "refactor", "monorepo", "codebase", "module", "dependency"]
_PLANNING_KW = ["plan", "规划", "roadmap", "设计方案", "workflow", "pipeline", "步骤", "step by step"]
_HIGH_RISK_KW = ["deploy", "rollback", "migration", "delete", "overwrite", "production", "生产", "部署", "删除", "客户", "法务", "财务"]
_TEACHING_KW = ["how does", "explain", "what is", "why does", "how to", "教我", "解释", "为什么", "怎么", "是什么"]
_IMPLEMENT_KW = ["implement", "write function", "write a", "create a", "写个", "实现", "帮我写", "生成代码"]
_STRICT_FMT_KW = ["JSON", "YAML", "CSV", "schema", "只返回", "不要解释", "按格式"]
_CONSTRAINT_KW = ["必须", "不能", "不要", "只能", "must", "shall", "required", "forbidden"]


def _kw_count(text, keywords):
    t = text.lower()
    return sum(1 for kw in keywords if kw.lower() in t)


def _rule_based_classify(user_message, history=None):
    """规则引擎降级分类。"""
    text = user_message.strip()
    signals = []
    n = len(text)

    if n < 10:
        return "S", 0.8, "short_message", ["short_message"]

    if _kw_count(text, _HIGH_RISK_KW) >= 2:
        return "XL", 0.9, "high_risk", ["high_risk"]

    c2 = 0.0
    if "```" in text: c2 += 0.3
    if _kw_count(text, _DEBUG_KW) >= 2: c2 += 0.25
    if _kw_count(text, _ARCH_KW) >= 2: c2 += 0.3
    if _kw_count(text, _PLANNING_KW) >= 2: c2 += 0.25
    if n > 500: c2 += 0.2
    if len(history or []) > 6: c2 += 0.1

    if c2 >= 0.5:
        tier = "XL" if c2 >= 0.8 else "L"
        return tier, min(c2, 1.0), "complex_task", [f"c2:{c2:.2f}"]

    if _kw_count(text, _IMPLEMENT_KW) >= 1 or _kw_count(text, _TEACHING_KW) >= 1:
        return "M", 0.7, "standard_task", ["standard_task"]

    if n > 100:
        return "M", 0.6, "medium_input", ["medium_input"]

    return "S", 0.5, "default", ["default"]


# ── Model Selector ──────────────────────────────────────

class ModelSelector:
    """模型选择器。ML 推理 + 规则降级。tier 映射从 DB 注入。"""

    def __init__(self, default_model="", bundle_dir=None):
        self._default_model = default_model
        self._tier_models = {}
        self._llm_registry = {}
        self._bundle_dir = Path(bundle_dir) if bundle_dir else _DEFAULT_BUNDLE_DIR
        self._config = {}
        self._ml_strategy = None

        runtime_yaml = self._bundle_dir / "router.runtime.yaml"
        if runtime_yaml.exists():
            try:
                self._config = yaml.safe_load(runtime_yaml.read_text(encoding="utf-8")) or {}
            except Exception as e:
                logger.warning(f"[model_selector] 加载配置失败: {e}")

        try:
            self._ml_strategy = _V4Phase3MLStrategy(self._bundle_dir, self._config)
            if self._ml_strategy.available:
                logger.info("[model_selector] ML 推理就绪")
        except Exception as e:
            logger.warning(f"[model_selector] ML 初始化失败，降级到规则引擎: {e}")

    def register_tier(self, tier, model_name):
        self._tier_models[tier] = model_name

    def register_llm(self, model_name, llm):
        self._llm_registry[model_name] = llm

    def get_llm(self, model_name):
        llm = self._llm_registry.get(model_name)
        if llm:
            return llm
        if self._default_model:
            llm = self._llm_registry.get(self._default_model)
            if llm:
                return llm
        if self._llm_registry:
            return next(iter(self._llm_registry.values()))
        raise RuntimeError(f"没有已注册的 LLM（{model_name}）")

    def classify(self, user_message, history=None):
        if not user_message or not user_message.strip():
            model = self._tier_models.get(DEFAULT_TEXT_TIER, self._default_model)
            return RoutingDecision(tier=DEFAULT_TEXT_TIER, model=model, route_class="R1", confidence=1.0, reason="empty")

        t0 = time.time()

        history_user_texts = None
        if history:
            history_user_texts = [m.get("content", "") for m in history[-8:]
                                  if isinstance(m, dict) and m.get("role") == "user" and m.get("content")]

        # ML 推理
        if self._ml_strategy and self._ml_strategy.available:
            ml = self._ml_strategy.predict(user_message, history=history, history_user_texts=history_user_texts)
            if ml:
                tier = ml["tier"]
                model = self._tier_models.get(tier, self._default_model)
                return RoutingDecision(
                    tier=tier, model=model, route_class=ml["route_class"],
                    confidence=ml["confidence"], reason=f"ml:{ml['route_class']}",
                    thinking_mode=ml["thinking_mode"], prompt_policy=ml["prompt_policy"],
                    prompt_hint=ml.get("prompt_hint", ""), difficulty_score=ml["difficulty_score"],
                    margin=ml["margin"], flags=ml.get("flags", {}), probabilities=ml.get("probabilities", {}),
                    source="ml_v4", model_version=ml.get("model_version", ""),
                    elapsed_ms=int((time.time() - t0) * 1000),
                )

        # 规则降级
        tier, confidence, reason, signals = _rule_based_classify(user_message, history)
        model = self._tier_models.get(tier, self._default_model)
        route_class = {v: k for k, v in ROUTE_CLASS_TO_TIER.items()}.get(tier, "R1")
        return RoutingDecision(
            tier=tier, model=model, route_class=route_class,
            confidence=confidence, reason=reason, signals=signals,
            source="rules", elapsed_ms=int((time.time() - t0) * 1000),
        )

    @property
    def is_ml_available(self):
        return self._ml_strategy is not None and self._ml_strategy.available

    @property
    def ml_available(self):
        return self.is_ml_available

    @property
    def registered_tiers(self):
        return list(self._tier_models.keys())

    @property
    def registered_models(self):
        return list(self._llm_registry.keys())
