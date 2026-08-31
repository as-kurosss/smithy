"""Tests for smithy.windows.tools.input_text — normalize_input."""

from smithy.windows.tools.input_text import normalize_input


class TestNormalizeInput:
    def test_plain_text_unchanged(self) -> None:
        assert normalize_input("Hello World") == "Hello World"

    def test_literal_ctrl_not_in_brackets(self) -> None:
        # No brackets → literal text
        assert normalize_input("CTRL") == "CTRL"

    def test_literal_ctrl_s_not_in_brackets(self) -> None:
        assert normalize_input("CTRL+S") == "CTRL+S"

    def test_bracket_single_key(self) -> None:
        assert normalize_input("[CTRL]") == "{CTRL}"

    def test_bracket_hold_release(self) -> None:
        assert normalize_input("[+CTRL]A[-CTRL]") == "{+CTRL}A{-CTRL}"

    def test_bracket_complex(self) -> None:
        result = normalize_input("[+CTRL][+SHIFT]A[-SHIFT][-CTRL]")
        assert result == "{+CTRL}{+SHIFT}A{-SHIFT}{-CTRL}"

    def test_mixed_text_and_keys(self) -> None:
        assert normalize_input("Hello [CTRL]") == "Hello {CTRL}"

    def test_literal_text_with_plus(self) -> None:
        assert normalize_input("2+2") == "2+2"

    def test_literal_enter(self) -> None:
        assert normalize_input("enter") == "enter"

    def test_bracket_enter(self) -> None:
        assert normalize_input("[enter]") == "{ENTER}"

    def test_sherpa_hello_world(self) -> None:
        result = normalize_input("[+SHIFT]Hello[-SHIFT]")
        assert result == "{+SHIFT}Hello{-SHIFT}"
