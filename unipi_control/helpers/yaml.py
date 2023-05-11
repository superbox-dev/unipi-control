from pathlib import Path
from typing import Union

import yaml

from unipi_control.exception import ConfigError


class Dumper(yaml.Dumper):  # pylint: disable=too-many-ancestors
    """Custom dumper for correct indentation."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        """Disable indentless."""
        return super().increase_indent(flow, False)


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
    return yaml.dump(
        yaml.safe_load(content),
        Dumper=Dumper,
        default_flow_style=False,
    )


def yaml_loader_safe(yaml_file: Path) -> Union[dict, list]:
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
    ConfigException
        Raise if the YAML file can't be read.
    """
    try:
        return yaml.safe_load(yaml_file.read_text())
    except yaml.MarkedYAMLError as error:
        msg = f"Can't read YAML file!\n{str(error.problem_mark)}"
        raise ConfigError(msg) from error
