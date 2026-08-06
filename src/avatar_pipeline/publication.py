"""Build one reusable master-video publication package for all platforms."""

from pydantic import BaseModel, ConfigDict, Field

from avatar_pipeline.models import DailyTask, TaskStatus


class PlatformPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    master_video_path: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    source_note: str = "来源以视频内信息条和审核记录为准。"
    ai_demo_note: str | None = None


class PublicationPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    master_video_path: str = Field(min_length=1)
    platforms: dict[str, PlatformPackage]


def build_publication_package(task: DailyTask) -> PublicationPackage:
    if task.status is not TaskStatus.READY_TO_PUBLISH:
        raise ValueError("task must be ready_to_publish")
    master = next((item.path for item in task.artifacts if item.kind == "master_video"), None)
    if not master:
        raise ValueError("master video artifact is required")
    ai_note = (
        "视频中如出现AI生成示意画面，将按媒体计划标识。"
        if task.media_plan and any(item.disclosure for item in task.media_plan.segments)
        else None
    )
    packages = {
        platform: PlatformPackage(
            master_video_path=master,
            title=task.news_script.title if task.news_script else "今日热点解读",
            description="固定演播室主持人新闻解读，基于可核验来源整理。",
            tags=["热点解读", "新闻观察", "理性表达"],
            ai_demo_note=ai_note,
        )
        for platform in task.platforms
    }
    return PublicationPackage(master_video_path=master, platforms=packages)
