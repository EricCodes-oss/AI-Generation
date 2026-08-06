"""Safe migration for legacy task JSON."""

from collections.abc import Mapping
from typing import Any

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


def migrate_task_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version", 1) >= 2:
        return dict(payload)
    result = dict(payload)
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
    result.setdefault("stop_reason", "legacy_task_not_verified")
    return result
