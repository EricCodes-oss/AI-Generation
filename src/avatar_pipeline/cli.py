"""Command-line interface for the Phase 1 daily workflow."""

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

from avatar_pipeline.config import load_config
from avatar_pipeline.models import DailyTask, TopicCandidate
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.service import DailyWorkflowService
from avatar_pipeline.skill_contracts import load_contracts

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _PROJECT_ROOT / "configs" / "default.yaml"


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD") from error


def _boolean(value: str) -> bool:
    normalized = value.casefold()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise argparse.ArgumentTypeError("value must be true or false")


def _add_date_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date", required=True, type=_date)


def build_parser() -> argparse.ArgumentParser:
    """Build the public argparse command tree."""

    config = load_config(_DEFAULT_CONFIG)
    parser = argparse.ArgumentParser(prog="avatar-pipeline")
    parser.add_argument("--workspace", type=Path, default=config.storage.workspace)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health")

    init_day = subparsers.add_parser("init-day")
    _add_date_argument(init_day)

    status = subparsers.add_parser("status")
    _add_date_argument(status)

    import_topics = subparsers.add_parser("import-topics")
    _add_date_argument(import_topics)
    import_topics.add_argument("--file", required=True, type=Path)

    approve_topic = subparsers.add_parser("approve-topic")
    _add_date_argument(approve_topic)
    approve_topic.add_argument("--topic-id", required=True)
    approve_topic.add_argument("--actor", required=True)

    record_script = subparsers.add_parser("record-script")
    _add_date_argument(record_script)
    record_script.add_argument("--file", required=True, type=Path)

    approve_script = subparsers.add_parser("approve-script")
    _add_date_argument(approve_script)
    approve_script.add_argument("--actor", required=True)

    record_qc = subparsers.add_parser("record-qc")
    _add_date_argument(record_qc)
    record_qc.add_argument("--passed", required=True, type=_boolean)
    record_qc.add_argument("--report", required=True)

    approve_video = subparsers.add_parser("approve-video")
    _add_date_argument(approve_video)
    approve_video.add_argument("--actor", required=True)
    return parser


def _task_payload(task: DailyTask) -> dict[str, Any]:
    return task.model_dump(mode="json")


def _health_payload() -> dict[str, Any]:
    config = load_config(_DEFAULT_CONFIG)
    contracts_directory = config.storage.contracts_directory
    if not contracts_directory.is_absolute():
        contracts_directory = _PROJECT_ROOT / contracts_directory
    contracts = load_contracts(contracts_directory)
    ffmpeg_path = shutil.which("ffmpeg")
    ffprobe_path = shutil.which("ffprobe")
    return {
        "python": {
            "available": sys.version_info >= (3, 11),
            "version": ".".join(str(part) for part in sys.version_info[:3]),
        },
        "ffmpeg": {
            "available": ffmpeg_path is not None and ffprobe_path is not None,
            "ffmpeg_path": ffmpeg_path,
            "ffprobe_path": ffprobe_path,
        },
        "skills": {
            kind.value: manifest.model_dump(mode="json")
            for kind, manifest in sorted(contracts.items(), key=lambda item: item[0].value)
        },
    }


def _load_topics(path: Path) -> list[TopicCandidate]:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    items = raw.get("candidates") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("topics file must be a JSON list or contain a candidates list")
    return [TopicCandidate.model_validate(item) for item in items]


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one parsed command and return a JSON-serializable payload."""

    if args.command == "health":
        return _health_payload()

    repository = DailyTaskRepository(args.workspace)
    service = DailyWorkflowService(repository)
    if args.command == "init-day":
        task = service.start_day(args.date)
    elif args.command == "status":
        task = repository.get(args.date)
    elif args.command == "import-topics":
        task = service.record_research(args.date, _load_topics(args.file))
    elif args.command == "approve-topic":
        task = service.approve_topic(args.date, args.topic_id, actor=args.actor)
    elif args.command == "record-script":
        task = service.record_script(args.date, args.file.read_text(encoding="utf-8"))
    elif args.command == "approve-script":
        task = service.approve_script(args.date, actor=args.actor)
    elif args.command == "record-qc":
        task = service.record_qc(args.date, passed=args.passed, report_path=args.report)
    elif args.command == "approve-video":
        task = service.approve_video(args.date, actor=args.actor)
    else:  # pragma: no cover - argparse guarantees a known command
        raise ValueError(f"unsupported command: {args.command}")
    return _task_payload(task)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, writing success JSON to stdout and errors to stderr."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = dispatch(args)
    except Exception as error:  # noqa: BLE001 - CLI boundary converts domain errors to exit code 2
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
