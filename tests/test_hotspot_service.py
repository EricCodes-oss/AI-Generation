from datetime import date

from avatar_pipeline.config import load_config
from avatar_pipeline.hotspot_models import CollectionStatus, HotspotFailure
from avatar_pipeline.hotspot_repository import HotspotRepository
from avatar_pipeline.hotspot_service import HotspotService
from tests.hotspot_factories import record, snapshot


def test_service_rejects_unreviewed_event_and_preserves_collection_failure(tmp_path):
    day = date(2026, 8, 10)
    repository = HotspotRepository(tmp_path)
    records = [
        record("w0", "weibo", 1, "同一事件"),
        record("b0", "baidu", 2, "同一事件"),
        record("z0", "zhihu", 3, "同一事件"),
    ]
    failure = HotspotFailure(
        platform="bilibili",
        captured_at=records[0].captured_at,
        reason="api returned -352",
        raw_snapshot_path="tmp/bilibili.json",
        status=CollectionStatus.RESTRICTED,
    )
    repository.save_snapshot(
        day,
        snapshot(
            "t0",
            "2026-08-10T19:40:00+08:00",
            records=records,
            failures=[failure],
        ),
    )
    service = HotspotService(repository, load_config("configs/default.yaml").hotspot)
    report = service.build_report(day)
    assert report.outcome == "no_qualified_hotspot"
    assert report.collection_failures[0].reason == "api returned -352"
    assert any("missing_verification" in item.reasons for item in report.rejected_events)
