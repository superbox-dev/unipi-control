"""Collection of argument parser helpers."""

import argparse

from unipi_control.helpers.log import LOG_LEVEL


def init_argparse(description: str) -> argparse.ArgumentParser:
    """Initialize argument parser with default arguments.

    Parameters
    ----------
    description: str
        Argument parser description.

    Returns
    -------
    ArgumentParser
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "-l",
        "--log",
        choices=["systemd"],
        default="stdout",
        help="set log handler to systemd",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help=f"verbose mode: multiple -v options increase the verbosity (maximum: {len(LOG_LEVEL)})",
    )

    return parser
