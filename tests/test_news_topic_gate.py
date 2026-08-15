from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.hotspot_selection import HotspotTopicCategory, TopicSelectionApproval
from avatar_pipeline.news_production import initialize_news_run
from avatar_pipeline.news_production_models import NewsRunManifest


def write_selection(path: Path, *, day=date(2026, 8, 12), title="教育热点新进展") -> Path:
    approval = TopicSelectionApproval(
        day=day,
        candidate_id="education-1",
        title=title,
        category=HotspotTopicCategory.EDUCATION,
        pool_sha256="b" * 64,
        approved=True,
        actor="owner",
        reason="共同评估后确认",
        approved_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
    )
    path.write_text(approval.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def test_new_v5_run_copies_confirmed_topic_selection(tmp_path: Path):
    selection = write_selection(tmp_path / "selection.json")
    run_dir = initialize_news_run(
        tmp_path / "output",
        day=date(2026, 8, 12),
        slug="education",
        topic="教育热点新进展",
        version=1,
        quality_config_path=Path("configs/news-video-quality-v5.yaml"),
        topic_selection_path=selection,
    )
    manifest = NewsRunManifest.model_validate_json(
        (run_dir / "production/run-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.topic_selection_id == "education-1"
    assert (run_dir / "production/topic-selection.json").is_file()


def test_new_v5_run_rejects_unconfirmed_or_mismatched_topic(tmp_path: Path):
    selection = write_selection(tmp_path / "selection.json")
    with pytest.raises(ValueError, match="does not match"):
        initialize_news_run(
            tmp_path / "output",
            day=date(2026, 8, 12),
            slug="wrong",
            topic="另一个话题",
            version=1,
            quality_config_path=Path("configs/news-video-quality-v5.yaml"),
            topic_selection_path=selection,
        )
