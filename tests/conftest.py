import logging
import shutil
import tempfile
from pathlib import Path

import pytest

from unipi_control.config import Config
from unipi_control.config import LOGGER_NAME


@pytest.fixture(autouse=True, scope="session")
def logger():
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger(LOGGER_NAME).handlers.clear()
    logging.info("Initialize logging")


class ConfigLoader:
    def __init__(self):
        self.temp_config_path: Path = Path(tempfile.mkdtemp())
        self.temp_config_file_path: Path = self.temp_config_path / "control.yaml"

        self.systemd_path = self.temp_config_path / "systemd/system"
        self.systemd_path.mkdir(parents=True)

    def write_config(self, content: str):
        with open(self.temp_config_file_path, "w") as f:
            f.write(content)

    def get_config(self) -> Config:
        return Config(
            config_base_path=self.temp_config_path,
            systemd_path=self.systemd_path,
        )

    def cleanup(self):
        shutil.rmtree(self.temp_config_path)


@pytest.fixture()
def config_loader(request) -> ConfigLoader:
    c = ConfigLoader()
    c.write_config(request.param)

    logging.info("Create configuration: %s", c.get_config())

    return c
