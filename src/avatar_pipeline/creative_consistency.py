"""Creative-contract gates for V5 productions.

Technical QC can prove that a file renders correctly; it cannot prove that the
finished film still tells the approved story.  This module keeps the approved
creative brief explicit and checks that the selected shots preserve its
non-negotiable visual elements.
"""

from __future__ import annotations

from collections.abc import Iterable

from avatar_pipeline.news_production_models import CreativeLock, NewsTimeline, ShotSelection


def _normalise_tags(tags: Iterable[str]) -> set[str]:
    return {tag.strip().casefold() for tag in tags if tag.strip()}


def creative_consistency_failures(
    lock: CreativeLock,
    shots: ShotSelection,
    timeline: NewsTimeline,
) -> list[str]:
    """Return hard failures when the timeline no longer matches the creative lock."""

    failures: list[str] = []
    if lock.status != "locked":
        failures.append("creative_lock:not_locked")

    shot_by_id = {shot.shot_id: shot for shot in shots.shots}
    used_shot_ids = [segment.shot_id for segment in timeline.segments if segment.type == "broll"]
    used_shot_ids = [shot_id for shot_id in used_shot_ids if shot_id is not None]

    for shot_id in used_shot_ids:
        shot = shot_by_id.get(shot_id)
        if shot is None:
            failures.append(f"creative_lock:unknown_shot:{shot_id}")
            continue
        if not shot.director_approved:
            failures.append(f"creative_lock:unapproved_shot:{shot_id}")
        if not shot.creative_tags:
            failures.append(f"creative_lock:missing_tags:{shot_id}")

    required = _normalise_tags(lock.required_visual_tags)
    covered = _normalise_tags(
        tag for shot in shots.shots if shot.shot_id in used_shot_ids for tag in shot.creative_tags
    )
    for tag in sorted(required - covered):
        failures.append(f"creative_lock:missing_required_visual:{tag}")

    if not used_shot_ids:
        failures.append("creative_lock:no_broll_shot")

    return failures
