#!/usr/bin/env python3
import argparse
from pathlib import Path
from typing import Union

import sys
from superbox_utils.argparse import init_argparse
from superbox_utils.core.exception import UnexpectedException
from superbox_utils.yaml.loader import yaml_loader_safe

from unipi_control.config import Config
from unipi_control.config import logger
from unipi_control.log import LOG_NAME
from unipi_control.version import __version__


class UnipiConfigConverter:
    def __init__(self, config: Config) -> None:
        self.config: Config = config

    def _read_source_yaml(self, source: Path) -> dict:
        source_yaml: Union[dict, list] = yaml_loader_safe(source)

        if isinstance(source_yaml, dict):
            return source_yaml

        raise UnexpectedException("INPUT is not a valid YAML file!")

    def _parse_modbus_register_blocks(self, modbus_register_blocks):
        _modbus_register_blocks = []

        # for modbus_register_block in modbus_register_blocks:

    def convert(self, source: Path, target: Path):
        """Convert Evok to Unipi Control YAML file format."""
        if not source.is_file():
            raise UnexpectedException("INPUT is not a file!")

        if target.is_file():
            raise UnexpectedException("OUTPUT is a file not a directory!")

        if not target.is_dir():
            raise UnexpectedException("OUTPUT directory not exists!")

        source_yaml: dict = self._read_source_yaml(source)

        self._parse_modbus_register_blocks(source_yaml)


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
    parser: argparse.ArgumentParser = init_argparse(description="Convert Evok to Unipi Control YAML file format")
    parser.add_argument("input", help="Path to the evok YAML file")
    parser.add_argument("output", help="Path to save the converted YAML file")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main() -> None:
    """Entrypoint for Unipi Config Converter."""
    try:
        args: argparse.Namespace = parse_args(sys.argv[1:])

        config: Config = Config()
        config.logging.init(LOG_NAME, log=args.log, log_path=Path("/var/log"), verbose=args.verbose)

        UnipiConfigConverter(config=config).convert(
            source=Path(args.input),
            target=Path(args.output),
        )
    except UnexpectedException as error:
        logger.error(error)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
