from datetime import date

import pytest

from avatar_pipeline.models import ArtifactRecord, DailyTask, TaskStatus
from avatar_pipeline.publication import build_publication_package


def ready_task():
    return DailyTask(
        day=date(2026, 8, 6),
        status=TaskStatus.READY_TO_PUBLISH,
        artifacts=[
            ArtifactRecord(kind="master_video", path="video/master.mp4"),
            ArtifactRecord(kind="source_record", path="sources.json"),
        ],
    )


def test_publication_package_reuses_one_master_for_three_platforms():
    package = build_publication_package(ready_task())
    assert package.master_video_path == "video/master.mp4"
    assert set(package.platforms) == {"douyin", "wechat_channels", "xiaohongshu"}
    assert {item.master_video_path for item in package.platforms.values()} == {"video/master.mp4"}


def test_unfinished_task_cannot_be_packaged():
    with pytest.raises(ValueError, match="ready_to_publish"):
        build_publication_package(DailyTask(day=date(2026, 8, 6)))
