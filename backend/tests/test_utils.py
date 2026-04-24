"""Unit tests for backend/lib/utils.py — reverse_string function."""

import pytest

from lib.utils import reverse_string


class TestReverseStringHappyPath:
    def test_basic_string(self) -> None:
        assert reverse_string("hello") == "olleh"

    def test_empty_string(self) -> None:
        assert reverse_string("") == ""

    def test_unicode_string(self) -> None:
        # Reversal is by codepoint (standard Python slice behaviour).
        assert reverse_string("café") == "éfac"

    def test_single_char(self) -> None:
        assert reverse_string("a") == "a"

    def test_palindrome(self) -> None:
        assert reverse_string("racecar") == "racecar"


class TestReverseStringTypeErrors:
    def test_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            reverse_string(None)  # type: ignore[arg-type]

    def test_int_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            reverse_string(42)  # type: ignore[arg-type]

    def test_list_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            reverse_string(["h", "i"])  # type: ignore[arg-type]

    def test_bytes_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            reverse_string(b"hello")  # type: ignore[arg-type]
