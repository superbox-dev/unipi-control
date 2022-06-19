from pathlib import Path

import pytest

from src.unipi_control.config import Config


@pytest.fixture()
def config():
    config = Config(
        config_base_path=Path(__file__).parent.parent.joinpath("src/unipi_control/installer/etc/unipi"),
    )

    print(config.logging.level)

    config.logging.level = "error"

    return config
