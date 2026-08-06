"""Safe migration for legacy task and host-profile JSON."""

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from avatar_pipeline.models import AvatarLayout, HostProfile

_STATUS_MAP = {
    "created": "input_received",
    "researched": "fact_screened",
    "topic_approved": "topic_script_review",
    "script_draft": "topic_script_review",
    "script_approved": "media_planning",
    "audio_ready": "generating_anchor",
    "assets_generating": "acquiring_or_generating_media",
    "compositing": "compositing",
    "qc_failed": "compositing",
    "qc_passed": "final_review",
    "video_approved": "ready_to_publish",
}

_SAFE_HOST_DEFAULTS = {
    "layout": AvatarLayout.SEATED_STUDIO_ANCHOR.value,
    "age_range": "30-36",
    "outfit": "deep_navy_blazer_ivory_blouse",
    "mouth_unobstructed": True,
}


class MigrationError(ValueError):
    """Raised when persisted data cannot be migrated without weakening safety."""


def migrate_host_profile(payload: Mapping[str, Any]) -> HostProfile:
    """Validate a persisted host and fill only fixed seated-anchor defaults.

    A profile without a historical layout cannot be considered an already
    approved fixed seated host, so migration marks it as new for host review.
    Explicit non-seated or unknown layouts are rejected instead of normalized.
    """

    if not isinstance(payload, Mapping):
        raise MigrationError("cannot migrate host profile: expected an object")

    normalized = dict(payload)
    layout_was_missing = "layout" not in normalized
    layout = normalized.get("layout", AvatarLayout.SEATED_STUDIO_ANCHOR.value)
    layout_value = layout.value if isinstance(layout, AvatarLayout) else layout
    if layout_value != AvatarLayout.SEATED_STUDIO_ANCHOR.value:
        raise MigrationError(f"unsafe host layout cannot be migrated: {layout_value!r}")

    for field, default in _SAFE_HOST_DEFAULTS.items():
        normalized.setdefault(field, default)
    if layout_was_missing:
        normalized["is_new"] = True

    try:
        return HostProfile.model_validate(normalized)
    except ValidationError as error:
        raise MigrationError(f"cannot migrate host profile safely: {error}") from error


def migrate_task_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Migrate task structure and always migrate an embedded host profile."""

    result = dict(payload)
    if result.get("schema_version", 1) < 2:
        result["schema_version"] = 2
        result["status"] = _STATUS_MAP.get(result.get("status", "created"), "input_received")
        result.setdefault("mode", "manual")
        result.setdefault("topic_source", "auto_hot")
        result.setdefault("avatar_source", "saved_host")
        result.setdefault("input_text", None)
        result.setdefault("candidates", [])
        result.setdefault("skipped_candidates", [])
        result.setdefault("selected_topic_id", None)
        result.setdefault("host_profile", None)
        result.setdefault("news_script", None)
        result.setdefault("media_plan", None)
        result.setdefault("subtitle_enabled", False)
        result.setdefault("video_structure", "studio_anchor_plus_vertical_news_insert")
        result.setdefault("media_policy", "reliable_original_first_ai_demo_fallback")
        result.setdefault("platforms", ["douyin", "wechat_channels", "xiaohongshu"])
        result.setdefault("approvals", [])
        result.setdefault("artifacts", [])

    result.setdefault("host_profile", None)
    host_profile = result["host_profile"]
    if host_profile is not None:
        result["host_profile"] = migrate_host_profile(host_profile).model_dump(mode="json")
    return result
