"""Safe migration for legacy task and host-profile JSON."""

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from avatar_pipeline.models import AvatarLayout, HostProfile

_LEGACY_STATUS_MAP = {
    "created": "input_received",
    "researched": "hotspot_review",
    "fact_screened": "hotspot_review",
    "topic_approved": "script_review",
    "script_draft": "script_review",
    "topic_script_review": "script_review",
    "script_approved": "media_planning",
    "host_review": "media_planning",
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
    """Validate a persisted host and fill only fixed seated-anchor defaults."""

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


def _migrate_approvals(result: dict[str, Any]) -> None:
    migrated: list[dict[str, Any]] = []
    for raw in result.get("approvals", []):
        if not isinstance(raw, Mapping):
            continue
        gate = raw.get("gate")
        if gate == "topic_script":
            hotspot = dict(raw)
            hotspot["gate"] = "hotspot"
            script = dict(raw)
            script["gate"] = "script"
            migrated.extend((hotspot, script))
        elif gate in {"hotspot", "script", "final_video"}:
            migrated.append(dict(raw))
    result["approvals"] = migrated


def migrate_task_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Migrate task structure and always migrate an embedded host profile."""

    result = dict(payload)
    schema_version = result.get("schema_version", 1)
    if schema_version < 3:
        mode = result.get("mode", "manual")
        old_status = result.get("status", "created")
        mapped_status = _LEGACY_STATUS_MAP.get(old_status, old_status)
        if old_status == "fact_screened" and mode == "managed":
            mapped_status = "scripting"
        result["schema_version"] = 3
        result["status"] = mapped_status
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
        _migrate_approvals(result)

    result.setdefault("host_profile", None)
    host_profile = result["host_profile"]
    if host_profile is not None:
        result["host_profile"] = migrate_host_profile(host_profile).model_dump(mode="json")
    return result
