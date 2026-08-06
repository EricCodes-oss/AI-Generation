"""Command-line interface for production and user-gated research workflows."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from avatar_pipeline.config import load_config
from avatar_pipeline.models import (
    AvatarSource,
    DailyTask,
    HostProfile,
    MediaPlan,
    NewsScript,
    RunMode,
    TaskStatus,
    TopicCandidate,
    TopicSource,
    utc_now,
)
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
    init_day.add_argument("--mode", choices=[mode.value for mode in RunMode], default=config.mode)
    init_day.add_argument(
        "--topic-source",
        choices=[source.value for source in TopicSource],
        default=config.topic_source,
    )
    init_day.add_argument("--input", dest="input_text")
    init_day.add_argument("--host-image", type=Path)

    status = subparsers.add_parser("status")
    _add_date_argument(status)

    import_research = subparsers.add_parser("import-research")
    _add_date_argument(import_research)
    import_research.add_argument("--file", required=True, type=Path)

    record_plan = subparsers.add_parser("record-plan")
    _add_date_argument(record_plan)
    record_plan.add_argument("--file", required=True, type=Path)

    approve_plan = subparsers.add_parser("approve-topic-script")
    _add_date_argument(approve_plan)
    approve_plan.add_argument("--actor", required=True)

    set_host = subparsers.add_parser("set-host")
    _add_date_argument(set_host)
    set_host.add_argument("--file", required=True, type=Path)

    approve_host = subparsers.add_parser("approve-host")
    _add_date_argument(approve_host)
    approve_host.add_argument("--actor", required=True)

    for command in ("mark-tts", "mark-anchor", "mark-media", "mark-compositing"):
        command_parser = subparsers.add_parser(command)
        _add_date_argument(command_parser)
        command_parser.add_argument("--path", required=True)

    record_qc = subparsers.add_parser("record-qc")
    _add_date_argument(record_qc)
    record_qc.add_argument("--passed", required=True, choices=("true", "false"))
    record_qc.add_argument("--report", required=True)

    approve_final = subparsers.add_parser("approve-final-video")
    _add_date_argument(approve_final)
    approve_final.add_argument("--actor", required=True)

    stop = subparsers.add_parser("stop")
    _add_date_argument(stop)
    stop.add_argument("--reason", required=True)

    # Phase 2A: user-gated research workflow.
    research_init = subparsers.add_parser("research-init")
    _add_date_argument(research_init)

    research_plan = subparsers.add_parser("research-plan")
    _add_date_argument(research_plan)
    research_plan.add_argument("--directive")

    research_import = subparsers.add_parser("research-import")
    _add_date_argument(research_import)
    research_import.add_argument("--file", required=True, type=Path)
    research_import.add_argument("--collector", required=True, choices=("fixture", "manual_import"))

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
    payload = task.model_dump(mode="json")
    payload["requires_host_approval"] = task.requires_host_approval
    return payload


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
        "mode": config.mode,
        "topic_source": config.topic_source,
        "supported_modes": [RunMode.MANAGED.value, RunMode.MANUAL.value],
        "topic_sources": [TopicSource.USER_TOPIC.value, TopicSource.AUTO_HOT.value],
        "host_layout": "seated_studio_anchor",
        "manual_approval_commands": [
            "approve-topic-script",
            "approve-host",
            "approve-final-video",
        ],
        "subtitle": config.subtitle,
        "video_structure": config.video_structure,
        "media_policy": config.media_policy,
        "platforms": config.platforms,
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
            item["installed"] and item["real_calls_enabled"] for item in third_party.values()
        ),
        "local_collectors": {
            "fixture": "ready",
            "manual_import": "ready",
            "command": "disabled_until_capability_probe",
        },
        "third_party_skills": third_party,
        "next_gate": "explicit_user_approval_before_top_recommendation",
    }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_topics(path: Path) -> list[TopicCandidate]:
    raw = _load_json(path)
    items = raw.get("candidates") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("topics file must be a JSON list or contain a candidates list")
    return [TopicCandidate.model_validate(item) for item in items]


def _load_collection(path: Path, collector_name: str) -> CollectionBatch:
    raw = _load_json(path)
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
    raw = _load_json(path)
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
        run = service.import_collection(args.date, _load_collection(args.file, args.collector))
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
            args.date, feedback=args.feedback, action=ResearchReviewAction(args.action)
        )
    elif args.command == "research-approve":
        run = service.approve(args.date, actor=args.actor, accepted_gaps=args.accept_gap)
    elif args.command == "research-status":
        run = service.status(args.date)
    else:  # pragma: no cover
        raise ValueError(f"unsupported research command: {args.command}")
    return _research_payload(run)


def _latest_reusable_host(repository: DailyTaskRepository, *, before: date) -> HostProfile | None:
    for previous_day in reversed(repository.list_days()):
        if previous_day >= before:
            continue
        previous_task = repository.get(previous_day)
        previous_host = previous_task.host_profile
        if previous_host is None:
            continue
        host_was_approved = any(record.gate == "host" for record in previous_task.approvals)
        if (
            previous_task.status is not TaskStatus.READY_TO_PUBLISH
            and previous_host.is_new
            and not host_was_approved
        ):
            continue
        return previous_host.model_copy(update={"is_new": False})
    return None


def _initialize_day(
    repository: DailyTaskRepository, service: DailyWorkflowService, args: argparse.Namespace
) -> DailyTask:
    topic_source = TopicSource(args.topic_source)
    input_text = args.input_text.strip() if args.input_text else None
    if topic_source is TopicSource.USER_TOPIC and not input_text:
        raise ValueError("--input is required when --topic-source is user_topic")
    if args.host_image is not None and not args.host_image.is_file():
        raise ValueError(f"host image not found: {args.host_image}")

    task = service.start_day(args.date, mode=RunMode(args.mode), input_text=input_text)
    task.topic_source = topic_source
    if args.host_image is not None:
        task.avatar_source = AvatarSource.USER_PROVIDED
        task.host_profile = HostProfile(
            id="fixed-seated-anchor",
            display_name="固定坐播主持人",
            reference_image=str(args.host_image),
            is_new=True,
        )
    else:
        saved_host = _latest_reusable_host(repository, before=args.date)
        if saved_host is not None:
            task.avatar_source = AvatarSource.SAVED_HOST
            task.host_profile = saved_host
        else:
            task.avatar_source = AvatarSource.AGENT_DESIGNED
    return repository.save(task)


def _dispatch_production(args: argparse.Namespace) -> dict[str, Any]:
    repository = DailyTaskRepository(args.workspace)
    service = DailyWorkflowService(repository)
    if args.command == "init-day":
        task = _initialize_day(repository, service, args)
    elif args.command == "status":
        task = repository.get(args.date)
        payload = _task_payload(task)
        # The research stage is deliberately non-mutating.  Preserve the
        # legacy CLI's "created" presentation after an approved research run
        # without changing the production task on disk.
        try:
            research_run = ResearchRunRepository(args.workspace).get(args.date)
        except FileNotFoundError:
            research_run = None
        if (
            research_run is not None
            and research_run.status.value == "approved"
            and task.status.value == "input_received"
        ):
            payload["status"] = "created"
        return payload
    elif args.command == "import-research":
        task = service.record_research(args.date, _load_topics(args.file))
    elif args.command == "record-plan":
        payload = _load_json(args.file)
        task = service.record_script_and_media_plan(
            args.date,
            payload["topic_id"],
            NewsScript.model_validate(payload["script"]),
            MediaPlan.model_validate(payload["media_plan"]),
        )
    elif args.command == "approve-topic-script":
        task = service.approve_topic_script(args.date, actor=args.actor)
        if task.status is TaskStatus.MEDIA_PLANNING and task.host_profile is not None:
            task = service.set_host(
                args.date,
                task.host_profile,
                avatar_source=task.avatar_source,
            )
    elif args.command == "set-host":
        task = service.set_host(
            args.date,
            HostProfile.model_validate(_load_json(args.file)),
            avatar_source=AvatarSource.USER_PROVIDED,
        )
    elif args.command == "approve-host":
        task = service.approve_host(args.date, actor=args.actor)
    elif args.command == "mark-tts":
        task = service.mark_tts_ready(args.date, artifact_path=args.path)
    elif args.command == "mark-anchor":
        task = service.mark_anchor_ready(args.date, artifact_path=args.path)
    elif args.command == "mark-media":
        task = service.mark_media_ready(args.date, artifact_path=args.path)
    elif args.command == "mark-compositing":
        task = service.mark_compositing(args.date, artifact_path=args.path)
    elif args.command == "record-qc":
        task = service.record_qc(args.date, passed=args.passed == "true", report_path=args.report)
    elif args.command == "approve-final-video":
        task = service.approve_final_video(args.date, actor=args.actor)
    elif args.command == "stop":
        task = service.stop_task(args.date, reason=args.reason)
    else:  # pragma: no cover
        raise ValueError(f"unsupported command: {args.command}")
    return _task_payload(task)


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one parsed command and return a JSON-serializable payload."""

    if args.command == "health":
        return _health_payload()
    if args.command == "research-health":
        return _research_health_payload()
    if args.command.startswith("research-"):
        return _dispatch_research(args)
    return _dispatch_production(args)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = dispatch(args)
    except Exception as error:  # noqa: BLE001 - CLI boundary
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
