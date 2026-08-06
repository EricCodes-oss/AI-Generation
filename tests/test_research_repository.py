import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_models import (
    DailyResearchPlan,
    QueryGroup,
    ResearchPlatform,
    TimeWindow,
)
from avatar_pipeline.research_repository import (
    ResearchRevisionAlreadyExists,
    ResearchRunAlreadyExists,
    ResearchRunNotFound,
    ResearchRunRepository,
)

NOW = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)
PILLARS = (
    ContentPillarSlug.CAREER_PRESSURE,
    ContentPillarSlug.PARENT_CHILD_COMMUNICATION,
    ContentPillarSlug.SELF_GROWTH,
)


def make_plan(day: date) -> DailyResearchPlan:
    groups = [
        QueryGroup(
            id=f"{day.isoformat()}-q-{index}",
            pillar=PILLARS[index // 3],
            intent=f"意图 {index}",
            scene=f"场景 {index}",
            natural_query=f"自然查询 {index}",
            platform_expressions={ResearchPlatform.XIAOHONGSHU: [f"查询 {index}"]},
            time_window=TimeWindow.LAST_72_HOURS,
        )
        for index in range(9)
    ]
    return DailyResearchPlan(
        day=day,
        core_groups=groups,
        time_window_shares={
            TimeWindow.LAST_72_HOURS: 0.5,
            TimeWindow.LAST_7_DAYS: 0.35,
            TimeWindow.LAST_30_DAYS: 0.15,
        },
        created_at=NOW,
    )


def test_repository_round_trips_utf8_and_creates_research_directories(tmp_path):
    repo = ResearchRunRepository(tmp_path)
    run = repo.create(date(2026, 8, 4))
    run.review_feedback = "请补充职场里被否定后的真实情绪"
    repo.save(run)

    loaded = repo.get(date(2026, 8, 4))
    assert loaded.review_feedback == "请补充职场里被否定后的真实情绪"
    research_root = tmp_path / "days" / "2026-08-04" / "research"
    assert (research_root / "run.json").is_file()
    assert (research_root / "raw").is_dir()
    assert (research_root / "reports").is_dir()
    assert (research_root / "revisions").is_dir()
    assert "被否定" in (research_root / "run.json").read_text(encoding="utf-8")


def test_failed_write_does_not_replace_existing_run_and_cleans_temporary_file(
    tmp_path, monkeypatch
):
    repo = ResearchRunRepository(tmp_path)
    original = repo.create(date(2026, 8, 4))
    original.review_feedback = "原版本"
    repo.save(original)

    changed = repo.get(date(2026, 8, 4))
    changed.review_feedback = "不应写入"

    def fail_dump(*_args, **_kwargs):
        raise OSError("simulated serialization failure")

    monkeypatch.setattr("avatar_pipeline.research_repository.json.dump", fail_dump)
    with pytest.raises(OSError, match="simulated"):
        repo.save(changed)

    assert repo.get(date(2026, 8, 4)).review_feedback == "原版本"
    research_root = tmp_path / "days" / "2026-08-04" / "research"
    assert not list(research_root.glob(".run.json.*.tmp"))


def test_numbered_revisions_are_immutable(tmp_path):
    repo = ResearchRunRepository(tmp_path)
    run = repo.create(date(2026, 8, 4))
    run.revision = 2
    run.review_feedback = "第二版"
    path = repo.save_revision(run)

    assert path.name == "revision-2.json"
    assert json.loads(path.read_text(encoding="utf-8"))["review_feedback"] == "第二版"
    with pytest.raises(ResearchRevisionAlreadyExists):
        repo.save_revision(run)
    assert json.loads(path.read_text(encoding="utf-8"))["review_feedback"] == "第二版"


def test_repository_reports_missing_and_duplicate_runs(tmp_path):
    repo = ResearchRunRepository(tmp_path)
    with pytest.raises(ResearchRunNotFound):
        repo.get(date(2026, 8, 4))

    repo.create(date(2026, 8, 4))
    with pytest.raises(ResearchRunAlreadyExists):
        repo.create(date(2026, 8, 4))


def test_write_artifact_confines_paths_to_the_day_research_directory(tmp_path):
    repo = ResearchRunRepository(tmp_path)
    repo.create(date(2026, 8, 4))

    path = repo.write_artifact(
        date(2026, 8, 4),
        Path("raw") / "小红书.json",
        {"标题": "成年人的沉默"},
    )
    assert json.loads(path.read_text(encoding="utf-8"))["标题"] == "成年人的沉默"

    for invalid in (Path("../task.json"), Path("/tmp/outside.json"), Path("raw/../../escape")):
        with pytest.raises(ValueError, match="research directory"):
            repo.write_artifact(date(2026, 8, 4), invalid, "blocked")


def test_list_recent_plans_is_exclusive_ordered_newest_first_and_date_bounded(tmp_path):
    repo = ResearchRunRepository(tmp_path)
    for day in (date(2026, 7, 1), date(2026, 8, 1), date(2026, 8, 3), date(2026, 8, 4)):
        run = repo.create(day)
        run.plan = make_plan(day)
        repo.save(run)

    plans = repo.list_recent_plans(before_day=date(2026, 8, 4), days=30)

    assert [plan.day for plan in plans] == [date(2026, 8, 3), date(2026, 8, 1)]
