from pathlib import Path

import yaml

from scripts.verify_research_skills import verify_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = PROJECT_ROOT / "skills" / "third_party.lock.yaml"


def test_research_skill_lock_pins_required_collectors():
    raw = yaml.safe_load(LOCK_PATH.read_text(encoding="utf-8"))
    skills = {item["name"]: item for item in raw["skills"]}

    assert set(skills) == {"opinions-crawler", "wechat-article-search"}
    for skill in skills.values():
        assert len(skill["commit"]) == 40
        assert skill["installed"] is False
        assert skill["real_calls_enabled"] is False
        assert (PROJECT_ROOT / skill["audit_path"]).is_file()
        assert skill["install_path"]

    assert skills["opinions-crawler"]["requires"]["node_min_major"] == 20
    assert skills["opinions-crawler"]["requires"]["chrome"] is True


def test_verifier_separates_local_readiness_from_real_calls():
    report = verify_manifest(
        PROJECT_ROOT,
        executable_resolver=lambda name: f"/fake/{name}" if name in {"node"} else None,
        node_version_reader=lambda _path: "v22.22.2",
        chrome_exists=lambda: True,
    )

    assert report.manifest_valid is True
    assert report.skills["opinions-crawler"].locally_ready is False
    assert "install path is missing" in report.skills["opinions-crawler"].issues
    assert report.skills["opinions-crawler"].real_calls_enabled is False
    assert report.skills["wechat-article-search"].real_calls_enabled is False


def test_real_call_switch_does_not_change_local_prerequisite_readiness(tmp_path):
    install_path = tmp_path / ".local" / "third-party-skills" / "collector"
    install_path.mkdir(parents=True)
    audit_path = tmp_path / "skills" / "audits" / "collector.md"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text("# audited\n", encoding="utf-8")
    lock_path = tmp_path / "skills" / "third_party.lock.yaml"
    lock_path.write_text(
        """
schema_version: 1
skills:
  - name: collector
    repository: https://example.invalid/collector.git
    commit: 0123456789abcdef0123456789abcdef01234567
    path: skills/collector
    role: Test collector
    install_path: .local/third-party-skills/collector
    installed: true
    audit_path: skills/audits/collector.md
    requires:
      node_min_major: 20
      chrome: false
      executables: [node]
    real_calls_enabled: true
""".lstrip(),
        encoding="utf-8",
    )

    report = verify_manifest(
        tmp_path,
        executable_resolver=lambda name: f"/fake/{name}",
        node_version_reader=lambda _path: "v22.22.2",
        chrome_exists=lambda: False,
    )

    assert report.skills["collector"].locally_ready is True
    assert report.skills["collector"].real_calls_enabled is True
