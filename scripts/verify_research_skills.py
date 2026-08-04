#!/usr/bin/env python3
"""Verify pinned research Skills and local prerequisites without live platform calls."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

import yaml

Status = str


@dataclass(frozen=True)
class SkillVerification:
    """Separate installed source integrity from runtime and user prerequisites."""

    name: str
    installed: bool
    source_installed: bool
    source_verified: bool
    locally_ready: bool
    real_calls_enabled: bool
    prerequisites: Mapping[str, Status] = field(default_factory=dict)
    probe_status: Status = "skipped"
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationReport:
    """Result of validating the lock and local capability prerequisites."""

    manifest_valid: bool
    skills: Mapping[str, SkillVerification] = field(default_factory=dict)
    manifest_issues: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """Installation audit succeeds even when live-use prerequisites remain manual."""

        return self.manifest_valid and all(
            skill.source_installed and skill.source_verified for skill in self.skills.values()
        )


_REQUIRED_FIELDS = {
    "name",
    "repository",
    "commit",
    "path",
    "role",
    "install_path",
    "installed",
    "source_tree_sha256",
    "audit_path",
    "requires",
    "capability_probe",
    "real_calls_enabled",
}
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PROBE_STATUSES = {"ready", "missing", "skipped"}


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


def _source_tree_sha256(root: Path) -> str:
    digest = sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def verify_manifest(
    project_root: Path,
    *,
    executable_resolver: Callable[[str], str | None] = shutil.which,
    node_version_reader: Callable[[str], str] = _default_node_version_reader,
    chrome_exists: Callable[[], bool] = _default_chrome_exists,
) -> VerificationReport:
    """Validate locked source trees and report each prerequisite truthfully."""

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
        expected_checksum = entry["source_tree_sha256"]
        if not isinstance(expected_checksum, str) or not _SHA256_RE.fullmatch(expected_checksum):
            manifest_issues.append(f"{name}: source_tree_sha256 must be a lowercase SHA-256")

        audit_path = entry["audit_path"]
        if not isinstance(audit_path, str) or not (root / audit_path).is_file():
            manifest_issues.append(f"{name}: audit file is missing")

        requires = entry["requires"]
        if not isinstance(requires, dict):
            manifest_issues.append(f"{name}: requires must be a mapping")
            requires = {}
        probe = entry["capability_probe"]
        if not isinstance(probe, dict):
            manifest_issues.append(f"{name}: capability_probe must be a mapping")
            probe = {}
        probe_status = probe.get("status", "skipped")
        if probe_status not in _PROBE_STATUSES:
            manifest_issues.append(f"{name}: invalid capability probe status")
            probe_status = "skipped"

        issues: list[str] = []
        prerequisites: dict[str, Status] = {}
        install_path_value = entry["install_path"]
        install_path = root / install_path_value if isinstance(install_path_value, str) else None
        source_installed = install_path is not None and install_path.is_dir()
        if not source_installed:
            issues.append("install path is missing")
        installed = entry["installed"] is True
        if not installed:
            issues.append("manifest marks skill as not installed")

        source_verified = False
        if source_installed and isinstance(expected_checksum, str):
            source_verified = _source_tree_sha256(install_path) == expected_checksum
            if not source_verified:
                issues.append("source tree checksum does not match lock")

        executables = requires.get("executables", [])
        if not isinstance(executables, list):
            manifest_issues.append(f"{name}: requires.executables must be a list")
            executables = []
        local_executables = requires.get("local_executables", {})
        if not isinstance(local_executables, dict):
            manifest_issues.append(f"{name}: requires.local_executables must be a mapping")
            local_executables = {}

        resolved: dict[str, str] = {}
        for executable in executables:
            if not isinstance(executable, str):
                manifest_issues.append(f"{name}: executable names must be strings")
                continue
            executable_path = executable_resolver(executable)
            local_path_value = local_executables.get(executable)
            if not executable_path and isinstance(local_path_value, str):
                local_path = root / local_path_value
                if local_path.is_file():
                    executable_path = str(local_path)
            prerequisites[executable] = "ready" if executable_path else "missing"
            if executable_path:
                resolved[executable] = executable_path
                continue
            issues.append(f"required executable is missing: {executable}")

        pinned_runtime = requires.get("pinned_runtime")
        if pinned_runtime is not None:
            if not isinstance(pinned_runtime, dict):
                manifest_issues.append(f"{name}: requires.pinned_runtime must be a mapping")
            else:
                runtime_package = pinned_runtime.get("package")
                runtime_version = pinned_runtime.get("version")
                runtime_package_json = pinned_runtime.get("package_json")
                runtime_fields = (runtime_package, runtime_version, runtime_package_json)
                if not all(isinstance(value, str) and value for value in runtime_fields):
                    manifest_issues.append(
                        f"{name}: pinned_runtime requires package, version, and package_json"
                    )
                else:
                    runtime_key = f"runtime:{runtime_package}"
                    runtime_path = root / runtime_package_json
                    runtime_ready = False
                    if runtime_path.is_file():
                        try:
                            runtime_metadata = json.loads(
                                runtime_path.read_text(encoding="utf-8")
                            )
                        except (OSError, json.JSONDecodeError) as exc:
                            issues.append(
                                f"cannot read runtime metadata for {runtime_package}: {exc}"
                            )
                        else:
                            runtime_ready = (
                                runtime_metadata.get("name") == runtime_package
                                and runtime_metadata.get("version") == runtime_version
                            )
                    prerequisites[runtime_key] = "ready" if runtime_ready else "missing"
                    if not runtime_ready:
                        issues.append(
                            f"required runtime is missing or has the wrong version: "
                            f"{runtime_package}@{runtime_version}"
                        )

        minimum = requires.get("node_min_major")
        if minimum is not None:
            if not isinstance(minimum, int) or minimum < 1:
                manifest_issues.append(f"{name}: node_min_major must be a positive integer")
            elif "node" in resolved:
                try:
                    major = _node_major(node_version_reader(resolved["node"]))
                except (OSError, subprocess.SubprocessError, ValueError) as exc:
                    issues.append(f"cannot read Node.js version: {exc}")
                    prerequisites["node"] = "missing"
                else:
                    if major is None or major < minimum:
                        issues.append(f"Node.js is below required major {minimum}")
                        prerequisites["node"] = "missing"

        if requires.get("chrome") is True:
            chrome_status = "ready" if chrome_exists() else "missing"
            prerequisites["chrome"] = chrome_status
            if chrome_status == "missing":
                issues.append("Chrome or Chromium is missing")
        if requires.get("chrome_extension"):
            prerequisites["chrome_extension"] = "manual_action_required"
            issues.append("Chrome extension requires manual verification")
        if requires.get("authenticated_sites"):
            prerequisites["authenticated_sites"] = "manual_action_required"
            issues.append("platform login state requires manual verification")
        npm_packages = requires.get("npm_packages", [])
        if npm_packages and not isinstance(npm_packages, list):
            manifest_issues.append(f"{name}: requires.npm_packages must be a list")
            npm_packages = []
        for package in npm_packages:
            if isinstance(package, str):
                prerequisites["npm_packages"] = "manual_action_required"
                issues.append("pinned local npm dependencies require manual installation")
                continue
            if not isinstance(package, dict):
                manifest_issues.append(
                    f"{name}: npm package requirements must be strings or mappings"
                )
                continue
            package_name = package.get("name")
            expected_version = package.get("version")
            package_json_value = package.get("package_json")
            package_fields = (package_name, expected_version, package_json_value)
            if not all(isinstance(value, str) and value for value in package_fields):
                manifest_issues.append(
                    f"{name}: npm package mapping requires name, version, and package_json"
                )
                continue
            package_key = f"npm_package:{package_name}"
            package_json_path = root / package_json_value
            package_ready = False
            if package_json_path.is_file():
                try:
                    package_metadata = json.loads(package_json_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    issues.append(f"cannot read npm package metadata for {package_name}: {exc}")
                else:
                    package_ready = (
                        package_metadata.get("name") == package_name
                        and package_metadata.get("version") == expected_version
                    )
            prerequisites[package_key] = "ready" if package_ready else "missing"
            if not package_ready:
                issues.append(
                    f"required npm package is missing or has the wrong version: "
                    f"{package_name}@{expected_version}"
                )

        real_calls_enabled = entry["real_calls_enabled"] is True
        blocking = {"missing", "manual_action_required"}
        locally_ready = (
            installed
            and source_installed
            and source_verified
            and all(status not in blocking for status in prerequisites.values())
            and probe_status == "ready"
        )
        reports[name] = SkillVerification(
            name=name,
            installed=installed,
            source_installed=source_installed,
            source_verified=source_verified,
            locally_ready=locally_ready,
            real_calls_enabled=real_calls_enabled,
            prerequisites=prerequisites,
            probe_status=probe_status,
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
        f"installation_audit_ok: {str(report.ok).lower()}",
    ]
    for issue in report.manifest_issues:
        lines.append(f"manifest_issue: {issue}")
    for name, skill in sorted(report.skills.items()):
        lines.append(
            f"{name}: source_installed={str(skill.source_installed).lower()} "
            f"source_verified={str(skill.source_verified).lower()} "
            f"locally_ready={str(skill.locally_ready).lower()} "
            f"real_calls_enabled={str(skill.real_calls_enabled).lower()} "
            f"probe={skill.probe_status}"
        )
        lines.extend(
            f"  prerequisite.{key}: {status}"
            for key, status in sorted(skill.prerequisites.items())
        )
        lines.extend(f"  issue: {issue}" for issue in skill.issues)
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
