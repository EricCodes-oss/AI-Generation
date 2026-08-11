from datetime import date

import pytest

from avatar_pipeline.hotspot_repository import HotspotRepository, SnapshotAlreadyExists
from tests.hotspot_factories import snapshot


def test_repository_round_trips_snapshot_and_lists_chronologically(tmp_path):
    repository = HotspotRepository(tmp_path)
    later = snapshot("t1", "2026-08-10T19:50:00+08:00")
    earlier = snapshot("t0", "2026-08-10T19:40:00+08:00")
    repository.save_snapshot(date(2026, 8, 10), later)
    repository.save_snapshot(date(2026, 8, 10), earlier)
    assert [item.snapshot_id for item in repository.list_snapshots(date(2026, 8, 10))] == [
        "t0",
        "t1",
    ]


def test_repository_refuses_to_overwrite_raw_snapshot(tmp_path):
    repository = HotspotRepository(tmp_path)
    item = snapshot("t0", "2026-08-10T19:40:00+08:00")
    repository.save_snapshot(date(2026, 8, 10), item)
    with pytest.raises(SnapshotAlreadyExists, match="t0"):
        repository.save_snapshot(date(2026, 8, 10), item)


def test_repository_loads_the_saved_report(tmp_path):
    from avatar_pipeline.hotspot_models import HotspotReport

    repository = HotspotRepository(tmp_path)
    report = HotspotReport(
        day="2026-08-10",
        rule_version="viral-v1.0",
        snapshot_ids=[],
        collection_failures=[],
        candidates=[],
        outcome="no_qualified_hotspot",
    )
    repository.save_report(date(2026, 8, 10), report, "# report\n")
    assert repository.load_report(date(2026, 8, 10)) == report


def test_repository_round_trips_short_video_evidence(tmp_path):
    from datetime import datetime

    from avatar_pipeline.hotspot_models import (
        EventShortVideoEvidence,
        ShortVideoPlatformEvidence,
    )

    repository = HotspotRepository(tmp_path)
    evidence = EventShortVideoEvidence(
        event_id="event-1",
        captured_at=datetime.fromisoformat("2026-08-11T11:30:00+08:00"),
        platforms={
            "douyin": ShortVideoPlatformEvidence(
                platform="douyin",
                source_count=2,
                comment_sample_count=10,
                views=1000,
                likes=100,
                suitability_score=0.8,
                raw_evidence_paths=["tmp/douyin.json"],
            )
        },
    )
    repository.save_short_video_evidence(date(2026, 8, 11), [evidence])
    loaded = repository.load_short_video_evidence(date(2026, 8, 11))
    assert loaded == {"event-1": evidence}
