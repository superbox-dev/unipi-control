#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Union

import sys
from superbox_utils.argparse import init_argparse
from superbox_utils.core.exception import UnexpectedException
from superbox_utils.logging.config import LoggingConfig
from superbox_utils.yaml.dumper import yaml_dumper
from superbox_utils.yaml.loader import yaml_loader_safe

from unipi_control.config import Config
from unipi_control.config import logger
from unipi_control.version import __version__


class UnipiConfigConverter:
    def __init__(self, config: Config, force: bool) -> None:
        self.config: Config = config
        self.force: bool = force

    @staticmethod
    def _read_source_yaml(source: Path) -> dict:
        source_yaml: Union[dict, list] = yaml_loader_safe(source)

        if isinstance(source_yaml, dict):
            return source_yaml

        raise UnexpectedException("INPUT is not a valid YAML file!")

    def _write_target_yaml(self, target: Path, content: dict) -> None:
        if target.exists() and not self.force:
            raise UnexpectedException("OUTPUT YAML file already exists!")

        target.write_text(yaml_dumper(json.dumps(content)), encoding="utf-8")
        logger.info("YAML file written to: %s", target.as_posix())

    @staticmethod
    def _parse_modbus_register_blocks(source_yaml: dict) -> list:
        _modbus_register_blocks: list = []

        for modbus_register_block in source_yaml["modbus_register_blocks"]:
            _modbus_register_blocks.append(
                {
                    "slave": modbus_register_block["board_index"],
                    "start_reg": modbus_register_block["start_reg"],
                    "count": modbus_register_block["count"],
                }
            )

        return _modbus_register_blocks

    @staticmethod
    def _parse_modbus_features(source_yaml: dict) -> list:
        _modbus_features: list = []

        for modbus_feature in source_yaml["modbus_features"]:
            if modbus_feature["type"] in {"DI", "DO", "LED", "RO"}:
                _modbus_feature: dict = {
                    "feature_type": modbus_feature["type"],
                    "count": modbus_feature["count"],
                    "major_group": modbus_feature["major_group"],
                    "val_reg": modbus_feature["val_reg"],
                }

                if val_coil := modbus_feature.get("val_coil"):
                    _modbus_feature["val_coil"] = val_coil

                _modbus_features.append(_modbus_feature)

        return _modbus_features

    def convert(self, source: Path, target: Path) -> None:
        """Convert Evok to Unipi Control YAML file format."""
        if not source.is_file():
            raise UnexpectedException("INPUT is not a file!")

        if target.is_file():
            raise UnexpectedException("OUTPUT is a file not a directory!")

        if not target.is_dir():
            raise UnexpectedException("OUTPUT directory not exists!")

        source_yaml: dict = self._read_source_yaml(source)
        target_yaml: dict = {
            "modbus_register_blocks": self._parse_modbus_register_blocks(source_yaml),
            "modbus_features": self._parse_modbus_features(source_yaml),
        }

        self._write_target_yaml(target=target / source.name, content=target_yaml)


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
    parser.add_argument("input", help="path to the evok YAML file")
    parser.add_argument("output", help="path to save the converted YAML file")
    parser.add_argument("-f", "--force", action="store_true", help="overwrite output YAML file if already exists")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main() -> None:
    """Entrypoint for Unipi Config Converter."""
    try:
        args: argparse.Namespace = parse_args(sys.argv[1:])

        config: Config = Config(logging=LoggingConfig(level="info"))
        config.logging.init(log=args.log, verbose=args.verbose)

        UnipiConfigConverter(config=config, force=args.force).convert(source=Path(args.input), target=Path(args.output))
    except UnexpectedException as error:
        logger.critical(error)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
