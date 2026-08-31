"""Tests for smithy.windows.tools.input_text — plain text only."""

from smithy.windows.tools.input_text import _send


class TestInputText:
    def test_send_exists(self) -> None:
        # _send should be importable and callable
        assert callable(_send)
