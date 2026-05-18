"""Tests for the audio mashup ffmpeg command builder."""

from src import audio_mashup, mashup_planner
from src.config import PROJECT_ROOT


def test_audio_mashup():
    manifest = audio_mashup.load_manifest(PROJECT_ROOT / "data" / "audio_manifest.example.json")
    plan = mashup_planner.build_mashup_plan("baraat, hype, punjabi, gen-z", length=5)
    clips, errors = audio_mashup.build_clip_specs(plan, manifest)

    assert not errors, f"manifest should cover the sample Baraat mashup, errors: {errors}"

    command = audio_mashup.build_ffmpeg_command(clips, audio_mashup.DEFAULT_OUTPUT)
    command_text = audio_mashup.format_command(command)

    assert command[0] == "ffmpeg"
    assert "-filter_complex" in command
    assert "concat=n=5" in command_text
    assert len(clips) == 5
