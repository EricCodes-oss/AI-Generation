"""Adapters that import already-captured local evidence; no network access."""

import json
from datetime import datetime
from pathlib import Path

from avatar_pipeline.hotspot_models import (
    CollectionStatus,
    HotspotFailure,
    HotspotRecord,
    HotspotSnapshot,
)
from avatar_pipeline.hotspot_normalizer import (
    classify_nature,
    normalize_platform,
    parse_heat,
)


def import_canonical_snapshot(path: Path) -> HotspotSnapshot:
    return HotspotSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def import_tophub_snapshot(
    *,
    path: Path,
    snapshot_id: str,
    captured_at: datetime,
    timezone: str,
    platform_aliases: dict[str, str],
    failures: dict[str, tuple[str, str]],
) -> HotspotSnapshot:
    boards = json.loads(path.read_text(encoding="utf-8"))
    records: list[HotspotRecord] = []
    for board in boards:
        source_platform = str(board["platform"])
        platform = normalize_platform(source_platform, platform_aliases)
        if platform not in set(platform_aliases.values()):
            continue
        for index, item in enumerate(board.get("items", []), start=1):
            rank_text = str(item.get("rank") or index)
            if not rank_text.isdigit():
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            records.append(
                HotspotRecord(
                    record_id=f"{snapshot_id}:{platform}:{rank_text}:{index}",
                    platform=platform,
                    board_name=source_platform,
                    captured_at=captured_at,
                    timezone=timezone,
                    rank=int(rank_text),
                    title=title,
                    heat_raw=str(item.get("heat") or "") or None,
                    heat_value=parse_heat(item.get("heat")),
                    url_or_reference=str(item.get("url") or f"{platform}:{title}"),
                    raw_snapshot_path=str(path),
                    content_nature=classify_nature(source_platform, title),
                )
            )
    failure_items = [
        HotspotFailure(
            platform=platform,
            captured_at=captured_at,
            reason=reason,
            raw_snapshot_path=raw_path,
            status=CollectionStatus.RESTRICTED,
        )
        for platform, (reason, raw_path) in sorted(failures.items())
    ]
    return HotspotSnapshot(
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        timezone=timezone,
        records=records,
        failures=failure_items,
    )
