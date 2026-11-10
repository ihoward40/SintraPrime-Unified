import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from media_render.jobs import (
    PRESET_THEMES,
    ExplainerJob,
    JobValidationError,
    LyricLine,
    LyricVideoJob,
    NarrationOptions,
    RenderResult,
    Theme,
)

THIS_FILE = Path(__file__).resolve()


def _lyric_job(**overrides):
    defaults = {
        "audio_path": str(THIS_FILE),  # any existing file stands in for audio
        "lyrics": [LyricLine("hello world", 0.5, 2.0), LyricLine("second line", 2.2, 4.0)],
        "output_path": "/tmp/media_render_test/out.mp4",
    }
    defaults.update(overrides)
    return LyricVideoJob(**defaults)


class TestLyricLineValidation(unittest.TestCase):
    def test_valid_line(self):
        LyricLine("text", 0.0, 1.0).validate()

    def test_empty_text_rejected(self):
        with pytest.raises(JobValidationError):
            LyricLine("   ", 0.0, 1.0).validate()

    def test_negative_start_rejected(self):
        with pytest.raises(JobValidationError):
            LyricLine("text", -0.1, 1.0).validate()

    def test_end_before_start_rejected(self):
        with pytest.raises(JobValidationError):
            LyricLine("text", 2.0, 2.0).validate()
        with pytest.raises(JobValidationError):
            LyricLine("text", 3.0, 2.0).validate()


class TestLyricVideoJobValidation(unittest.TestCase):
    def test_valid_job(self):
        _lyric_job().validate()

    def test_missing_audio_rejected(self):
        with pytest.raises(JobValidationError):
            _lyric_job(audio_path="/tmp/does-not-exist-track.mp3").validate()

    def test_empty_lyrics_rejected(self):
        with pytest.raises(JobValidationError):
            _lyric_job(lyrics=[]).validate()

    def test_overlapping_lyrics_rejected(self):
        with pytest.raises(JobValidationError):
            _lyric_job(
                lyrics=[
                    LyricLine("one", 0.0, 2.0),
                    LyricLine("two", 1.5, 3.0),  # overlaps "one"
                ]
            ).validate()

    def test_touching_lyrics_allowed(self):
        _lyric_job(
            lyrics=[LyricLine("one", 0.0, 2.0), LyricLine("two", 2.0, 3.0)]
        ).validate()

    def test_bad_output_extension_rejected(self):
        with pytest.raises(JobValidationError):
            _lyric_job(output_path="/tmp/out.avi").validate()

    def test_bad_dimensions_rejected(self):
        with pytest.raises(JobValidationError):
            _lyric_job(width=0).validate()
        with pytest.raises(JobValidationError):
            _lyric_job(fps=-1).validate()

    def test_duration_seconds(self):
        job = _lyric_job()
        assert job.duration_seconds == 4.0


class TestNarrationOptions(unittest.TestCase):
    def test_default_valid(self):
        NarrationOptions().validate()

    def test_unknown_engine_rejected(self):
        with pytest.raises(JobValidationError):
            NarrationOptions(engine="magic").validate()

    def test_external_file_requires_existing_audio(self):
        with pytest.raises(JobValidationError):
            NarrationOptions(engine="external-file").validate()
        with pytest.raises(JobValidationError):
            NarrationOptions(
                engine="external-file", narration_audio_path="/tmp/nope.wav"
            ).validate()
        NarrationOptions(
            engine="external-file", narration_audio_path=str(THIS_FILE)
        ).validate()

    def test_rate_bounds(self):
        with pytest.raises(JobValidationError):
            NarrationOptions(rate=0.1).validate()
        with pytest.raises(JobValidationError):
            NarrationOptions(rate=3.0).validate()

    def test_language_format(self):
        with pytest.raises(JobValidationError):
            NarrationOptions(language="english").validate()
        NarrationOptions(language="en-US").validate()


class TestExplainerJobValidation(unittest.TestCase):
    def test_valid_with_script_text(self):
        ExplainerJob(
            script_text="One. Two. Three.",
            output_path="/tmp/x.mp4",
        ).validate()

    def test_valid_with_script_path(self):
        ExplainerJob(
            script_path=str(THIS_FILE),
            output_path="/tmp/x.mp4",
        ).validate()

    def test_needs_exactly_one_script_source(self):
        with pytest.raises(JobValidationError):
            ExplainerJob(output_path="/tmp/x.mp4").validate()
        with pytest.raises(JobValidationError):
            ExplainerJob(
                script_text="hi",
                script_path=str(THIS_FILE),
                output_path="/tmp/x.mp4",
            ).validate()

    def test_blank_script_text_rejected(self):
        with pytest.raises(JobValidationError):
            ExplainerJob(script_text="   ", output_path="/tmp/x.mp4").validate()

    def test_missing_script_path_rejected(self):
        with pytest.raises(JobValidationError):
            ExplainerJob(
                script_path="/tmp/no-such-script.md", output_path="/tmp/x.mp4"
            ).validate()

    def test_script_property_resolves_both_sources(self):
        job = ExplainerJob(script_text="hello", output_path="/tmp/x.mp4")
        assert job.script == "hello"
        job2 = ExplainerJob(script_path=str(THIS_FILE), output_path="/tmp/x.mp4")
        assert "LyricLine" in job2.script


class TestThemeAndResult(unittest.TestCase):
    def test_preset_themes_exist(self):
        assert "lawful-roots" in PRESET_THEMES
        assert isinstance(PRESET_THEMES["lawful-roots"], Theme)

    def test_render_result_fields(self):
        result = RenderResult(
            job_id="abc123",
            success=True,
            output_path=Path("/tmp/out.mp4"),
            elapsed_seconds=1.5,
            command=["npx", "hyperframes", "render"],
            message="done",
        )
        assert result.success
        assert result.job_id == "abc123"


if __name__ == "__main__":
    unittest.main()
