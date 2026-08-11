"""Application service for deterministic hotspot evaluation and reporting."""

from datetime import date

from avatar_pipeline.candidate_verifier import verify_candidate
from avatar_pipeline.config import HotspotConfig
from avatar_pipeline.event_clusterer import cluster_events
from avatar_pipeline.hotspot_models import EvaluatedHotspot, GateDecision, HotspotReport
from avatar_pipeline.hotspot_report import build_hotspot_report, render_hotspot_markdown
from avatar_pipeline.hotspot_repository import HotspotRepository
from avatar_pipeline.trend_analyzer import analyze_event_trend
from avatar_pipeline.virality_gate import evaluate_virality_gate
from avatar_pipeline.virality_scorer import score_virality


class HotspotService:
    def __init__(self, repository: HotspotRepository, config: HotspotConfig) -> None:
        self.repository = repository
        self.config = config

    def build_report(self, day: date) -> HotspotReport:
        snapshots = self.repository.list_snapshots(day)
        if not snapshots:
            raise ValueError(f"no hotspot snapshots stored for {day.isoformat()}")
        records = [record for snapshot in snapshots for record in snapshot.records]
        failures = [failure for snapshot in snapshots for failure in snapshot.failures]
        verifications = self.repository.load_verifications(day, missing_ok=True)
        editorial_signals = self.repository.load_editorial_signals(day, missing_ok=True)
        evaluations = []
        for event in cluster_events(records, aliases=self.config.event_aliases):
            evidence = verifications.get(event.event_id)
            editorial = editorial_signals.get(event.event_id)
            event_trend = analyze_event_trend(
                event,
                snapshots,
                related_subtopic_ids=(evidence.related_subtopic_ids if evidence else ()),
            )
            missing = [
                name
                for name, value in (
                    ("missing_verification", evidence),
                    ("missing_editorial_signals", editorial),
                )
                if value is None
            ]
            if missing:
                evaluations.append(
                    EvaluatedHotspot(
                        cluster=event,
                        trend=event_trend,
                        gate=GateDecision(
                            event_id=event.event_id,
                            passed=False,
                            checks={},
                            reasons=missing,
                        ),
                    )
                )
                continue
            verified = verify_candidate(
                event,
                evidence,
                as_of=snapshots[-1].captured_at,
                max_age_hours=self.config.max_event_age_hours,
            )
            gate = evaluate_virality_gate(event, event_trend, records, verified, self.config)
            score = (
                score_virality(
                    event,
                    event_trend,
                    records,
                    evidence,
                    verified,
                    editorial,
                    gate,
                    self.config,
                )
                if gate.passed
                else None
            )
            evaluations.append(
                EvaluatedHotspot(
                    cluster=event,
                    trend=event_trend,
                    gate=gate,
                    score=score,
                    verification=evidence,
                    editorial_signals=editorial,
                )
            )
        report = build_hotspot_report(
            day=day,
            rule_version=self.config.rule_version,
            snapshot_ids=[item.snapshot_id for item in snapshots],
            failures=failures,
            evaluations=evaluations,
            display_score_min=self.config.display_score_min,
            strong_score_min=self.config.strong_score_min,
            director_score_min=self.config.director_score_min,
            max_candidates=self.config.max_candidates,
        )
        self.repository.save_report(day, report, render_hotspot_markdown(report))
        return report
