from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = PROJECT_ROOT / "skills"
SKILL_NAMES = (
    "daily-hotspot-research",
    "hotspot-query-planner",
    "channels-hotspot-research",
    "hotspot-source-recorder",
    "audience-comment-insight",
    "hotspot-ranking-review",
)

PRESSURE_GUARDRAILS = {
    "hotspot-query-planner": (
        "exactly 9 core query groups",
        "three per content pillar",
        "eldercare",
        "14-day cooldown",
    ),
    "channels-hotspot-research": (
        "disclose every platform failure",
        "never fabricate platform coverage",
        "WeChat Channels",
    ),
    "hotspot-source-recorder": (
        "provenance",
        "unknown metrics remain null",
        "raw artifact",
    ),
    "audience-comment-insight": (
        "never copy a complete comment",
        "never infer exact demographics",
        "implicit need",
    ),
    "hotspot-ranking-review": (
        "72 hours",
        "7 days",
        "at least two target platforms",
        "official or authoritative verification",
        "do not estimate",
        "watermark",
    ),
    "daily-hotspot-research": (
        "Top 3",
        "HOTSPOT_REVIEW",
        "do not write scripts",
        "wait for explicit user approval",
    ),
}


def _read_skill(name: str) -> tuple[dict, str]:
    path = SKILLS_ROOT / name / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def test_all_project_research_skills_have_discoverable_frontmatter_and_contract_sections():
    for name in SKILL_NAMES:
        metadata, body = _read_skill(name)
        assert metadata["name"] == name
        assert metadata["description"].startswith("Use when")
        assert set(metadata) == {"name", "description"}
        for section in (
            "## Inputs",
            "## Outputs",
            "## Quality Gate",
            "## Prohibited Behavior",
            "## Failure Degradation",
            "## User Actions",
        ):
            assert section in body, f"{name} is missing {section}"


def test_pressure_scenarios_are_explicitly_prevented():
    for name, required_phrases in PRESSURE_GUARDRAILS.items():
        _, body = _read_skill(name)
        for phrase in required_phrases:
            assert phrase.casefold() in body.casefold(), f"{name} lacks guardrail: {phrase}"


def test_research_orchestrator_is_allowlisted_and_stops_at_hotspot_review():
    _, body = _read_skill("daily-hotspot-research")
    allowed = {
        "hotspot-query-planner",
        "channels-hotspot-research",
        "hotspot-source-recorder",
        "audience-comment-insight",
        "hotspot-ranking-review",
        "opinions-crawler",
        "wechat-article-search",
    }
    for skill_name in allowed:
        assert f"`{skill_name}`" in body

    assert "Only invoke the seven Skills listed above" in body
    assert "父母养老与照护压力" in body
    assert "approve, revise, redo, return, or hold" in body
    assert "do not write scripts" in body.casefold()
    assert "wait for explicit user approval" in body
