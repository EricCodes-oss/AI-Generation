"""User-gated, cross-domain hotspot candidate pools for V5 news production."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
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



class DisasterEventType(StrEnum):
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    TYPHOON = "typhoon"
    WILDFIRE = "wildfire"
    LANDSLIDE = "landslide"
    MUDSLIDE = "mudslide"
    EXTREME_HEAT = "extreme_heat"
    OTHER_NATURAL_DISASTER = "other_natural_disaster"


class LivelihoodAssessment(DomainModel):
    affected_groups: list[str] = Field(min_length=1)
    direct_interest: str = Field(min_length=1)
    effective_date: date | None = None
    previous_rule: str = Field(min_length=1)
    new_rule: str = Field(min_length=1)
    misconception_to_clarify: str = Field(min_length=1)
    required_action: str = Field(min_length=1)
    national_or_local_scope: str = Field(min_length=1)
    exceptions_and_boundaries: str = Field(min_length=1)
    direct_impact_score: int = Field(ge=0, le=25)
    recency_score: int = Field(ge=0, le=20)
    cognitive_conflict_score: int = Field(ge=0, le=20)
    affected_population_score: int = Field(ge=0, le=15)
    visual_material_score: int = Field(ge=0, le=10)
    authoritative_evidence_score: int = Field(ge=0, le=10)
    editorial_feedback_tags: list[str] = Field(default_factory=list)

    @property
    def total_score(self) -> int:
        return sum(self.score_breakdown.values())

    @property
    def score_breakdown(self) -> dict[str, int]:
        return {
            "direct_impact": self.direct_impact_score,
            "recency": self.recency_score,
            "cognitive_conflict": self.cognitive_conflict_score,
            "affected_population": self.affected_population_score,
            "visual_material": self.visual_material_score,
            "authoritative_evidence": self.authoritative_evidence_score,
        }


class DisasterAssessment(DomainModel):
    event_type: DisasterEventType
    location: str = Field(min_length=1)
    occurred_at: datetime
    status_updated_at: datetime
    active: bool
    casualties_or_missing_reported: bool = False
    mass_evacuation_reported: bool = False
    infrastructure_disruption_reported: bool = False
    official_emergency_response_started: bool = False
    secondary_risk_reported: bool = False
    authoritative_fact_source_ids: list[str] = Field(min_length=1)
    footage_time_location_verified: bool
    public_safety_value: str = Field(min_length=1)
    dignity_or_privacy_risk: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_update_time(self) -> DisasterAssessment:
        if self.status_updated_at < self.occurred_at:
            raise ValueError("disaster status update cannot precede occurrence")
        return self

    @property
    def has_concrete_impact(self) -> bool:
        return any(
            (
                self.casualties_or_missing_reported,
                self.mass_evacuation_reported,
                self.infrastructure_disruption_reported,
                self.official_emergency_response_started,
                self.secondary_risk_reported,
            )
        )

    @property
    def qualifies_for_fast_lane(self) -> bool:
        return self.active and self.has_concrete_impact


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
    livelihood_assessment: LivelihoodAssessment | None = None
    disaster_assessment: DisasterAssessment | None = None

    @model_validator(mode="after")
    def validate_ordinary_life_moment(self) -> HotspotPoolCandidate:
        if self.category is not HotspotTopicCategory.ORDINARY_LIFE_MOMENT:
            return self
        if self.ordinary_moment_assessment is None:
            raise ValueError("ordinary moment assessment is required")
        if reasons := self.ordinary_moment_assessment.rejection_reasons:
            raise ValueError("; ".join(reasons))
        return self

    @model_validator(mode="after")
    def validate_disaster_sources(self) -> HotspotPoolCandidate:
        assessment = self.disaster_assessment
        if assessment is None:
            return self
        available = {source.source_id: source for source in self.authoritative_sources}
        matched = [
            available[source_id]
            for source_id in assessment.authoritative_fact_source_ids
            if source_id in available
        ]
        reliable_types = {"primary", "official", "reputable_media"}
        if not matched or not any(source.evidence_type in reliable_types for source in matched):
            raise ValueError("authoritative disaster source must match candidate evidence")
        return self

    @property
    def livelihood_score(self) -> int:
        if self.livelihood_assessment is None:
            return 0
        return self.livelihood_assessment.total_score

    @property
    def disaster_fast_lane(self) -> bool:
        return bool(
            self.disaster_assessment
            and self.disaster_assessment.qualifies_for_fast_lane
        )


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

    def list_recent_produced_topics(self, day: date, *, cooldown_days: int) -> list[str]:
        cutoff = day - timedelta(days=cooldown_days)
        roots = [
            self.root / "hotspot-selections",
            self.root.parent / "output",
            self.root / "output",
        ]
        titles: list[str] = []
        seen_paths: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("topic-selection.json"):
                resolved = path.resolve()
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, TypeError, json.JSONDecodeError):
                    continue
                produced_day = _produced_topic_day(payload)
                approved = payload.get("approved", True)
                if produced_day is None or not approved or not cutoff <= produced_day <= day:
                    continue
                titles.extend(_produced_topic_titles(payload))
        return list(dict.fromkeys(titles))

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


def _produced_topic_day(payload: dict[str, object]) -> date | None:
    for key in ("day", "date", "selected_at", "approved_at"):
        value = str(payload.get(key) or "").strip()
        if not value:
            continue
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            continue
    run_id = str(payload.get("run_id") or "")
    if match := re.search(r"(?:19|20)\d{2}-\d{2}-\d{2}", run_id):
        return date.fromisoformat(match.group())
    return None


def _produced_topic_titles(payload: dict[str, object]) -> list[str]:
    values: list[object] = [
        payload.get("title"),
        payload.get("topic"),
        payload.get("selected_title"),
    ]
    candidate = payload.get("candidate")
    if isinstance(candidate, dict):
        values.extend(
            [
                candidate.get("title"),
                candidate.get("topic"),
                candidate.get("recommended_title"),
            ]
        )
    return list(
        dict.fromkeys(str(value).strip() for value in values if str(value or "").strip())
    )


_TOPIC_NORMALIZATION_RULES = (
    (r"三个|三名|仨|3名", "3"),
    (r"(\d+)块(\d)", r"\1.\2元"),
    (r"便利店|小超市|超市", "小店"),
    (r"倒闭|闭店|关店|停业", "闭店"),
    (r"露天焚烧|焚烧", "禁烧"),
    (r"科学精准", "精准"),
    (r"融资|赞助|鼓励|挺住", "支持"),
    (r"凑出|凑了|凑", ""),
    (r"得知|即将|老板|为|要", ""),
)


def _normalize_topic(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).lower()
    for pattern, replacement in _TOPIC_NORMALIZATION_RULES:
        normalized = re.sub(pattern, replacement, normalized)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff.]+", "", normalized)


def _ngram_dice(left: str, right: str, *, size: int) -> float:
    left_grams = {left[index : index + size] for index in range(len(left) - size + 1)}
    right_grams = {right[index : index + size] for index in range(len(right) - size + 1)}
    if not left_grams or not right_grams:
        return 0.0
    return 2 * len(left_grams & right_grams) / (len(left_grams) + len(right_grams))


_CONFLICTING_TOPIC_TERMS = (
    frozenset({"飞机", "汽车", "火车", "轮船"}),
    frozenset({"男孩", "女孩"}),
)


def _quoted_topic_names(title: str) -> set[str]:
    return {
        _normalize_topic(name)
        for name in re.findall(r"《([^》]{1,40})》", title)
        if _normalize_topic(name)
    }


def _has_conflicting_topic_terms(left: str, right: str) -> bool:
    for terms in _CONFLICTING_TOPIC_TERMS:
        left_terms = {term for term in terms if term in left}
        right_terms = {term for term in terms if term in right}
        if left_terms and right_terms and left_terms.isdisjoint(right_terms):
            return True
    return False


def _same_topic(left: str, right: str) -> bool:
    left_normalized = _normalize_topic(left)
    right_normalized = _normalize_topic(right)
    if not left_normalized or not right_normalized:
        return False
    if _has_conflicting_topic_terms(left_normalized, right_normalized):
        return False
    if left_normalized == right_normalized:
        return True
    if _quoted_topic_names(left) & _quoted_topic_names(right):
        return True
    sequence_score = SequenceMatcher(None, left_normalized, right_normalized).ratio()
    unigram_score = _ngram_dice(left_normalized, right_normalized, size=1)
    bigram_score = _ngram_dice(left_normalized, right_normalized, size=2)
    return (
        sequence_score >= 0.74
        or (unigram_score >= 0.82 and bigram_score >= 0.50)
        or (unigram_score >= 0.75 and bigram_score >= 0.60)
    )


class HotspotSelectionService:
    def __init__(
        self,
        repository: HotspotSelectionRepository,
        *,
        produced_topic_cooldown_days: int = 30,
    ) -> None:
        self.repository = repository
        self.produced_topic_cooldown_days = produced_topic_cooldown_days

    def import_pool(self, day: date, pool: HotspotCandidatePool) -> HotspotCandidatePool:
        filtered = self._exclude_recently_produced(day, pool)
        ranked = self._rank_candidates(filtered)
        self.repository.save_pool(day, ranked)
        return ranked

    @staticmethod
    def _rank_candidates(pool: HotspotCandidatePool) -> HotspotCandidatePool:
        rating_priority = {
            DirectorRating.S: 3,
            DirectorRating.A: 2,
            DirectorRating.B: 1,
            DirectorRating.NOT_RECOMMENDED: 0,
        }
        candidates = sorted(
            pool.candidates,
            key=lambda candidate: (
                candidate.disaster_fast_lane,
                candidate.livelihood_score,
                rating_priority[candidate.director_rating],
            ),
            reverse=True,
        )
        return pool.model_copy(update={"candidates": candidates})

    def _exclude_recently_produced(
        self, day: date, pool: HotspotCandidatePool
    ) -> HotspotCandidatePool:
        produced = self.repository.list_recent_produced_topics(
            day, cooldown_days=self.produced_topic_cooldown_days
        )
        candidates = [
            candidate
            for candidate in pool.candidates
            if not any(_same_topic(candidate.title, title) for title in produced)
        ]
        return pool.model_copy(update={"candidates": candidates})

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
