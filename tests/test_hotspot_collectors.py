from datetime import datetime
from pathlib import Path

from avatar_pipeline.hotspot_collectors import (
    import_canonical_snapshot,
    import_tophub_snapshot,
)


def test_canonical_import_round_trips_the_auditable_snapshot():
    snapshot = import_canonical_snapshot(Path("tests/fixtures/hotspots/canonical-t0.json"))
    assert snapshot.snapshot_id == "t0"
    assert snapshot.captured_at == datetime.fromisoformat("2026-08-10T19:40:00+08:00")
    assert snapshot.records == []
    assert snapshot.failures == []


def test_tophub_import_records_restricted_platform_instead_of_zero_heat():
    snapshot = import_tophub_snapshot(
        path=Path("tests/fixtures/hotspots/tophub-t0.json"),
        snapshot_id="t0",
        captured_at=datetime.fromisoformat("2026-08-10T19:40:00+08:00"),
        timezone="Asia/Shanghai",
        platform_aliases={"微博": "weibo", "百度": "baidu"},
        failures={"bilibili": ("api returned -352", "tmp/t0/bilibili.json")},
    )
    assert {item.platform for item in snapshot.records} == {"weibo", "baidu"}
    assert snapshot.failures[0].platform == "bilibili"
    assert snapshot.failures[0].reason == "api returned -352"


def test_tophub_import_keeps_record_ids_unique_when_platform_has_multiple_boards(tmp_path):
    path = tmp_path / "tophub.json"
    path.write_text(
        '[{"platform":"微博","items":[{"rank":"1","title":"事件A"}]},'
        '{"platform":"微博","items":[{"rank":"1","title":"事件B"}]}]',
        encoding="utf-8",
    )
    snapshot = import_tophub_snapshot(
        path=path,
        snapshot_id="t0",
        captured_at=datetime.fromisoformat("2026-08-10T19:40:00+08:00"),
        timezone="Asia/Shanghai",
        platform_aliases={"微博": "weibo"},
        failures={},
    )
    assert len({item.record_id for item in snapshot.records}) == 2
