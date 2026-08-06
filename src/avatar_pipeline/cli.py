"""Non-interactive CLI for the dual-mode hotspot news-anchor workflow."""

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

from avatar_pipeline.config import load_config
from avatar_pipeline.models import (
    DailyTask,
    HostProfile,
    MediaPlan,
    NewsScript,
    RunMode,
    TopicCandidate,
    TopicSource,
)
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


def _add_date_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date", required=True, type=_date)


def build_parser() -> argparse.ArgumentParser:
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

    for command, kind in (
        ("mark-tts", "master_audio"),
        ("mark-anchor", "anchor_video"),
        ("mark-media", "insert_media"),
        ("mark-compositing", "master_video"),
    ):
        command_parser = subparsers.add_parser(command)
        _add_date_argument(command_parser)
        command_parser.add_argument("--path", required=True)
        command_parser.set_defaults(artifact_kind=kind)

    record_qc = subparsers.add_parser("record-qc")
    _add_date_argument(record_qc)
    record_qc.add_argument("--passed", required=True, choices=["true", "false"])
    record_qc.add_argument("--report", required=True)

    approve_final = subparsers.add_parser("approve-final-video")
    _add_date_argument(approve_final)
    approve_final.add_argument("--actor", required=True)

    stop = subparsers.add_parser("stop")
    _add_date_argument(stop)
    stop.add_argument("--reason", required=True)
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
            "version": ".".join(map(str, sys.version_info[:3])),
        },
        "ffmpeg": {
            "available": ffmpeg_path is not None and ffprobe_path is not None,
            "ffmpeg_path": ffmpeg_path,
            "ffprobe_path": ffprobe_path,
        },
        "mode": config.mode,
        "topic_source": config.topic_source,
        "subtitle": config.subtitle,
        "video_structure": config.video_structure,
        "media_policy": config.media_policy,
        "platforms": config.platforms,
        "skills": {
            kind.value: manifest.model_dump(mode="json")
            for kind, manifest in sorted(contracts.items(), key=lambda item: item[0].value)
        },
    }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_topics(path: Path) -> list[TopicCandidate]:
    raw = _load_json(path)
    items = raw.get("candidates") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        raise ValueError("research file must be a JSON list or contain candidates")
    return [TopicCandidate.model_validate(item) for item in items]


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "health":
        return _health_payload()
    repository = DailyTaskRepository(args.workspace)
    service = DailyWorkflowService(repository)
    if args.command == "init-day":
        task = service.start_day(args.date, mode=RunMode(args.mode), input_text=args.input_text)
    elif args.command == "status":
        task = repository.get(args.date)
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
    elif args.command == "set-host":
        task = service.set_host(args.date, HostProfile.model_validate(_load_json(args.file)))
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
