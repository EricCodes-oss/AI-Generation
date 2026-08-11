"""Deterministic normalization without cross-platform heat conversion."""

import re
import unicodedata

from avatar_pipeline.hotspot_models import ContentNature

_HEAT_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)")
_MULTIPLIERS = {"万": 10_000.0, "w": 10_000.0, "W": 10_000.0, "亿": 100_000_000.0}
_COMMERCIAL_TERMS = ("券后", "原价", "到手价", "热销", "优惠", "购买", "促销")
_ACTIVITY_TERMS = ("平台活动", "签到活动", "挑战赛入口")
_PINNED_TERMS = ("置顶", "推荐位")


def parse_heat(value: str | int | float | None) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    compact = value.replace(",", "").replace(" ", "")
    match = _HEAT_PATTERN.search(compact)
    if not match:
        return None
    number = float(match.group(1))
    multiplier = next(
        (factor for marker, factor in _MULTIPLIERS.items() if marker in compact),
        1.0,
    )
    return number * multiplier


def normalize_platform(name: str, aliases: dict[str, str]) -> str:
    return aliases.get(name.strip(), name.strip().casefold().replace(" ", "_"))


def classify_nature(platform: str, title: str) -> ContentNature:
    text = f"{platform} {title}"
    if any(term in text for term in _COMMERCIAL_TERMS):
        return ContentNature.COMMERCIAL_PROMOTION
    if any(term in text for term in _ACTIVITY_TERMS):
        return ContentNature.PLATFORM_ACTIVITY
    if any(term in text for term in _PINNED_TERMS):
        return ContentNature.PINNED
    return ContentNature.NATURAL


def normalize_title_tokens(title: str) -> set[str]:
    cleaned = re.sub(
        r"[^0-9A-Za-z\u4e00-\u9fff]",
        "",
        unicodedata.normalize("NFKC", title),
    )
    return {cleaned[index : index + 2] for index in range(max(0, len(cleaned) - 1))}
