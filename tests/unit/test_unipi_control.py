"""Unit tests for unipi-control entry point."""

from argparse import Namespace

from unipi_control.unipi_control import parse_args


class TestHappyPathUnipiControl:
    def test_parse_args(self) -> None:
        """Test cli arguments for 'unipi-control'."""
        parser = parse_args(["-vv"])

        assert parser.verbose == 2
        assert isinstance(parser, Namespace)
