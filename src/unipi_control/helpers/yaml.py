from pathlib import Path
from typing import Union

import yaml  # type: ignore
import yaml  # type: ignore
from yaml import Loader

from unipi_control.exception import ConfigException


class Dumper(yaml.Dumper):  # pylint: disable=too-many-ancestors
    """Custom dumper for correct indentation."""

    def increase_indent(self, flow=False, indentless=False):
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
        yaml.load(content, Loader=Loader),
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
        return yaml.load(yaml_file.read_text(), Loader=yaml.FullLoader)
    except yaml.MarkedYAMLError as error:
        raise ConfigException(f"Can't read YAML file!\n{str(error.problem_mark)}") from error
