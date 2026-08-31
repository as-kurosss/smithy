"""Tests for smithy.windows.tools.input_text — normalize_input."""

from smithy.windows.tools.input_text import normalize_input


class TestNormalizeInput:
    def test_plain_text_unchanged(self) -> None:
        assert normalize_input("Hello World") == "Hello World"

    def test_modifier_combo_ctrl_s(self) -> None:
        assert normalize_input("CTRL+S") == "{CTRL}s"

    def test_modifier_combo_alt_f4(self) -> None:
        assert normalize_input("ALT+F4") == "{ALT}{F4}"

    def test_modifier_combo_ctrl_shift_s(self) -> None:
        assert normalize_input("CTRL+SHIFT+S") == "{CTRL}{SHIFT}s"

    def test_bare_key_enter(self) -> None:
        assert normalize_input("enter") == "{ENTER}"

    def test_bare_key_esc(self) -> None:
        assert normalize_input("esc") == "{ESC}"

    def test_sherpa_hold_release(self) -> None:
        assert normalize_input("[+CTRL]A[-CTRL]") == "{+CTRL}A{-CTRL}"

    def test_sherpa_press_release(self) -> None:
        assert normalize_input("[CTRL]") == "{CTRL}"

    def test_sherpa_complex(self) -> None:
        result = normalize_input("[+CTRL][+SHIFT]A[-SHIFT][-CTRL]")
        assert result == "{+CTRL}{+SHIFT}A{-SHIFT}{-CTRL}"

    def test_mixed_text_not_treated_as_combo(self) -> None:
        assert normalize_input("Hello World") == "Hello World"

    def test_partial_key_name_not_combo(self) -> None:
        # "Hello+S" — "hello" is not a known key name
        assert normalize_input("Hello+S") == "Hello+S"

    def test_unknown_key_not_combo(self) -> None:
        # "unknown" is neither a known key nor a single char → not a combo
        assert normalize_input("CTRL+unknown") == "CTRL+unknown"
