import json
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from avatar_pipeline.models import ContentPillarSlug
from avatar_pipeline.research_adapters import (
    CollectionBatch,
    CommandCollector,
    CommandSpec,
    FixtureCollector,
    ManualImportCollector,
    RawCollectionItem,
    ResearchCollector,
)
from avatar_pipeline.research_models import (
    DailyResearchPlan,
    QueryGroup,
    ResearchPlatform,
    TimeWindow,
)

NOW = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)


def make_plan() -> DailyResearchPlan:
    pillars = tuple(ContentPillarSlug)
    groups = [
        QueryGroup(
            id=f"q-{index}",
            pillar=pillars[index // 3],
            intent=f"intent-{index}",
            scene=f"scene-{index}",
            natural_query=f"natural-query-{index}",
            platform_expressions={ResearchPlatform.XIAOHONGSHU: [f"query-{index}"]},
            time_window=TimeWindow.LAST_72_HOURS,
        )
        for index in range(9)
    ]
    return DailyResearchPlan(
        day=date(2026, 8, 4),
        core_groups=groups,
        time_window_shares={
            TimeWindow.LAST_72_HOURS: 0.5,
            TimeWindow.LAST_7_DAYS: 0.35,
            TimeWindow.LAST_30_DAYS: 0.15,
        },
        created_at=NOW,
    )


class StepClock:
    def __init__(self) -> None:
        self.current = NOW

    def __call__(self) -> datetime:
        value = self.current
        self.current += timedelta(seconds=1)
        return value


def test_fixture_collector_reads_utf8_json_object_and_list_and_preserves_paths(tmp_path):
    object_path = tmp_path / "douyin.json"
    object_path.write_text(
        json.dumps({"title": "成年人真正的清醒", "likes": "1.2万"}, ensure_ascii=False),
        encoding="utf-8",
    )
    list_path = tmp_path / "xiaohongshu.json"
    list_path.write_text(
        json.dumps([{"title": "别急着否定自己"}, {"title": "允许人生慢一点"}], ensure_ascii=False),
        encoding="utf-8",
    )

    collector: ResearchCollector = FixtureCollector(
        {
            ResearchPlatform.DOUYIN: [object_path],
            ResearchPlatform.XIAOHONGSHU: [list_path],
        },
        clock=StepClock(),
    )
    batch = collector.collect(make_plan())

    assert isinstance(batch, CollectionBatch)
    assert batch.collector_name == "fixture"
    assert [item.payload["title"] for item in batch.raw_items] == [
        "成年人真正的清醒",
        "别急着否定自己",
        "允许人生慢一点",
    ]
    assert [item.platform for item in batch.raw_items] == [
        ResearchPlatform.DOUYIN,
        ResearchPlatform.XIAOHONGSHU,
        ResearchPlatform.XIAOHONGSHU,
    ]
    assert batch.raw_artifact_paths == [str(object_path), str(list_path)]
    assert all(item.raw_artifact_path in batch.raw_artifact_paths for item in batch.raw_items)
    assert batch.failures == []
    assert batch.completed_at > batch.started_at


def test_manual_import_accepts_items_wrapper_and_records_manual_collector(tmp_path):
    path = tmp_path / "manual.json"
    path.write_text(
        json.dumps(
            {
                "items": [{"title": "视频号手工记录", "content_id": "wx-1"}],
                "exported_by": "operator",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    batch = ManualImportCollector(
        {ResearchPlatform.WECHAT_CHANNELS: [path]}, clock=StepClock()
    ).collect(make_plan())

    assert batch.collector_name == "manual_import"
    assert batch.raw_items == [
        RawCollectionItem(
            platform=ResearchPlatform.WECHAT_CHANNELS,
            payload={"title": "视频号手工记录", "content_id": "wx-1"},
            raw_artifact_path=str(path),
        )
    ]


def test_fixture_collector_keeps_partial_success_when_one_platform_file_is_invalid(tmp_path):
    good = tmp_path / "good.json"
    good.write_text('[{"title": "有效内容"}]', encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")

    batch = FixtureCollector(
        {
            ResearchPlatform.XIAOHONGSHU: [good],
            ResearchPlatform.DOUYIN: [bad],
        },
        clock=StepClock(),
    ).collect(make_plan())

    assert [item.payload["title"] for item in batch.raw_items] == ["有效内容"]
    assert len(batch.failures) == 1
    failure = batch.failures[0]
    assert failure.platform is ResearchPlatform.DOUYIN
    assert failure.error_code == "invalid_json"
    assert failure.raw_artifact_path == str(bad)
    assert failure.retryable is False
    assert set(batch.raw_artifact_paths) == {str(good), str(bad)}


def test_command_collector_uses_argument_arrays_without_shell_and_parses_output(tmp_path):
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"items": [{"title": "命令采集结果"}]}, ensure_ascii=False),
            stderr="",
        )

    raw_path = tmp_path / "command-output.json"
    collector = CommandCollector(
        [
            CommandSpec(
                platform=ResearchPlatform.DOUYIN,
                argv=["opencli", "douyin", "hashtag", "职场压力"],
                raw_output_path=raw_path,
                timeout_seconds=12,
                rate_delay_seconds=1.5,
            )
        ],
        runner=runner,
        clock=StepClock(),
    )
    batch = collector.collect(make_plan())

    assert calls == [
        (
            ["opencli", "douyin", "hashtag", "职场压力"],
            {
                "capture_output": True,
                "text": True,
                "timeout": 12.0,
                "check": False,
            },
        )
    ]
    assert "shell" not in calls[0][1]
    assert batch.raw_items[0].payload == {"title": "命令采集结果"}
    assert batch.raw_items[0].rate_delay_seconds == 1.5
    assert raw_path.read_text(encoding="utf-8").startswith("{")
    assert batch.raw_artifact_paths == [str(raw_path)]


def test_command_collector_returns_failures_for_timeout_nonzero_and_invalid_json(tmp_path):
    outcomes = iter(
        [
            subprocess.TimeoutExpired(cmd=["timeout"], timeout=5),
            SimpleNamespace(returncode=2, stdout="partial", stderr="login required"),
            SimpleNamespace(returncode=0, stdout="not-json", stderr=""),
            SimpleNamespace(returncode=0, stdout='[{"title": "仍然成功"}]', stderr=""),
        ]
    )

    def runner(argv, **kwargs):
        outcome = next(outcomes)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    commands = [
        CommandSpec(
            platform=platform,
            argv=["collector", code],
            raw_output_path=tmp_path / f"{code}.json",
            timeout_seconds=5,
        )
        for platform, code in (
            (ResearchPlatform.DOUYIN, "timeout"),
            (ResearchPlatform.WECHAT_CHANNELS, "nonzero"),
            (ResearchPlatform.XIAOHONGSHU, "invalid"),
            (ResearchPlatform.ZHIHU, "success"),
        )
    ]

    batch = CommandCollector(commands, runner=runner, clock=StepClock()).collect(make_plan())

    assert [failure.error_code for failure in batch.failures] == [
        "timeout",
        "non_zero_exit",
        "invalid_json",
    ]
    assert [failure.retryable for failure in batch.failures] == [True, True, False]
    assert batch.failures[1].message == "login required"
    assert [item.payload["title"] for item in batch.raw_items] == ["仍然成功"]
    assert {Path(path).name for path in batch.raw_artifact_paths} == {
        "nonzero.json",
        "invalid.json",
        "success.json",
    }
