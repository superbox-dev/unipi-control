"""Collection of YAML helpers."""

from pathlib import Path
from typing import Any
from typing import Dict

import yaml

from unipi_control.helpers.exception import YamlError


class Dumper(yaml.Dumper):  # pylint: disable=too-many-ancestors
    """Custom dumper for correct indentation."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:  # noqa: ARG002
        """Disable indentless."""
        super().increase_indent(flow, indentless=False)  # type: ignore[no-untyped-call]


def yaml_dumper(content: str) -> str:
    """Convert a JSON string into a YAML string.

    Parameters
    ----------
    content: str
        JSON content as string

    Returns
    -------
    str:
        YAML content as string
    """
    data: str = yaml.dump(
        yaml.safe_load(content),
        Dumper=Dumper,
        default_flow_style=False,
    )

    return data


def yaml_loader_safe(yaml_file: Path) -> Dict[str, Any]:
    """Read a YAML file.

    Parameters
    ----------
    yaml_file: Path
        Path to the YAML file.

    Returns
    -------
    YAML file content as dict or list

    Raises
    ------
    YamlError
        Raise if the YAML file can't be read.
    """
    try:
        data: Dict[str, Any] = yaml.safe_load(yaml_file.read_text())
    except yaml.MarkedYAMLError as error:
        msg = f"Can't read YAML file!\n{error.problem_mark}"
        raise YamlError(msg) from error

    return data
