"""Command-line interface for the production and user-gated research workflows."""

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from avatar_pipeline.config import load_config
from avatar_pipeline.models import DailyTask, TopicCandidate, utc_now
from avatar_pipeline.query_planner import build_daily_plan
from avatar_pipeline.repository import DailyTaskRepository
from avatar_pipeline.research_adapters import CollectionBatch, RawCollectionItem
from avatar_pipeline.research_models import (
    CollectionFailure,
    CommentInsightCard,
    ResearchPlatform,
    ResearchReviewAction,
    ResearchRun,
)
from avatar_pipeline.research_repository import ResearchRunRepository
from avatar_pipeline.research_service import ResearchService
from avatar_pipeline.service import DailyWorkflowService
from avatar_pipeline.skill_contracts import load_contracts

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _PROJECT_ROOT / "configs" / "default.yaml"
_RESEARCH_LOCK = _PROJECT_ROOT / "skills" / "third_party.lock.yaml"


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

    research_init = subparsers.add_parser("research-init")
    _add_date_argument(research_init)

    research_plan = subparsers.add_parser("research-plan")
    _add_date_argument(research_plan)
    research_plan.add_argument("--directive")

    research_import = subparsers.add_parser("research-import")
    _add_date_argument(research_import)
    research_import.add_argument("--file", required=True, type=Path)
    research_import.add_argument(
        "--collector", required=True, choices=("fixture", "manual_import")
    )

    research_insights = subparsers.add_parser("research-import-insights")
    _add_date_argument(research_insights)
    research_insights.add_argument("--file", required=True, type=Path)

    research_report = subparsers.add_parser("research-report")
    _add_date_argument(research_report)

    research_revise = subparsers.add_parser("research-revise")
    _add_date_argument(research_revise)
    research_revise.add_argument(
        "--action",
        required=True,
        choices=tuple(
            action.value
            for action in ResearchReviewAction
            if action is not ResearchReviewAction.APPROVE
        ),
    )
    research_revise.add_argument("--feedback", required=True)

    research_approve = subparsers.add_parser("research-approve")
    _add_date_argument(research_approve)
    research_approve.add_argument("--actor", required=True)
    research_approve.add_argument("--accept-gap", action="append", default=[])

    research_status = subparsers.add_parser("research-status")
    _add_date_argument(research_status)

    subparsers.add_parser("research-health")
    return parser


def _task_payload(task: DailyTask) -> dict[str, Any]:
    return task.model_dump(mode="json")


def _research_payload(run: ResearchRun) -> dict[str, Any]:
    return run.model_dump(mode="json")


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


def _research_health_payload() -> dict[str, Any]:
    lock = yaml.safe_load(_RESEARCH_LOCK.read_text(encoding="utf-8"))
    entries = lock.get("skills", []) if isinstance(lock, dict) else []
    third_party = {
        entry["name"]: {
            "installed": bool(entry.get("installed")),
            "real_calls_enabled": bool(entry.get("real_calls_enabled")),
            "install_path": entry.get("install_path"),
        }
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    }
    return {
        "workflow_mode": "user_gated",
        "real_collection_enabled": any(
            item["installed"] and item["real_calls_enabled"]
            for item in third_party.values()
        ),
        "local_collectors": {
            "fixture": "ready",
            "manual_import": "ready",
            "command": "disabled_until_capability_probe",
        },
        "third_party_skills": third_party,
        "next_gate": "explicit_user_approval_before_top_recommendation",
    }


def _load_topics(path: Path) -> list[TopicCandidate]:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    items = raw.get("candidates") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("topics file must be a JSON list or contain a candidates list")
    return [TopicCandidate.model_validate(item) for item in items]


def _load_collection(path: Path, collector_name: str) -> CollectionBatch:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    items = raw.get("items") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("research source items must be a JSON list")

    raw_items: list[RawCollectionItem] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"research source items[{index}] must be an object")
        payload = item.get("payload")
        if not isinstance(payload, dict):
            raise ValueError(f"research source items[{index}].payload must be an object")
        raw_items.append(
            RawCollectionItem(
                platform=ResearchPlatform(item.get("platform")),
                query_group_id=item.get("query_group_id"),
                payload=payload,
                raw_artifact_path=str(path),
            )
        )

    failures_raw = raw.get("failures", []) if isinstance(raw, dict) else []
    if not isinstance(failures_raw, list):
        raise ValueError("research source failures must be a JSON list")
    failures = [CollectionFailure.model_validate(item) for item in failures_raw]
    timestamp = utc_now()
    return CollectionBatch(
        raw_items=raw_items,
        failures=failures,
        collector_name=collector_name,
        started_at=timestamp,
        completed_at=timestamp,
        raw_artifact_paths=[str(path)],
    )


def _load_insights(path: Path) -> list[CommentInsightCard]:
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    items = raw.get("cards") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("comment insight file must be a JSON list or contain a cards list")
    return [CommentInsightCard.model_validate(item) for item in items]


def _dispatch_research(args: argparse.Namespace) -> dict[str, Any]:
    repository = ResearchRunRepository(args.workspace)
    service = ResearchService(repository)
    if args.command == "research-init":
        run = service.start(args.date)
    elif args.command == "research-plan":
        config = load_config(_DEFAULT_CONFIG)
        history = repository.list_recent_plans(args.date, days=config.research.query.history_days)
        plan = build_daily_plan(
            args.date,
            config.research,
            history,
            user_directive=args.directive,
        )
        run = service.record_plan(args.date, plan)
    elif args.command == "research-import":
        run = service.import_collection(
            args.date,
            _load_collection(args.file, args.collector),
        )
    elif args.command == "research-import-insights":
        run = service.record_insights(args.date, _load_insights(args.file))
    elif args.command == "research-report":
        report_path = service.render_report(args.date)
        return {
            "report_path": str(report_path),
            "run": _research_payload(service.status(args.date)),
        }
    elif args.command == "research-revise":
        run = service.request_revision(
            args.date,
            feedback=args.feedback,
            action=ResearchReviewAction(args.action),
        )
    elif args.command == "research-approve":
        run = service.approve(
            args.date,
            actor=args.actor,
            accepted_gaps=args.accept_gap,
        )
    elif args.command == "research-status":
        run = service.status(args.date)
    else:  # pragma: no cover - caller limits research commands
        raise ValueError(f"unsupported research command: {args.command}")
    return _research_payload(run)


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one parsed command and return a JSON-serializable payload."""

    if args.command == "health":
        return _health_payload()
    if args.command == "research-health":
        return _research_health_payload()
    if args.command.startswith("research-"):
        return _dispatch_research(args)

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
