#!/usr/bin/env python3
"""Verify pinned research Skill metadata without making any live calls."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class SkillVerification:
    """Local, non-network readiness for one third-party Skill."""

    name: str
    installed: bool
    locally_ready: bool
    real_calls_enabled: bool
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationReport:
    """Result of validating the lock and local prerequisites."""

    manifest_valid: bool
    skills: Mapping[str, SkillVerification] = field(default_factory=dict)
    manifest_issues: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.manifest_valid and all(skill.locally_ready for skill in self.skills.values())


_REQUIRED_FIELDS = {
    "name",
    "repository",
    "commit",
    "path",
    "role",
    "install_path",
    "installed",
    "audit_path",
    "requires",
    "real_calls_enabled",
}
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _default_node_version_reader(node_path: str) -> str:
    result = subprocess.run(
        [node_path, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip() or result.stderr.strip()


def _default_chrome_exists() -> bool:
    candidates = (
        Path("/Applications/Google Chrome.app"),
        Path("/Applications/Chromium.app"),
        Path.home() / "Applications/Google Chrome.app",
        Path.home() / "Applications/Chromium.app",
    )
    return any(path.exists() for path in candidates) or any(
        shutil.which(name) is not None
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
    )


def _node_major(version: str) -> int | None:
    match = re.search(r"v?(\d+)", version)
    return int(match.group(1)) if match else None


def verify_manifest(
    project_root: Path,
    *,
    executable_resolver: Callable[[str], str | None] = shutil.which,
    node_version_reader: Callable[[str], str] = _default_node_version_reader,
    chrome_exists: Callable[[], bool] = _default_chrome_exists,
) -> VerificationReport:
    """Validate the lock and inspect local prerequisites without executing a Skill."""

    root = Path(project_root).resolve()
    lock_path = root / "skills" / "third_party.lock.yaml"
    if not lock_path.is_file():
        return VerificationReport(False, manifest_issues=("lock manifest is missing",))

    try:
        raw = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return VerificationReport(False, manifest_issues=(f"cannot read lock manifest: {exc}",))

    manifest_issues: list[str] = []
    entries = raw.get("skills") if isinstance(raw, dict) else None
    if not isinstance(entries, list):
        return VerificationReport(False, manifest_issues=("skills must be a list",))

    names: set[str] = set()
    reports: dict[str, SkillVerification] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            manifest_issues.append(f"skills[{index}] must be a mapping")
            continue

        missing = sorted(_REQUIRED_FIELDS - set(entry))
        if missing:
            manifest_issues.append(f"skills[{index}] missing fields: {', '.join(missing)}")
            continue

        name = entry["name"]
        if not isinstance(name, str) or not name:
            manifest_issues.append(f"skills[{index}] has invalid name")
            continue
        if name in names:
            manifest_issues.append(f"duplicate skill name: {name}")
            continue
        names.add(name)

        if not isinstance(entry["commit"], str) or not _COMMIT_RE.fullmatch(entry["commit"]):
            manifest_issues.append(f"{name}: commit must be a 40-character lowercase SHA")

        audit_path = entry["audit_path"]
        if not isinstance(audit_path, str) or not (root / audit_path).is_file():
            manifest_issues.append(f"{name}: audit file is missing")

        requires = entry["requires"]
        if not isinstance(requires, dict):
            manifest_issues.append(f"{name}: requires must be a mapping")
            requires = {}

        issues: list[str] = []
        install_path_value = entry["install_path"]
        install_path = root / install_path_value if isinstance(install_path_value, str) else None
        if install_path is None or not install_path.is_dir():
            issues.append("install path is missing")

        installed = entry["installed"] is True
        if not installed:
            issues.append("manifest marks skill as not installed")

        executables = requires.get("executables", [])
        if not isinstance(executables, list):
            manifest_issues.append(f"{name}: requires.executables must be a list")
            executables = []
        resolved: dict[str, str] = {}
        for executable in executables:
            path = executable_resolver(executable) if isinstance(executable, str) else None
            if path is None:
                issues.append(f"required executable is missing: {executable}")
            else:
                resolved[executable] = path

        minimum = requires.get("node_min_major")
        if minimum is not None:
            if not isinstance(minimum, int) or minimum < 1:
                manifest_issues.append(f"{name}: node_min_major must be a positive integer")
            elif "node" in resolved:
                try:
                    major = _node_major(node_version_reader(resolved["node"]))
                except (OSError, subprocess.SubprocessError, ValueError) as exc:
                    issues.append(f"cannot read Node.js version: {exc}")
                else:
                    if major is None:
                        issues.append("cannot parse Node.js version")
                    elif major < minimum:
                        issues.append(f"Node.js {major} is below required major {minimum}")

        if requires.get("chrome") is True and not chrome_exists():
            issues.append("Chrome or Chromium is missing")

        real_calls_enabled = entry["real_calls_enabled"] is True
        reports[name] = SkillVerification(
            name=name,
            installed=installed,
            locally_ready=not issues,
            real_calls_enabled=real_calls_enabled,
            issues=tuple(issues),
        )

    return VerificationReport(
        manifest_valid=not manifest_issues,
        skills=reports,
        manifest_issues=tuple(manifest_issues),
    )


def _format_report(report: VerificationReport) -> str:
    lines = [
        f"manifest_valid: {str(report.manifest_valid).lower()}",
        f"ok: {str(report.ok).lower()}",
    ]
    for issue in report.manifest_issues:
        lines.append(f"manifest_issue: {issue}")
    for name, skill in sorted(report.skills.items()):
        lines.append(
            f"{name}: installed={str(skill.installed).lower()} "
            f"locally_ready={str(skill.locally_ready).lower()} "
            f"real_calls_enabled={str(skill.real_calls_enabled).lower()}"
        )
        lines.extend(f"  - {issue}" for issue in skill.issues)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = verify_manifest(args.project_root)
    print(_format_report(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
