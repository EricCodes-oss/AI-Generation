import json
from copy import deepcopy
from datetime import date

import pytest

from avatar_pipeline.migration import (
    MigrationError,
    migrate_host_profile,
    migrate_task_payload,
)
from avatar_pipeline.models import AvatarLayout
from avatar_pipeline.repository import DailyTaskRepository

LEGACY_IDENTITY = {
    "id": "anchor-legacy",
    "display_name": "林知夏",
    "reference_image": "assets/hosts/lin-zhixia-v3.png",
    "studio_reference": "assets/studios/quiet-news-room.png",
    "voice_id": "voice-lin-02",
    "visual_style": "成熟陪伴型新闻主持人",
    "version": 7,
    "is_new": False,
}


def test_legacy_host_gets_only_safe_defaults_and_requires_review_without_identity_drift():
    migrated = migrate_host_profile(LEGACY_IDENTITY)

    assert migrated.layout is AvatarLayout.SEATED_STUDIO_ANCHOR
    assert migrated.age_range == "30-36"
    assert migrated.outfit == "deep_navy_blazer_ivory_blouse"
    assert migrated.mouth_unobstructed is True
    assert migrated.id == LEGACY_IDENTITY["id"]
    assert migrated.display_name == LEGACY_IDENTITY["display_name"]
    assert migrated.reference_image == LEGACY_IDENTITY["reference_image"]
    assert migrated.studio_reference == LEGACY_IDENTITY["studio_reference"]
    assert migrated.voice_id == LEGACY_IDENTITY["voice_id"]
    assert migrated.visual_style == LEGACY_IDENTITY["visual_style"]
    assert migrated.version == LEGACY_IDENTITY["version"]
    assert migrated.is_new is True


def test_host_with_explicit_safe_layout_preserves_existing_identity_and_review_flag():
    payload = {
        **LEGACY_IDENTITY,
        "layout": "seated_studio_anchor",
        "age_range": "32-38",
        "outfit": "charcoal_blazer_ivory_blouse",
        "mouth_unobstructed": True,
    }

    migrated = migrate_host_profile(payload)

    assert migrated.reference_image == payload["reference_image"]
    assert migrated.voice_id == payload["voice_id"]
    assert migrated.version == payload["version"]
    assert migrated.is_new is False
    assert migrated.age_range == payload["age_range"]
    assert migrated.outfit == payload["outfit"]


@pytest.mark.parametrize("layout", ["standing_anchor", "outdoor_reporter", "unknown_layout", ""])
def test_non_seated_or_unknown_layout_raises_clear_migration_error(layout):
    with pytest.raises(MigrationError, match="unsafe host layout"):
        migrate_host_profile({**LEGACY_IDENTITY, "layout": layout})


def test_unsafe_host_profile_validation_is_reported_as_migration_error():
    with pytest.raises(MigrationError, match="cannot migrate host profile"):
        migrate_host_profile(
            {
                **LEGACY_IDENTITY,
                "layout": "seated_studio_anchor",
                "mouth_unobstructed": False,
            }
        )


def test_migrate_task_payload_migrates_nested_host_even_for_schema_version_two():
    payload = {
        "schema_version": 2,
        "day": "2026-08-05",
        "host_profile": dict(LEGACY_IDENTITY),
        "stop_reason": "operator paused",
        "candidates": [{"id": "untouched-candidate"}],
    }
    original = deepcopy(payload)

    migrated = migrate_task_payload(payload)

    assert migrated["schema_version"] == 2
    assert migrated["host_profile"]["layout"] == "seated_studio_anchor"
    assert migrated["host_profile"]["is_new"] is True
    assert migrated["host_profile"]["reference_image"] == LEGACY_IDENTITY["reference_image"]
    assert migrated["host_profile"]["voice_id"] == LEGACY_IDENTITY["voice_id"]
    assert migrated["host_profile"]["version"] == LEGACY_IDENTITY["version"]
    assert migrated["stop_reason"] == "operator paused"
    assert migrated["candidates"] == [{"id": "untouched-candidate"}]
    assert payload == original


def test_migrate_task_payload_keeps_missing_or_null_host_as_none():
    without_host = migrate_task_payload({"schema_version": 2, "day": "2026-08-05"})
    null_host = migrate_task_payload(
        {"schema_version": 2, "day": "2026-08-05", "host_profile": None}
    )

    assert without_host["host_profile"] is None
    assert null_host["host_profile"] is None


def test_legacy_task_migration_does_not_fabricate_stop_reason_or_fact_verification():
    payload = {
        "day": "2026-08-04",
        "status": "created",
        "candidates": [
            {
                "id": "candidate-1",
                "fact_status": "pending",
                "publishable": False,
                "source_evidence": [],
            }
        ],
    }

    migrated = migrate_task_payload(payload)

    assert "stop_reason" not in migrated
    assert migrated["candidates"] == payload["candidates"]


def test_repository_get_integrates_safe_host_migration_for_schema_version_two(tmp_path):
    day = date(2026, 8, 5)
    path = tmp_path / "days" / day.isoformat() / "task.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "day": day.isoformat(),
                "status": "input_received",
                "host_profile": LEGACY_IDENTITY,
                "stop_reason": None,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    task = DailyTaskRepository(tmp_path).get(day)

    assert task.host_profile is not None
    assert task.host_profile.layout is AvatarLayout.SEATED_STUDIO_ANCHOR
    assert task.host_profile.reference_image == LEGACY_IDENTITY["reference_image"]
    assert task.host_profile.voice_id == LEGACY_IDENTITY["voice_id"]
    assert task.host_profile.version == LEGACY_IDENTITY["version"]
    assert task.host_profile.is_new is True
    assert task.stop_reason is None


def test_repository_get_blocks_unsafe_legacy_host_layout(tmp_path):
    day = date(2026, 8, 5)
    path = tmp_path / "days" / day.isoformat() / "task.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "day": day.isoformat(),
                "host_profile": {**LEGACY_IDENTITY, "layout": "standing_anchor"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(MigrationError, match="standing_anchor"):
        DailyTaskRepository(tmp_path).get(day)
