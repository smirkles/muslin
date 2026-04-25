"""Tests for backend/lib/cascade/prompts.py — narration loader."""

from pathlib import Path

import pytest


class TestLoadNarration:
    def test_load_narration_returns_dict_with_expected_keys(self, tmp_path: Path) -> None:
        """load_narration parses section headers and returns keyed dict."""
        prompt_dir = tmp_path / "swayback"
        prompt_dir.mkdir()
        (prompt_dir / "v1_baseline.md").write_text(
            "## step_1_intro\nStarting text.\n\n" "## step_2_fold_line\nFold line text.\n"
        )

        from lib.cascade.prompts import load_narration

        result = load_narration("swayback", version="v1_baseline", prompts_root=tmp_path)
        assert "step_1_intro" in result
        assert "step_2_fold_line" in result
        assert result["step_1_intro"] == "Starting text."

    def test_load_narration_swayback_returns_5_keys(self) -> None:
        """load_narration('swayback') returns exactly 5 keys from the real file."""
        from lib.cascade.prompts import load_narration

        result = load_narration("swayback")
        expected_keys = {
            "step_1_intro",
            "step_2_fold_line",
            "step_3_fold_wedge",
            "step_4_true_side_seam",
            "step_5_true_cb_seam",
        }
        assert set(result.keys()) == expected_keys

    def test_load_narration_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """load_narration raises FileNotFoundError for a missing prompt file."""
        from lib.cascade.prompts import load_narration

        with pytest.raises(FileNotFoundError) as exc_info:
            load_narration("nonexistent", version="v1_baseline", prompts_root=tmp_path)

        assert "nonexistent" in str(exc_info.value)

    def test_load_narration_missing_file_error_includes_path(self, tmp_path: Path) -> None:
        """FileNotFoundError message includes the attempted path."""
        from lib.cascade.prompts import load_narration

        with pytest.raises(FileNotFoundError) as exc_info:
            load_narration("cascade_x", version="v2", prompts_root=tmp_path)

        assert "v2" in str(exc_info.value)

    def test_load_narration_strips_whitespace_from_values(self, tmp_path: Path) -> None:
        """Body text is stripped of leading/trailing whitespace."""
        prompt_dir = tmp_path / "swayback"
        prompt_dir.mkdir()
        (prompt_dir / "v1_baseline.md").write_text(
            "## step_1_intro\n   Some text here.   \n\n## step_2\nNext.\n"
        )

        from lib.cascade.prompts import load_narration

        result = load_narration("swayback", version="v1_baseline", prompts_root=tmp_path)
        assert result["step_1_intro"] == "Some text here."
