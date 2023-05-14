from argparse import Namespace

from unipi_control.unipi_control import parse_args


class TestHappyPathUnipiControl:
    def test_parse_args(self) -> None:
        parser = parse_args(["-vv"])

        assert parser.verbose == 2
        assert isinstance(parser, Namespace)
