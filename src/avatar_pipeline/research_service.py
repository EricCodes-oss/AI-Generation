"""Explicit user-gated orchestration for daily hotspot research."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path

from avatar_pipeline.research_adapters import CollectionBatch
from avatar_pipeline.research_models import (
    CommentInsightCard,
    DailyResearchPlan,
    ResearchApprovalRecord,
    ResearchReportSummary,
    ResearchReviewAction,
    ResearchRun,
    ResearchRunStatus,
)
from avatar_pipeline.research_report import build_report_summary, render_report_markdown
from avatar_pipeline.research_repository import ResearchRunRepository
from avatar_pipeline.source_normalizer import NormalizationContext, normalize_batch

Normalizer = Callable[[CollectionBatch, NormalizationContext], object]
ReportBuilder = Callable[[ResearchRun], str]
SummaryBuilder = Callable[[ResearchRun], ResearchReportSummary]

_DEFAULT_COLLECTOR_VERSIONS = {
    "fixture": "fixture-v1",
    "manual_import": "manual-v1",
    "command": "audited-command-v1",
}


class ResearchWorkflowError(RuntimeError):
    """Raised when an explicit research workflow transition is not legal."""


class ResearchService:
    """Coordinate research artifacts while stopping at the user approval gate."""

    def __init__(
        self,
        repository: ResearchRunRepository,
        *,
        normalizer: Normalizer = normalize_batch,
        report_builder: ReportBuilder = render_report_markdown,
        summary_builder: SummaryBuilder = build_report_summary,
        collector_versions: dict[str, str] | None = None,
    ) -> None:
        self.repository = repository
        self._normalizer = normalizer
        self._report_builder = report_builder
        self._summary_builder = summary_builder
        self._collector_versions = {
            **_DEFAULT_COLLECTOR_VERSIONS,
            **(collector_versions or {}),
        }

    def start(self, day: date) -> ResearchRun:
        """Start one research run without touching the production task state."""

        return self.repository.create(day)

    def record_plan(self, day: date, plan: DailyResearchPlan) -> ResearchRun:
        """Persist a reviewed query plan and open the collection step."""

        run = self.repository.get(day)
        self._require_status(
            run,
            ResearchRunStatus.DRAFT,
            ResearchRunStatus.REVISION_REQUESTED,
            ResearchRunStatus.HELD,
        )
        if plan.day != day:
            raise ValueError("research plan day must match the requested day")

        return self._save_validated(
            run,
            plan=plan,
            status=ResearchRunStatus.COLLECTING,
            report_artifact_path=None,
        )

    def import_collection(self, day: date, batch: CollectionBatch) -> ResearchRun:
        """Normalize and merge one partially successful collector batch."""

        run = self.repository.get(day)
        self._require_status(
            run,
            ResearchRunStatus.COLLECTING,
            ResearchRunStatus.REVISION_REQUESTED,
        )
        if run.plan is None:
            raise ResearchWorkflowError("a recorded research plan is required before collection")

        query_pillars = {
            group.id: group.pillar
            for group in [*run.plan.core_groups, *run.plan.expansion_groups]
        }
        context = NormalizationContext(
            collector_name=batch.collector_name,
            collector_version=self._collector_versions.get(
                batch.collector_name, f"{batch.collector_name}-unversioned"
            ),
            collected_at=batch.completed_at,
            query_pillars=query_pillars,
        )
        result = self._normalizer(batch, context)

        sources_by_id = {source.id: source for source in run.sources}
        for source in result.sources:
            sources_by_id.setdefault(source.id, source)

        return self._save_validated(
            run,
            sources=list(sources_by_id.values()),
            failures=[*run.failures, *batch.failures],
            status=ResearchRunStatus.COLLECTING,
            report_artifact_path=None,
        )

    def record_insights(
        self, day: date, cards: Iterable[CommentInsightCard]
    ) -> ResearchRun:
        """Persist comment insight cards and expose a report-ready run for review."""

        run = self.repository.get(day)
        self._require_status(
            run,
            ResearchRunStatus.COLLECTING,
            ResearchRunStatus.REVISION_REQUESTED,
            ResearchRunStatus.READY_FOR_REVIEW,
        )
        if not run.sources:
            raise ResearchWorkflowError("research sources are required before comment insights")

        cards_by_source = {card.source_id: card for card in run.insight_cards}
        for card in cards:
            cards_by_source[card.source_id] = card

        candidate = self._validated_copy(
            run,
            insight_cards=list(cards_by_source.values()),
            status=ResearchRunStatus.READY_FOR_REVIEW,
            report_artifact_path=None,
        )
        candidate.summary = self._summary_builder(candidate)
        candidate = ResearchRun.model_validate(candidate.model_dump())
        return self.repository.save(candidate)

    def render_report(self, day: date) -> Path:
        """Render the review artifact but deliberately do not approve or advance it."""

        run = self.repository.get(day)
        self._require_status(run, ResearchRunStatus.READY_FOR_REVIEW)
        relative_path = Path("reports") / f"daily-research-revision-{run.revision}.md"
        report_path = self.repository.write_artifact(
            day,
            relative_path,
            self._report_builder(run),
        )
        self._save_validated(run, report_artifact_path=relative_path.as_posix())
        return report_path

    def approve(
        self,
        day: date,
        actor: str,
        accepted_gaps: list[str] | None = None,
    ) -> ResearchRun:
        """Record explicit user approval and freeze the numbered revision."""

        run = self.repository.get(day)
        self._require_status(run, ResearchRunStatus.READY_FOR_REVIEW)
        if not run.report_artifact_path:
            raise ResearchWorkflowError("a rendered report is required before approval")

        approval = ResearchApprovalRecord(
            actor=actor,
            revision=run.revision,
            accepted_gaps=accepted_gaps or [],
        )
        if not run.is_approvable() and not approval.accepted_gaps:
            raise ResearchWorkflowError(
                "accepted gaps are required when research coverage is below the approval target"
            )

        approved = self._validated_copy(
            run,
            status=ResearchRunStatus.APPROVED,
            review_action=ResearchReviewAction.APPROVE,
            approvals=[*run.approvals, approval],
        )
        approved = self.repository.save(approved)
        self.repository.save_revision(approved)
        return approved

    def request_revision(
        self,
        day: date,
        feedback: str,
        action: ResearchReviewAction,
    ) -> ResearchRun:
        """Apply an explicit hold, supplement, return, or redo decision."""

        run = self.repository.get(day)
        self._require_status(
            run,
            ResearchRunStatus.READY_FOR_REVIEW,
            ResearchRunStatus.APPROVED,
            ResearchRunStatus.HELD,
            ResearchRunStatus.REVISION_REQUESTED,
        )
        normalized_feedback = feedback.strip()
        if not normalized_feedback:
            raise ValueError("review feedback must not be blank")
        if action is ResearchReviewAction.APPROVE:
            raise ResearchWorkflowError("use approve() for the approve action")

        revision = run.revision
        parent_revision = run.parent_revision
        if run.status is ResearchRunStatus.APPROVED:
            parent_revision = run.revision
            revision = run.revision + 1

        updates: dict[str, object] = {
            "revision": revision,
            "parent_revision": parent_revision,
            "review_action": action,
            "review_feedback": normalized_feedback,
            "report_artifact_path": None,
        }
        if action is ResearchReviewAction.HOLD:
            updates["status"] = ResearchRunStatus.HELD
        elif action is ResearchReviewAction.REDO:
            updates.update(
                status=ResearchRunStatus.DRAFT,
                plan=None,
                sources=[],
                insight_cards=[],
                failures=[],
                summary=ResearchReportSummary(),
            )
        else:
            updates["status"] = ResearchRunStatus.REVISION_REQUESTED

        return self._save_validated(run, **updates)

    def status(self, day: date) -> ResearchRun:
        """Reload the persisted current state for operator review or resume."""

        return self.repository.get(day)

    @staticmethod
    def _require_status(run: ResearchRun, *allowed: ResearchRunStatus) -> None:
        if run.status not in allowed:
            expected = ", ".join(status.value for status in allowed)
            raise ResearchWorkflowError(
                f"research run must be in {expected}; current status is {run.status.value}"
            )

    def _save_validated(self, run: ResearchRun, **updates: object) -> ResearchRun:
        return self.repository.save(self._validated_copy(run, **updates))

    @staticmethod
    def _validated_copy(run: ResearchRun, **updates: object) -> ResearchRun:
        payload = run.model_dump()
        payload.update(updates)
        return ResearchRun.model_validate(payload)
