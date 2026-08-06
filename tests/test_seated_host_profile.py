import pytest
from pydantic import ValidationError

from avatar_pipeline.models import AvatarLayout, HostProfile


def test_host_profile_uses_fixed_seated_news_anchor_defaults():
    host = HostProfile(
        id="host-main",
        display_name="林知遥",
        reference_image="hosts/main.png",
    )

    assert host.layout is AvatarLayout.SEATED_STUDIO_ANCHOR
    assert host.age_range == "30-36"
    assert host.outfit == "deep_navy_blazer_ivory_blouse"
    assert host.mouth_unobstructed is True


def test_host_profile_rejects_non_seated_layout():
    with pytest.raises(ValidationError, match="seated_studio_anchor"):
        HostProfile(
            id="host-main",
            display_name="林知遥",
            reference_image="hosts/main.png",
            layout="standing_studio_anchor",
        )


def test_host_profile_rejects_obstructed_mouth():
    with pytest.raises(ValidationError, match="mouth_unobstructed"):
        HostProfile(
            id="host-main",
            display_name="林知遥",
            reference_image="hosts/main.png",
            mouth_unobstructed=False,
        )


def test_host_profile_defaults_to_selected_presenter_voice():
    host = HostProfile(
        id="host-main",
        display_name="林知遥",
        reference_image="hosts/main.png",
    )

    assert host.voice_id == "宣传女生Pro:clone_20260806_114837_980375"
