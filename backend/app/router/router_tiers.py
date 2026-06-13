"""Canonical router tier identifiers and legacy aliases.

本地化自 opensquilla.router_tiers，消除外部依赖。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

TEXT_TIERS: tuple[str, str, str, str] = ("c0", "c1", "c2", "c3")
DEFAULT_TEXT_TIER = "c1"
HIGHEST_TEXT_TIER = "c3"
IMAGE_TIER = "image_model"

LEGACY_TEXT_TIER_ALIASES: dict[str, str] = {
    "t0": "c0",
    "t1": "c1",
    "t2": "c2",
    "t3": "c3",
}

ROUTE_CLASS_TO_TIER: dict[str, str] = {
    "R0": "c0",
    "R1": "c1",
    "R2": "c2",
    "R3": "c3",
}
TIER_TO_ROUTE_CLASS: dict[str, str] = {tier: route for route, tier in ROUTE_CLASS_TO_TIER.items()}


def normalize_text_tier(value: object) -> str | None:
    if value is None:
        return None
    tier = str(value).strip().lower()
    if not tier:
        return None
    if tier in TEXT_TIERS:
        return tier
    return LEGACY_TEXT_TIER_ALIASES.get(tier)


def normalize_tier_id(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw == IMAGE_TIER:
        return IMAGE_TIER
    return normalize_text_tier(raw)
