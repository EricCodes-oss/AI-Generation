from pathlib import Path

from avatar_pipeline.skill_contracts import SkillKind, load_contracts


def test_required_external_skill_contracts_are_declared():
    contracts = load_contracts(Path("skills/contracts"))
    assert set(contracts) == {SkillKind.TTS, SkillKind.AVATAR, SkillKind.SEEDANCE}
    assert contracts[SkillKind.AVATAR].primary_mode == "image_plus_audio"
    assert contracts[SkillKind.AVATAR].fallback_mode == "image_plus_text"
    assert contracts[SkillKind.SEEDANCE].required_outputs == ["video_path", "task_id"]
    assert contracts[SkillKind.TTS].real_generation_enabled is False
