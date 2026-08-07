import json
from datetime import UTC, date, datetime, timedelta

from avatar_pipeline.browser_collection import BrowserCollectionEnvelope
from avatar_pipeline.models import RunMode, TaskStatus
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.research_models import HotspotReviewCard, ResearchRunStatus
from avatar_pipeline.research_repository import ResearchRunRepository
from avatar_pipeline.research_service import ResearchService
from avatar_pipeline.service import DailyWorkflowService

DAY = date(2026, 8, 7)
NOW = datetime(2026, 8, 7, 10, 0, tzinfo=UTC)


def platform_item(source_id, event_key, platform, likes):
    return {
        "source_id": source_id,
        "event_key": event_key,
        "platform": platform,
        "content_id": source_id,
        "canonical_url": f"https://example.test/{source_id}",
        "account_name": "公开账号",
        "title_or_caption": f"热点 {event_key}",
        "published_at": (NOW - timedelta(hours=12)).isoformat(),
        "collected_at": NOW.isoformat(),
        "query": "热点",
        "visible_metrics": {"likes": likes, "comments": 100},
        "metric_visibility": {
            "likes": "visible_exact",
            "comments": "visible_exact",
            "views": "not_visible",
        },
        "collector_method": "chrome_authenticated",
        "raw_evidence_reference": f"browser/{source_id}.json",
    }


def envelope():
    return BrowserCollectionEnvelope.model_validate(
        {
            "schema_version": 1,
            "collector_name": "chrome-browser-readonly",
            "started_at": NOW.isoformat(),
            "completed_at": NOW.isoformat(),
            "capabilities": [
                {
                    "platform": platform,
                    "status": "ready",
                    "method": "chrome_authenticated",
                    "observed_at": NOW.isoformat(),
                }
                for platform in ("douyin", "wechat_channels", "xiaohongshu")
            ],
            "items": [
                platform_item("dy-1", "event-1", "douyin", 10000),
                platform_item("xhs-1", "event-1", "xiaohongshu", 8000),
                platform_item("dy-2", "event-2", "douyin", 7000),
                platform_item("wx-2", "event-2", "wechat_channels", 6000),
            ],
            "failures": [],
        }
    )


def authority_metadata():
    result = {}
    for key in ("event-1", "event-2"):
        result[key] = {
            "title": f"已核实 {key}",
            "pillar": "career_pressure",
            "fact_status": "verified",
            "verification_summary": "核心事实已由官方来源确认。",
            "authority_evidence": [
                {
                    "source_id": f"official-{key}",
                    "publisher": "官方机构",
                    "title": f"官方说明 {key}",
                    "url_or_reference": f"https://authority.example/{key}",
                    "published_at": NOW.isoformat(),
                    "authority_type": "official",
                    "verifies_fact": True,
                    "conflicts": False,
                    "summary": "官方确认核心事实。",
                }
            ],
            "audience_insight": "职场人关注事件对日常工作的影响。",
            "speaking_angle": "解释事实，再给出普通人可执行的判断方法。",
        }
    return result


def test_real_browser_evidence_ranks_and_bridges_to_manual_hotspot_review(tmp_path):
    research_repository = ResearchRunRepository(tmp_path)
    research = ResearchService(research_repository)
    research.start(DAY)

    imported = research.import_browser_evidence(DAY, envelope())
    assert imported.status is ResearchRunStatus.COLLECTING

    ranking = research.rank_browser_hotspots(DAY, authority_metadata(), now=NOW)
    assert len(ranking.cards) == 2
    assert all(isinstance(card, HotspotReviewCard) for card in ranking.cards)

    task_repository = DailyTaskRepository(tmp_path)
    production = DailyWorkflowService(task_repository)
    production.start_day(DAY, mode=RunMode.MANUAL)
    task = research.submit_hotspot_cards(DAY, production)

    assert task.status is TaskStatus.HOTSPOT_REVIEW
    assert len(task.candidates) == 2
    assert task.approvals == []
    assert task.selected_topic_id is None
    assert all(candidate.publishable for candidate in task.candidates)
    assert all(candidate.verification_summary for candidate in task.candidates)
    assert all(len(candidate.source_evidence) >= 3 for candidate in task.candidates)


def test_hotspot_report_truthfully_shows_channels_metrics_unknowns_and_media_plan(tmp_path):
    research = ResearchService(ResearchRunRepository(tmp_path))
    research.start(DAY)
    research.import_browser_evidence(DAY, envelope())
    research.rank_browser_hotspots(DAY, authority_metadata(), now=NOW)

    report_path = research.render_hotspot_report(DAY)
    report = report_path.read_text(encoding="utf-8")

    assert "Top 3 热点候选" in report
    assert "抖音" in report
    assert "小红书" in report
    assert "视频号" in report
    assert "播放量：unknown" in report
    assert "Seedance 2.0" in report
    assert "不直接使用平台热点视频" in report
    assert "选择一个热点后才进入脚本生成" in report


def test_browser_artifact_persists_no_credentials(tmp_path):
    research = ResearchService(ResearchRunRepository(tmp_path))
    research.start(DAY)
    research.import_browser_evidence(DAY, envelope())

    path = tmp_path / "days" / DAY.isoformat() / "research" / "real" / "browser-evidence.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(payload).casefold()

    assert "cookie" not in serialized
    assert "token" not in serialized
    assert len(payload["items"]) == 4
