"""Fail-closed clearance checks for inserted news media.

Research evidence and production assets are deliberately separate.  A platform
URL can prove that a topic is hot, but it cannot by itself grant permission to
put that platform video in the final edit.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import Field

from avatar_pipeline.models import DomainModel
from avatar_pipeline.research_models import MediaClearanceStatus


class MediaEvidence(DomainModel):
    """Sanitized asset metadata; never contains bytes, cookies, or tokens."""

    asset_id: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    origin_url: str | None = None
    rights_reference: str | None = None
    watermark_detected: bool = False
    logo_detected: bool = False
    account_mark_detected: bool = False
    qr_code_detected: bool = False
    ai_generated: bool = False
    non_replicative: bool = False
    ai_disclosure: str | None = None


@dataclass(frozen=True)
class MediaInspection:
    """Decision and remediation shown to the media-planning step."""

    status: MediaClearanceStatus
    production_allowed: bool
    reason: str
    fallback_plan: str


def decide_media_clearance(evidence: MediaEvidence) -> MediaInspection:
    """Return a fail-closed production decision for one candidate asset."""

    if evidence.watermark_detected:
        return _rejected_watermark("检测到平台水印")
    if evidence.logo_detected:
        return _rejected_watermark("检测到平台 Logo 或角标")
    if evidence.account_mark_detected:
        return _rejected_watermark("检测到账号昵称、用户 ID 或账号标识")
    if evidence.qr_code_detected:
        return _rejected_watermark("检测到二维码")

    if evidence.ai_generated:
        if not evidence.non_replicative:
            return _rejected_uncleared("AI 画面缺少非复刻式声明")
        if not _has_ai_disclosure(evidence.ai_disclosure):
            return _rejected_uncleared("AI 画面缺少明确的 AI 生成披露")
        return MediaInspection(
            status=MediaClearanceStatus.AI_ILLUSTRATIVE,
            production_allowed=True,
            reason="已声明为非复刻式 AI 示意画面",
            fallback_plan="保留 AI 生成标识，并避免复刻原视频人物、构图和品牌视觉。",
        )

    if evidence.origin in {"authorized_official", "official"} and evidence.rights_reference:
        return _authorized(MediaClearanceStatus.AUTHORIZED_OFFICIAL)
    if evidence.origin in {"authorized_original", "user_original"} and evidence.rights_reference:
        return _authorized(MediaClearanceStatus.AUTHORIZED_ORIGINAL)
    return _rejected_uncleared("缺少明确授权记录或素材来源不明")


def require_production_media_clearance(evidence: MediaEvidence) -> MediaInspection:
    """Raise when the asset cannot safely enter the production timeline."""

    inspection = decide_media_clearance(evidence)
    if not inspection.production_allowed:
        raise ValueError(f"production media rejected: {inspection.reason}")
    return inspection


def _authorized(status: MediaClearanceStatus) -> MediaInspection:
    return MediaInspection(
        status=status,
        production_allowed=True,
        reason="已提供授权记录且未发现水印或平台标识",
        fallback_plan="保留授权记录，合成前后再次执行水印与账号标识检查。",
    )


def _rejected_watermark(reason: str) -> MediaInspection:
    return MediaInspection(
        status=MediaClearanceStatus.REJECTED_WATERMARK,
        production_allowed=False,
        reason=f"{reason} (watermark_or_branding_gate)",
        fallback_plan=(
            "不得裁剪、遮挡、模糊或 AI 擦除；改用授权无水印素材或 Seedance 2.0 AI 示意画面。"
        ),
    )


def _rejected_uncleared(reason: str) -> MediaInspection:
    return MediaInspection(
        status=MediaClearanceStatus.REJECTED_UNCLEARED,
        production_allowed=False,
        reason=reason,
        fallback_plan="改用有明确授权的无水印素材；没有时使用 Seedance 2.0 非复刻式 AI 示意画面。",
    )


def _has_ai_disclosure(disclosure: str | None) -> bool:
    if not disclosure or not disclosure.strip():
        return False
    normalized = disclosure.casefold()
    return "ai" in normalized or "人工智能" in disclosure or "生成" in disclosure
