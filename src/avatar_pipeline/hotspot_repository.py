"""Atomic, auditable persistence for imported hotspot evidence and reports."""

import json
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from pydantic import BaseModel

from avatar_pipeline.hotspot_models import (
    CandidateVerification,
    EditorialSignals,
    EventShortVideoEvidence,
    HotspotReport,
    HotspotSnapshot,
)


class SnapshotAlreadyExists(RuntimeError):
    """Raised when immutable raw evidence would be overwritten."""


class HotspotRepository:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def save_snapshot(self, day: date, snapshot: HotspotSnapshot) -> Path:
        path = self._day_root(day) / "snapshots" / f"{snapshot.snapshot_id}.json"
        if path.exists():
            raise SnapshotAlreadyExists(snapshot.snapshot_id)
        self._write_model(path, snapshot)
        return path

    def list_snapshots(self, day: date) -> list[HotspotSnapshot]:
        paths = (self._day_root(day) / "snapshots").glob("*.json")
        snapshots = [
            HotspotSnapshot.model_validate_json(path.read_text(encoding="utf-8")) for path in paths
        ]
        return sorted(snapshots, key=lambda item: item.captured_at)

    def save_verifications(self, day: date, items: list[CandidateVerification]) -> Path:
        return self._write_json(
            self._day_root(day) / "verification.json",
            [item.model_dump(mode="json") for item in items],
        )

    def load_verifications(
        self, day: date, *, missing_ok: bool = False
    ) -> dict[str, CandidateVerification]:
        path = self._day_root(day) / "verification.json"
        if missing_ok and not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = [CandidateVerification.model_validate(item) for item in payload]
        return {item.event_id: item for item in items}

    def save_short_video_evidence(
        self, day: date, items: list[EventShortVideoEvidence]
    ) -> Path:
        return self._write_json(
            self._day_root(day) / "short-video-evidence.json",
            [item.model_dump(mode="json") for item in items],
        )

    def load_short_video_evidence(
        self, day: date, *, missing_ok: bool = False
    ) -> dict[str, EventShortVideoEvidence]:
        path = self._day_root(day) / "short-video-evidence.json"
        if missing_ok and not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = [EventShortVideoEvidence.model_validate(item) for item in payload]
        return {item.event_id: item for item in items}

    def save_editorial_signals(self, day: date, items: list[EditorialSignals]) -> Path:
        return self._write_json(
            self._day_root(day) / "editorial-signals.json",
            [item.model_dump(mode="json") for item in items],
        )

    def load_editorial_signals(
        self, day: date, *, missing_ok: bool = False
    ) -> dict[str, EditorialSignals]:
        path = self._day_root(day) / "editorial-signals.json"
        if missing_ok and not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = [EditorialSignals.model_validate(item) for item in payload]
        return {item.event_id: item for item in items}

    def load_report(self, day: date) -> HotspotReport:
        path = self._day_root(day) / "reports" / "candidate-report.json"
        return HotspotReport.model_validate_json(path.read_text(encoding="utf-8"))

    def save_report(self, day: date, report: HotspotReport, markdown: str) -> tuple[Path, Path]:
        root = self._day_root(day) / "reports"
        json_path = root / "candidate-report.json"
        markdown_path = root / "candidate-report.md"
        self._write_model(json_path, report)
        self._atomic_text(markdown_path, markdown)
        return json_path, markdown_path

    def _day_root(self, day: date) -> Path:
        return self.root / "hotspots" / day.isoformat()

    def _write_model(self, path: Path, model: BaseModel) -> Path:
        return self._write_json(path, model.model_dump(mode="json"))

    def _write_json(self, path: Path, payload: Any) -> Path:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        return self._atomic_text(path, text)

    @staticmethod
    def _atomic_text(path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        normalized = text.rstrip("\n") + "\n"
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(normalized)
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
        return path
