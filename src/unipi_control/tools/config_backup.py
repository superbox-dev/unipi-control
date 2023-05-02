#!/usr/bin/env python3
import argparse
import tarfile
from datetime import date
from datetime import datetime
from pathlib import Path

import sys
from superbox_utils.argparse import init_argparse
from superbox_utils.core.exception import UnexpectedException
from superbox_utils.logging.config import LoggingConfig

from unipi_control.config import Config
from unipi_control.config import DEFAULT_CONFIG_PATH
from unipi_control.config import logger
from unipi_control.version import __version__


class UnipiConfigBackup:
    def __init__(self, config: Config) -> None:
        self.config: Config = config

    def backup(self, target: Path) -> None:
        """Backup configuration file."""
        if target.is_file():
            raise UnexpectedException("OUTPUT is a file not a directory!")

        if not target.is_dir():
            raise UnexpectedException("OUTPUT directory not exists!")

        tar_filename: str = f"config-{date.today()}-{datetime.now().strftime('%H%M%S')}.tar.gz"
        tar_file: Path = target / tar_filename

        if tar_file.exists():
            raise UnexpectedException(f"{tar_file.as_posix()} already exists!")

        try:
            with tarfile.open(tar_file, "x:gz") as tar:
                tar.add(self.config.config_base_path / "control.yaml", arcname=self.config.config_base_path)
        except IOError as error:
            raise UnexpectedException(f"{error.strerror}: '{error.filename}") from error

        logger.info("%s created!", tar_file.as_posix())


def parse_args(args: list) -> argparse.Namespace:
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
    parser.add_argument("output", help="Path to save the backup file")
    parser.add_argument(
        "-c",
        "--config",
        action="store",
        default=DEFAULT_CONFIG_PATH,
        help=f"path to the configuration (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main() -> None:
    """Entrypoint for Unipi Config Converter."""
    try:
        args: argparse.Namespace = parse_args(sys.argv[1:])

        config: Config = Config(logging=LoggingConfig(level="info"), config_base_path=Path(args.config))
        config.logging.init(log=args.log, verbose=args.verbose)

        UnipiConfigBackup(config=config).backup(target=Path(args.output))
    except UnexpectedException as error:
        logger.critical(error)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
