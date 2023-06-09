"""Integration tests for unipi-model-info cli command."""

from _pytest.capture import CaptureFixture  # pylint: disable=import-private-name

from unipi_control.tools.model_info import main


class TestHappyPathUnipiModelInfo:
    def test_unknown_model_info(self, capsys: CaptureFixture) -> None:
        """Test for unknown model."""
        main()
        assert "Name: unknown\nModel: unknown\nVersion: unknown\nSerial: unknown" in capsys.readouterr().out
