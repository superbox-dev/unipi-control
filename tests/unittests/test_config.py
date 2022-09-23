import shutil
import tempfile
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture

from unipi_control.config import Config
from unittests.test_config_data import CONFIG_INVALID_DEVICE_NAME


class TestUnhappyPathConfig:
    def test_invalid_device_name(self, caplog: LogCaptureFixture):
        temp_config_path: Path = Path(tempfile.mkdtemp())
        temp_config_file_path: Path = temp_config_path / "control.yaml"

        with open(temp_config_file_path, "w") as f:
            f.write(CONFIG_INVALID_DEVICE_NAME)

        with pytest.raises(SystemExit) as error:
            Config(config_base_path=temp_config_path)
            assert 1 == error.value

        shutil.rmtree(temp_config_path)

        logs: list = [record.getMessage() for record in caplog.records]

        assert (
            "[CONFIG] Invalid value 'Invalid Device Name' in 'device_name'. The following 7characters are prohibited: A-Z a-z 0-9 -_"
            in logs
        )
