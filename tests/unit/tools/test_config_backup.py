from argparse import Namespace

from unipi_control.tools.config_backup import parse_args


class TestHappyPathUnipiConfigBackup:
    def test_parse_args(self) -> None:
        """Test cli arguments for 'unipi-config-backup'."""
        parser = parse_args(["-c", "config", "output"])

        assert parser.config == "config"
        assert parser.output == "output"
        assert isinstance(parser, Namespace)
