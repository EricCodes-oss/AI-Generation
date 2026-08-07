from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = PROJECT_ROOT / "docs" / "operations" / "real-three-platform-collection-runbook.md"
PHASE_RUNBOOK = PROJECT_ROOT / "docs" / "operations" / "phase-2a-hotspot-research-runbook.md"
README = PROJECT_ROOT / "README.md"


def _documentation_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in (RUNBOOK, PHASE_RUNBOOK, README))


def test_real_collection_runbook_documents_platforms_and_read_only_browser_rules():
    text = _documentation_text()

    for platform in ("抖音", "微信视频号", "小红书"):
        assert platform in text
    assert "Chrome 登录态只由 Agent 使用" in text
    assert "禁止保存 Cookie、Token、密码" in text
    assert "只读" in text
    for prohibited_action in ("点赞", "评论", "收藏", "关注", "私信", "发布"):
        assert prohibited_action in text


def test_real_collection_runbook_documents_windows_and_honest_failure_states():
    text = _documentation_text()

    assert "最近 72 小时" in text
    assert "最近 7 天" in text
    for status in (
        "ready",
        "login_required",
        "ui_changed",
        "rate_limited",
        "manual_assist_required",
    ):
        assert f"`{status}`" in text
    assert "null/unknown" in text
    assert "公众号不能冒充视频号" in text


def test_real_collection_runbook_documents_media_safety_and_cli_flow():
    text = _documentation_text()

    assert "带水印" in text
    assert "授权不明" in text
    assert "禁止去水印" in text
    assert "Seedance 2.0 非复刻式 AI 示意画面" in text
    for command in (
        "research-import-browser",
        "research-rank-hotspots",
        "research-hotspot-report",
        "research-submit-top3",
    ):
        assert command in text
    assert "热点、脚本、最终视频三个确认点" in text


def test_sensitive_runtime_directories_are_git_ignored():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "runs/" in gitignore
    assert "workspace/" in gitignore
