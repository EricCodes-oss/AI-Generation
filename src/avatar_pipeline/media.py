"""Validation for the anchor and inserted-news-media timeline."""

import re
from collections.abc import Mapping

from avatar_pipeline.media_clearance import MediaEvidence, require_production_media_clearance
from avatar_pipeline.models import AvatarLayout, MediaKind, MediaPlan, NewsScript

_NEGATED_AI_GENERATION_PATTERN = re.compile(
    r"(?:\b(?:not|non)\s*[-–—]?\s*ai\s*[-–—]?\s*generated\b|"
    r"\b(?:not|non)\s+generated\s+by\s+ai\b|"
    r"(?:不是|并非|非)\s*(?:ai|人工智能)\s*生成)",
    re.IGNORECASE,
)
_EXPLICIT_AI_GENERATION_PATTERN = re.compile(
    r"(?:\bai\s*[-–—]?\s*generated\b|"
    r"\bgenerated\s+by\s+ai\b|"
    r"(?:ai|人工智能)\s*生成)",
    re.IGNORECASE,
)


def _has_explicit_ai_generation_disclosure(disclosure: str | None) -> bool:
    if not disclosure or not disclosure.strip():
        return False
    if _NEGATED_AI_GENERATION_PATTERN.search(disclosure):
        return False
    return _EXPLICIT_AI_GENERATION_PATTERN.search(disclosure) is not None


def validate_media_plan(
    plan: MediaPlan,
    script: NewsScript,
    *,
    media_evidence: Mapping[str, MediaEvidence] | None = None,
) -> None:
    if plan.anchor_layout != AvatarLayout.SEATED_STUDIO_ANCHOR:
        raise ValueError("media plan anchor_layout must be seated_studio_anchor")
    if not plan.host_id or not plan.host_id.strip():
        raise ValueError("media plan requires host_id")

    segments = sorted(plan.segments, key=lambda item: item.start_seconds)
    if segments[0].start_seconds != 0:
        raise ValueError("media plan must start at zero")
    if abs(segments[-1].end_seconds - plan.duration_seconds) > 0.01:
        raise ValueError("media plan must end at declared duration")
    script_ids = {segment.id for segment in script.spoken_segments}
    previous_end = 0.0
    for segment in segments:
        if segment.script_segment_id not in script_ids:
            raise ValueError("media segment references unknown script segment")
        if segment.start_seconds < previous_end:
            raise ValueError("media segments must not overlap")
        if segment.kind is MediaKind.ANCHOR:
            if not segment.host_id or not segment.host_id.strip():
                raise ValueError("anchor segment requires host_id")
            if segment.host_id != plan.host_id:
                raise ValueError("anchor segment must reference the declared fixed host")
        if segment.kind is MediaKind.ORIGINAL_NEWS:
            if (
                not segment.source_id
                or not segment.source_id.strip()
                or not segment.provenance
                or not segment.provenance.strip()
            ):
                raise ValueError("original news media requires source_id and provenance")
            if segment.source_id not in script.source_ids:
                raise ValueError("original media source must be declared by script")
            if segment.asset_path:
                if media_evidence is None or segment.asset_path not in media_evidence:
                    raise ValueError("acquired original media requires clearance metadata")
                require_production_media_clearance(media_evidence[segment.asset_path])
        if segment.kind is MediaKind.AI_DEMO and not _has_explicit_ai_generation_disclosure(
            segment.disclosure
        ):
            raise ValueError("AI demo media requires explicit AI generation disclosure")
        previous_end = segment.end_seconds
    if segments[0].kind is not MediaKind.ANCHOR or segments[-1].kind is not MediaKind.ANCHOR:
        raise ValueError("news video must open and close with the anchor")
    for index in range(len(segments) - 1):
        current_is_anchor = segments[index].kind is MediaKind.ANCHOR
        next_is_anchor = segments[index + 1].kind is MediaKind.ANCHOR
        if current_is_anchor == next_is_anchor:
            raise ValueError("anchor and insert segments must alternate")
