"""Validation for the anchor and inserted-news-media timeline."""

from avatar_pipeline.models import MediaKind, MediaPlan, NewsScript


def validate_media_plan(plan: MediaPlan, script: NewsScript) -> None:
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
        if segment.kind is MediaKind.ORIGINAL_NEWS:
            if not segment.source_id or not segment.provenance:
                raise ValueError("original news media requires source_id and provenance")
            if segment.source_id not in script.source_ids:
                raise ValueError("original media source must be declared by script")
        if segment.kind is MediaKind.AI_DEMO and (
            not segment.disclosure or "AI" not in segment.disclosure.upper()
        ):
            raise ValueError("AI demo media requires disclosure")
        previous_end = segment.end_seconds
    if segments[0].kind is not MediaKind.ANCHOR or segments[-1].kind is not MediaKind.ANCHOR:
        raise ValueError("news video must open and close with the anchor")
    for index in range(len(segments) - 1):
        if segments[index].kind is segments[index + 1].kind:
            raise ValueError("anchor and insert segments must alternate")
