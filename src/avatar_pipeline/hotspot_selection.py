"""User-gated, cross-domain hotspot candidate pools for V5 news production."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import Field, model_validator

from avatar_pipeline.models import DomainModel, SourceEvidence, utc_now
from avatar_pipeline.ordinary_moments import OrdinaryMomentAssessment


class HotspotTopicCategory(StrEnum):
    SOCIAL_LIVELIHOOD = "social_livelihood"
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    INTERNATIONAL = "international"
    POLICY = "policy"
    CONSUMER = "consumer"
    EDUCATION = "education"
    INFLUENCER = "influencer"
    ORDINARY_PEOPLE = "ordinary_people"
    ORDINARY_LIFE_MOMENT = "ordinary_life_moment"
    CULTURE_ENTERTAINMENT = "culture_entertainment"
    WEATHER_DISASTER = "weather_disaster"



class DirectorRating(StrEnum):
    S = "S"
    A = "A"
    B = "B"
    NOT_RECOMMENDED = "not_recommended"


class CandidatePoolStatus(StrEnum):
    AWAITING_USER_EVALUATION = "awaiting_user_evaluation"
    SELECTED = "selected"


class HotspotPoolCandidate(DomainModel):
    candidate_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: HotspotTopicCategory
    latest_development: str = Field(min_length=1)
    heat_basis: list[str] = Field(min_length=1)
    authoritative_sources: list[SourceEvidence] = Field(min_length=1)
    why_watch: str = Field(min_length=1)
    visual_material_plan: list[str] = Field(min_length=1)
    suggested_title: str = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    director_rating: DirectorRating
    preferred_media_sources: list[str] = Field(default_factory=list)
    ordinary_moment_assessment: OrdinaryMomentAssessment | None = None

    @model_validator(mode="after")
    def validate_ordinary_life_moment(self) -> HotspotPoolCandidate:
        if self.category is not HotspotTopicCategory.ORDINARY_LIFE_MOMENT:
            return self
        if self.ordinary_moment_assessment is None:
            raise ValueError("ordinary moment assessment is required")
        if reasons := self.ordinary_moment_assessment.rejection_reasons:
            raise ValueError("; ".join(reasons))
        return self


class HotspotCandidatePool(DomainModel):
    day: date
    candidates: list[HotspotPoolCandidate] = Field(max_length=8)
    status: CandidatePoolStatus = CandidatePoolStatus.AWAITING_USER_EVALUATION
    generated_at: datetime = Field(default_factory=utc_now)
    selection_rule: str = "editorial-opportunity-v2.0"

    @model_validator(mode="after")
    def validate_diversity(self) -> HotspotCandidatePool:
        ids = [item.candidate_id for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate IDs must be unique")
        return self

    @property
    def covered_categories(self) -> set[HotspotTopicCategory]:
        return {item.category for item in self.candidates}


class TopicSelectionApproval(DomainModel):
    day: date
    candidate_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: HotspotTopicCategory
    pool_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved: bool
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    approved_at: datetime = Field(default_factory=utc_now)


class HotspotSelectionRepository:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def save_pool(self, day: date, pool: HotspotCandidatePool) -> Path:
        if pool.day != day:
            raise ValueError("candidate pool day does not match target day")
        path = self._day_root(day) / "candidate-pool.json"
        self._write_json(path, pool.model_dump(mode="json"))
        return path

    def load_pool(self, day: date) -> HotspotCandidatePool:
        path = self._day_root(day) / "candidate-pool.json"
        return HotspotCandidatePool.model_validate_json(path.read_text(encoding="utf-8"))

    def pool_sha256(self, day: date) -> str:
        path = self._day_root(day) / "candidate-pool.json"
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def save_pool_report(self, day: date, markdown: str) -> Path:
        path = self._day_root(day) / "candidate-pool.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
        return path

    def pool_path(self, day: date) -> Path:
        return self._day_root(day) / "candidate-pool.json"

    def pool_report_path(self, day: date) -> Path:
        return self._day_root(day) / "candidate-pool.md"

    def selection_path(self, day: date) -> Path:
        return self._day_root(day) / "topic-selection.json"

    def save_selection(self, day: date, approval: TopicSelectionApproval) -> Path:
        if approval.day != day:
            raise ValueError("topic selection day does not match target day")
        return self._write_json(
            self._day_root(day) / "topic-selection.json",
            approval.model_dump(mode="json"),
        )

    def load_selection(self, day: date) -> TopicSelectionApproval:
        path = self._day_root(day) / "topic-selection.json"
        return TopicSelectionApproval.model_validate_json(path.read_text(encoding="utf-8"))

    def _day_root(self, day: date) -> Path:
        return self.root / "hotspot-selections" / day.isoformat()

    @staticmethod
    def _write_json(path: Path, payload: object) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            temporary = Path(handle.name)
        temporary.replace(path)
        return path


class HotspotSelectionService:
    def __init__(self, repository: HotspotSelectionRepository) -> None:
        self.repository = repository

    def import_pool(self, day: date, pool: HotspotCandidatePool) -> HotspotCandidatePool:
        self.repository.save_pool(day, pool)
        return pool

    def select(
        self,
        day: date,
        *,
        candidate_id: str,
        actor: str,
        reason: str,
    ) -> TopicSelectionApproval:
        pool = self.repository.load_pool(day)
        candidate = next(
            (item for item in pool.candidates if item.candidate_id == candidate_id),
            None,
        )
        if candidate is None:
            raise ValueError(f"candidate not found: {candidate_id}")
        approval = TopicSelectionApproval(
            day=day,
            candidate_id=candidate.candidate_id,
            title=candidate.title,
            category=candidate.category,
            pool_sha256=self.repository.pool_sha256(day),
            approved=True,
            actor=actor,
            reason=reason,
        )
        self.repository.save_selection(day, approval)
        return approval


def load_candidate_pool(path: Path) -> HotspotCandidatePool:
    return HotspotCandidatePool.model_validate_json(Path(path).read_text(encoding="utf-8"))
