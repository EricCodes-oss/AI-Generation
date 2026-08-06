from hashlib import sha256
from pathlib import Path

import yaml

from scripts.verify_research_skills import verify_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = PROJECT_ROOT / "skills" / "third_party.lock.yaml"


def tree_checksum(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_research_skill_lock_pins_required_collectors():
    raw = yaml.safe_load(LOCK_PATH.read_text(encoding="utf-8"))
    skills = {item["name"]: item for item in raw["skills"]}

    assert set(skills) == {"opinions-crawler", "wechat-article-search"}
    for skill in skills.values():
        assert len(skill["commit"]) == 40
        assert skill["installed"] is True
        assert skill["real_calls_enabled"] is False
        assert (PROJECT_ROOT / skill["audit_path"]).is_file()
        assert skill["install_path"].startswith(".local/third-party-skills/")
        assert len(skill["source_tree_sha256"]) == 64
        assert skill["capability_probe"]["status"] in {"ready", "missing", "skipped"}

    opinions = skills["opinions-crawler"]
    wechat = skills["wechat-article-search"]
    assert opinions["requires"]["node_min_major"] == 20
    assert opinions["requires"]["chrome"] is True
    assert opinions["requires"]["local_executables"]["opencli"] == ".local/bin/opencli"
    assert opinions["requires"]["pinned_runtime"]["version"] == "1.8.6"
    assert opinions["requires"]["chrome_extension_package"]["version"] == "1.0.22"
    assert len(opinions["requires"]["chrome_extension_package"]["archive_sha256"]) == 64
    assert wechat["requires"]["npm_packages"] == [
        {
            "name": "cheerio",
            "version": "1.2.0",
            "package_json": ".local/tools/wechat-article-search/node_modules/cheerio/package.json",
            "integrity": (
                "sha512-WDrybc/gKFpTYQutKIK6UvfcuxijIZfMfXaYm8NMsPQxSYvf+13fXUJ4rztGGbJ"
                "cBQ/GF55gvrZ0Bc0bj/mqvg=="
            ),
        }
    ]


def test_verifier_separates_source_installation_prerequisites_and_real_calls(tmp_path):
    install_path = tmp_path / ".local" / "third-party-skills" / "opinions-crawler"
    install_path.mkdir(parents=True)
    (install_path / "SKILL.md").write_text("# installed\n", encoding="utf-8")
    audit_path = tmp_path / "skills" / "audits" / "opinions-crawler.md"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text("# audited\n", encoding="utf-8")
    lock_path = tmp_path / "skills" / "third_party.lock.yaml"
    lock_path.write_text(
        f"""
schema_version: 1
skills:
  - name: opinions-crawler
    repository: https://example.invalid/collector.git
    commit: 0123456789abcdef0123456789abcdef01234567
    path: skills/opinions-crawler
    role: Test collector
    install_path: .local/third-party-skills/opinions-crawler
    installed: true
    source_tree_sha256: {tree_checksum(install_path)}
    audit_path: skills/audits/opinions-crawler.md
    requires:
      node_min_major: 20
      chrome: true
      executables: [node, npm, opencli]
      chrome_extension: Browser Bridge
      authenticated_sites: platform-specific
    capability_probe:
      command: [opencli, --version]
      status: missing
      observed_at: 2026-08-04
      detail: executable missing
    real_calls_enabled: false
""".lstrip(),
        encoding="utf-8",
    )

    report = verify_manifest(
        tmp_path,
        executable_resolver=lambda name: f"/fake/{name}" if name == "node" else None,
        node_version_reader=lambda _path: "v22.22.2",
        chrome_exists=lambda: True,
    )

    assert report.manifest_valid is True
    opinions = report.skills["opinions-crawler"]
    assert opinions.source_installed is True
    assert opinions.source_verified is True
    assert opinions.locally_ready is False
    assert opinions.prerequisites["node"] == "ready"
    assert opinions.prerequisites["npm"] == "missing"
    assert opinions.prerequisites["opencli"] == "missing"
    assert opinions.prerequisites["chrome"] == "ready"
    assert opinions.prerequisites["chrome_extension"] == "manual_action_required"
    assert opinions.prerequisites["authenticated_sites"] == "manual_action_required"
    assert opinions.real_calls_enabled is False


def test_real_call_switch_does_not_change_local_prerequisite_readiness(tmp_path):
    install_path = tmp_path / ".local" / "third-party-skills" / "collector"
    install_path.mkdir(parents=True)
    (install_path / "SKILL.md").write_text("# installed\n", encoding="utf-8")
    audit_path = tmp_path / "skills" / "audits" / "collector.md"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text("# audited\n", encoding="utf-8")
    lock_path = tmp_path / "skills" / "third_party.lock.yaml"
    lock_path.write_text(
        f"""
schema_version: 1
skills:
  - name: collector
    repository: https://example.invalid/collector.git
    commit: 0123456789abcdef0123456789abcdef01234567
    path: skills/collector
    role: Test collector
    install_path: .local/third-party-skills/collector
    installed: true
    source_tree_sha256: {tree_checksum(install_path)}
    audit_path: skills/audits/collector.md
    requires:
      node_min_major: 20
      chrome: false
      executables: [node]
    capability_probe:
      command: [node, --version]
      status: ready
      observed_at: 2026-08-04
      detail: safe version probe
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


def test_verifier_rejects_an_installed_source_tree_checksum_mismatch(tmp_path):
    install_path = tmp_path / ".local" / "third-party-skills" / "collector"
    install_path.mkdir(parents=True)
    (install_path / "SKILL.md").write_text("# changed\n", encoding="utf-8")
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
    source_tree_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    audit_path: skills/audits/collector.md
    requires:
      node_min_major: 20
      chrome: false
      executables: [node]
    capability_probe:
      command: [node, --version]
      status: ready
      observed_at: 2026-08-04
      detail: safe version probe
    real_calls_enabled: false
""".lstrip(),
        encoding="utf-8",
    )

    report = verify_manifest(
        tmp_path,
        executable_resolver=lambda name: f"/fake/{name}",
        node_version_reader=lambda _path: "v22.22.2",
        chrome_exists=lambda: False,
    )

    assert report.skills["collector"].source_verified is False
    assert "source tree checksum does not match lock" in report.skills["collector"].issues


def test_verifier_resolves_project_local_executables_and_node_packages(tmp_path):
    install_path = tmp_path / ".local" / "third-party-skills" / "collector"
    install_path.mkdir(parents=True)
    (install_path / "SKILL.md").write_text("# installed\n", encoding="utf-8")
    audit_path = tmp_path / "skills" / "audits" / "collector.md"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text("# audited\n", encoding="utf-8")

    local_bin = tmp_path / ".local" / "bin"
    local_bin.mkdir(parents=True)
    (local_bin / "opencli").write_text("#!/bin/sh\n", encoding="utf-8")
    runtime_path = (
        tmp_path / ".local" / "tools" / "opencli" / "node_modules" / "@jackwener" / "opencli"
    )
    runtime_path.mkdir(parents=True)
    (runtime_path / "package.json").write_text(
        '{"name":"@jackwener/opencli","version":"1.8.6"}\n', encoding="utf-8"
    )
    package_path = tmp_path / ".local" / "tools" / "wechat" / "node_modules" / "cheerio"
    package_path.mkdir(parents=True)
    (package_path / "package.json").write_text(
        '{"name":"cheerio","version":"1.2.0"}\n', encoding="utf-8"
    )

    lock_path = tmp_path / "skills" / "third_party.lock.yaml"
    lock_path.write_text(
        f"""
schema_version: 1
skills:
  - name: collector
    repository: https://example.invalid/collector.git
    commit: 0123456789abcdef0123456789abcdef01234567
    path: skills/collector
    role: Test collector
    install_path: .local/third-party-skills/collector
    installed: true
    source_tree_sha256: {tree_checksum(install_path)}
    audit_path: skills/audits/collector.md
    requires:
      node_min_major: 20
      chrome: false
      executables: [node, opencli]
      local_executables:
        opencli: .local/bin/opencli
      pinned_runtime:
        package: "@jackwener/opencli"
        version: "1.8.6"
        package_json: .local/tools/opencli/node_modules/@jackwener/opencli/package.json
      npm_packages:
        - name: cheerio
          version: 1.2.0
          package_json: .local/tools/wechat/node_modules/cheerio/package.json
    capability_probe:
      command: [opencli, --version]
      status: ready
      observed_at: 2026-08-04
      detail: project-local executable probe passed
    real_calls_enabled: false
""".lstrip(),
        encoding="utf-8",
    )

    report = verify_manifest(
        tmp_path,
        executable_resolver=lambda name: "/fake/node" if name == "node" else None,
        node_version_reader=lambda _path: "v23.11.0",
        chrome_exists=lambda: False,
    )

    collector = report.skills["collector"]
    assert collector.prerequisites["opencli"] == "ready"
    assert collector.prerequisites["runtime:@jackwener/opencli"] == "ready"
    assert collector.prerequisites["npm_package:cheerio"] == "ready"
    assert collector.locally_ready is True
