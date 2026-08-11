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
        "t0", "t1"
    ]


def test_repository_refuses_to_overwrite_raw_snapshot(tmp_path):
    repository = HotspotRepository(tmp_path)
    item = snapshot("t0", "2026-08-10T19:40:00+08:00")
    repository.save_snapshot(date(2026, 8, 10), item)
    with pytest.raises(SnapshotAlreadyExists, match="t0"):
        repository.save_snapshot(date(2026, 8, 10), item)
