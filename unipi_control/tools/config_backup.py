#!/usr/bin/env python3
"""Backup Unipi Control configuration."""

import argparse
import sys
import tarfile
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import List
from typing import Optional

from unipi_control import __version__  # type: ignore[attr-defined]
from unipi_control.config import Config
from unipi_control.config import DEFAULT_CONFIG_DIR
from unipi_control.config import LoggingConfig
from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.argparse import init_argparse
from unipi_control.helpers.exception import UnexpectedError
from unipi_control.helpers.log import SIMPLE_LOG_FORMAT


class UnipiConfigBackup:
    def __init__(self, config: Config) -> None:
        self.config: Config = config

    def backup(self, target_dir: Path) -> None:
        """Backup configuration file."""
        exception_message: Optional[str] = None

        if target_dir.is_file():
            exception_message = "OUTPUT is a file not a directory!"
        elif not target_dir.is_dir():
            exception_message = "OUTPUT directory not exists!"

        if exception_message:
            raise UnexpectedError(exception_message)

        datetime_now = datetime.now(tz=timezone.utc)
        tar_filename: str = f"config-{datetime_now.date()}-{datetime_now.strftime('%H%M%S')}.tar.gz"
        tar_file: Path = target_dir / tar_filename
        tar_file.unlink(missing_ok=True)

        try:
            with tarfile.open(tar_file, "x:gz") as tar:
                tar.add(self.config.config_base_dir / "control.yaml", arcname=self.config.config_base_dir)
        except OSError as error:
            exception_message = f"{error.strerror}: '{error.filename}'"
            raise UnexpectedError(exception_message) from error

        UNIPI_LOGGER.info("%s created!", tar_file.as_posix())


def parse_args(args: List[str]) -> argparse.Namespace:
    """Initialize argument parser options.

    Parameters
    ----------
    args: list
        Arguments as list.

    Returns
    -------
    Argparse namespace
    """
    parser: argparse.ArgumentParser = init_argparse(description="Backup Unipi Control configuration")
    parser.add_argument("output", help="path to save the backup file")
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        default=DEFAULT_CONFIG_DIR,
        help=f"path to the configuration (default: {DEFAULT_CONFIG_DIR})",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main(argv: Optional[List[str]] = None) -> None:
    """Entrypoint for Unipi Config Converter."""
    if argv is None:
        argv = sys.argv[1:]

    try:
        args: argparse.Namespace = parse_args(argv)

        config: Config = Config(logging=LoggingConfig(level="info"), config_base_dir=Path(args.config))
        config.logging.init(log=args.log, verbose=args.verbose, fmt=SIMPLE_LOG_FORMAT)

        UnipiConfigBackup(config=config).backup(target_dir=Path(args.output))
    except UnexpectedError as error:
        UNIPI_LOGGER.critical(error)
        sys.exit(1)
    except KeyboardInterrupt:
        ...
