"""Explicit user-gated orchestration for daily hotspot research."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
from pathlib import Path

from avatar_pipeline.browser_collection import BrowserCollectionEnvelope
from avatar_pipeline.hotspot_ranking import HotspotRankingResult, rank_hotspots
from avatar_pipeline.models import (
    ContentPillarSlug,
    FactStatus,
    NewsPillarSlug,
    SourceEvidence,
    TopicCandidate,
    utc_now,
)
from avatar_pipeline.research_adapters import CollectionBatch
from avatar_pipeline.research_models import (
    CommentInsightCard,
    DailyResearchPlan,
    HotspotReviewCard,
    PlatformEvidenceRecord,
    ResearchApprovalRecord,
    ResearchReportSummary,
    ResearchReviewAction,
    ResearchRun,
    ResearchRunStatus,
)
from avatar_pipeline.research_report import (
    build_report_summary,
    render_hotspot_review_markdown,
    render_report_markdown,
)
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

    def import_browser_evidence(
        self, day: date, envelope: BrowserCollectionEnvelope
    ) -> ResearchRun:
        """Persist sanitized real-platform evidence without requiring the legacy plan."""

        run = self.repository.get(day)
        self._require_status(
            run,
            ResearchRunStatus.DRAFT,
            ResearchRunStatus.COLLECTING,
            ResearchRunStatus.REVISION_REQUESTED,
        )
        payload = envelope.model_dump(mode="json")
        self.repository.write_artifact(day, Path("real/browser-evidence.json"), payload)
        return self._save_validated(
            run,
            status=ResearchRunStatus.COLLECTING,
            report_artifact_path=None,
        )

    def rank_browser_hotspots(
        self,
        day: date,
        metadata: dict[str, dict[str, object]],
        *,
        now: datetime | None = None,
    ) -> HotspotRankingResult:
        """Rank verified browser evidence and persist the truthful review payload."""

        run = self.repository.get(day)
        self._require_status(
            run,
            ResearchRunStatus.COLLECTING,
            ResearchRunStatus.READY_FOR_REVIEW,
            ResearchRunStatus.REVISION_REQUESTED,
        )
        evidence_payload = self.repository.read_artifact(day, Path("real/browser-evidence.json"))
        envelope = BrowserCollectionEnvelope.model_validate(evidence_payload)
        sources = [PlatformEvidenceRecord.model_validate(item) for item in envelope.items]
        ranking = rank_hotspots(sources, metadata=metadata, now=now or datetime.now(UTC))
        self.repository.write_artifact(
            day,
            Path("real/hotspot-ranking.json"),
            {
                "selected_window": ranking.selected_window.value,
                "cards": [card.model_dump(mode="json") for card in ranking.cards],
                "excluded_clusters": [
                    cluster.model_dump(mode="json") for cluster in ranking.excluded_clusters
                ],
            },
        )
        self._save_validated(
            run,
            status=ResearchRunStatus.READY_FOR_REVIEW,
            report_artifact_path=None,
        )
        return ranking

    def render_hotspot_report(self, day: date) -> Path:
        """Write Markdown for the manual hotspot confirmation gate."""

        cards = self._load_hotspot_cards(day)
        path = self.repository.write_artifact(
            day,
            Path("reports/hotspot-top3.md"),
            render_hotspot_review_markdown(cards),
        )
        run = self.repository.get(day)
        self._save_validated(run, report_artifact_path=str(path))
        return path

    def submit_hotspot_cards(self, day: date, production_service: object) -> object:
        """Bridge eligible review cards into the existing production hotspot gate."""

        candidates = [_card_to_topic_candidate(card) for card in self._load_hotspot_cards(day)]
        return production_service.record_research(day, candidates)

    def _load_hotspot_cards(self, day: date) -> list[HotspotReviewCard]:
        payload = self.repository.read_artifact(day, Path("real/hotspot-ranking.json"))
        return [HotspotReviewCard.model_validate(item) for item in payload.get("cards", [])]

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
            group.id: group.pillar for group in [*run.plan.core_groups, *run.plan.expansion_groups]
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

    def record_insights(self, day: date, cards: Iterable[CommentInsightCard]) -> ResearchRun:
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


_PILLAR_TO_NEWS = {
    ContentPillarSlug.CAREER_PRESSURE: NewsPillarSlug.WORKPLACE_LIFE,
    ContentPillarSlug.PARENT_CHILD_COMMUNICATION: NewsPillarSlug.EDUCATION,
    ContentPillarSlug.SELF_GROWTH: NewsPillarSlug.SOCIAL_PHENOMENA,
}


def _card_to_topic_candidate(card: HotspotReviewCard) -> TopicCandidate:
    sources = [
        SourceEvidence(
            source_id=item.source_id,
            platform=item.platform.value,
            title=item.title_or_caption,
            url_or_reference=item.canonical_url or item.content_id or item.source_id,
            evidence_type="primary",
            published_at=item.published_at,
            reliability_note="真实平台热度证据，仅用于研究，不自动作为成片素材。",
        )
        for item in card.platform_evidence
    ]
    sources.extend(
        SourceEvidence(
            source_id=item.source_id,
            platform=item.publisher,
            title=item.title,
            url_or_reference=item.url_or_reference,
            evidence_type="official" if item.authority_type == "official" else "reputable_media",
            published_at=item.published_at,
            reliability_note=item.summary,
        )
        for item in card.authority_evidence
        if item.verifies_fact and not item.conflicts
    )
    platforms = sorted({item.platform.value for item in card.platform_evidence})
    return TopicCandidate(
        id=card.cluster_id,
        title=card.title,
        pillar=_PILLAR_TO_NEWS[card.pillar],
        score=card.total_score,
        fact_status=FactStatus.VERIFIED,
        target_audience=card.audience_insight,
        situation=card.fact_summary,
        recommendation_reason=card.speaking_angle,
        opening_hook=card.fact_summary,
        trend_evidence=[f"平台覆盖：{', '.join(platforms)}", card.production_media_plan],
        risk_flags=card.risk_flags,
        source_evidence=sources,
        dedupe_key=card.cluster_id,
        cluster_id=card.cluster_id,
        verified_at=utc_now(),
        verification_summary=card.verification_summary,
        publishable=True,
    )
