#!/usr/bin/env python3
"""Convert Evok to Unipi Control YAML file format."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from unipi_control import __version__  # type: ignore[attr-defined]
from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.argparse import init_argparse
from unipi_control.helpers.exception import UnexpectedError
from unipi_control.helpers.log import SIMPLE_LOG_FORMAT
from unipi_control.helpers.yaml import yaml_dumper
from unipi_control.helpers.yaml import yaml_loader_safe

UNIPI_LOGGER.setLevel(logging.INFO)

stdout_handler: logging.Handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(SIMPLE_LOG_FORMAT))
UNIPI_LOGGER.addHandler(stdout_handler)


class UnipiConfigConverter:
    def __init__(self, force: bool) -> None:
        self.force: bool = force

    @staticmethod
    def _read_source_yaml(source: Path) -> Dict[str, Any]:
        source_yaml: Dict[str, Any] = yaml_loader_safe(source)

        if isinstance(source_yaml, dict):
            return source_yaml

        exception_message: str = "INPUT is not a valid YAML file!"
        raise UnexpectedError(exception_message)

    def _write_target_yaml(self, target: Path, content: Dict[str, Any]) -> None:
        if target.exists() and not self.force:
            exception_message: str = "OUTPUT YAML file already exists!"
            raise UnexpectedError(exception_message)

        target.write_text(yaml_dumper(json.dumps(content)), encoding="utf-8")
        UNIPI_LOGGER.info("YAML file written to: %s", target.as_posix())

    @staticmethod
    def _parse_modbus_register_blocks(source_yaml: Dict[str, Any]) -> List[Dict[str, Any]]:
        _modbus_register_blocks: List[Dict[str, Any]] = []

        for modbus_register_block in source_yaml["modbus_register_blocks"]:
            _modbus_register_block: Dict[str, Any] = {
                "slave": modbus_register_block["board_index"],
                "start_reg": modbus_register_block["start_reg"],
                "count": modbus_register_block["count"],
            }

            _modbus_register_blocks.append(_modbus_register_block)

        return _modbus_register_blocks

    @staticmethod
    def _parse_modbus_features(source_yaml: Dict[str, Any]) -> List[Dict[str, Any]]:
        _modbus_features: List[Dict[str, Any]] = []

        for modbus_feature in source_yaml["modbus_features"]:
            if modbus_feature["type"] in {"DI", "DO", "LED", "RO"}:
                _modbus_feature: Dict[str, Any] = {
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
        exception_message: Optional[str] = None

        if not source.is_file():
            exception_message = "INPUT is not a file!"
        elif target.is_file():
            exception_message = "OUTPUT is a file not a directory!"
        elif not target.is_dir():
            exception_message = "OUTPUT directory not exists!"

        if exception_message:
            raise UnexpectedError(exception_message)

        source_yaml: Dict[str, Any] = self._read_source_yaml(source)
        target_yaml: Dict[str, Any] = {
            "modbus_register_blocks": self._parse_modbus_register_blocks(source_yaml),
            "modbus_features": self._parse_modbus_features(source_yaml),
        }

        self._write_target_yaml(target=target / source.name, content=target_yaml)


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
    parser: argparse.ArgumentParser = init_argparse(description="Convert Evok to Unipi Control YAML file format")
    parser.add_argument("input", help="path to the evok YAML file")
    parser.add_argument("output", help="path to save the converted YAML file")
    parser.add_argument("-f", "--force", action="store_true", help="overwrite output YAML file if already exists")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point for Unipi Config Converter."""
    if argv is None:
        argv = sys.argv[1:]

    try:
        args: argparse.Namespace = parse_args(argv)
        UnipiConfigConverter(force=args.force).convert(source=Path(args.input), target=Path(args.output))
    except UnexpectedError as error:
        UNIPI_LOGGER.critical(error)
        sys.exit(1)
    except KeyboardInterrupt:
        ...
