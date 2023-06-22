"""Integration tests for unipi-config-backup cli command."""
import re
import tarfile
from typing import List, TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from pytest_mock import MockerFixture

from tests.conftest import ConfigLoader
from tests.conftest_data import CONFIG_CONTENT
from tests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.tools.config_backup import main

if TYPE_CHECKING:
    from pathlib import Path


class TestHappyPathUnipiConfigBackup:
    @pytest.mark.parametrize(
        "config_loader",
        [
            (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
        ],
        indirect=["config_loader"],
    )
    def test_unipi_config_backup(self, config_loader: ConfigLoader, caplog: LogCaptureFixture) -> None:
        """Test for config backup."""
        backup_path: Path = config_loader.temp_path / "backup"
        backup_path.mkdir()

        main([backup_path.as_posix(), "-c", config_loader.temp.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]
        files: List[Path] = list(backup_path.glob("*.tar.gz"))

        assert len(logs) == 1
        assert len(files) == 1
        assert re.match(r"^.*/config-\d{4}-\d{2}-\d{2}-\d{6}\.tar\.gz$", files[0].as_posix())
        assert ".tar.gz created!" in logs[0]


class TestUnhappyPathUnipiConfigBackup:
    @pytest.mark.parametrize(
        "config_loader",
        [
            (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
        ],
        indirect=["config_loader"],
    )
    def test_cli_output_directory_not_exists(self, config_loader: ConfigLoader, caplog: LogCaptureFixture) -> None:
        """Test for missing output directory."""
        with pytest.raises(SystemExit) as error:
            main([(config_loader.temp_path / "not_exists").as_posix(), "-c", config_loader.temp.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert len(logs) == 1
        assert "OUTPUT directory not exists!" in logs
        assert error.value.code == 1

    @pytest.mark.parametrize(
        "config_loader",
        [
            (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
        ],
        indirect=["config_loader"],
    )
    def test_cli_output_is_not_a_directory(self, config_loader: ConfigLoader, caplog: LogCaptureFixture) -> None:
        """Test for output is not a directory."""
        with pytest.raises(SystemExit) as error:
            main([config_loader.config_file_path.as_posix(), "-c", config_loader.temp.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert len(logs) == 1
        assert "OUTPUT is a file not a directory!" in logs
        assert error.value.code == 1

    @pytest.mark.parametrize(
        "config_loader",
        [
            (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
        ],
        indirect=["config_loader"],
    )
    def test_cli_tarfile_error(
        self, config_loader: ConfigLoader, caplog: LogCaptureFixture, mocker: MockerFixture
    ) -> None:
        """Test for tarfile error."""
        mock_tar_add = MagicMock()
        mock_tar_add.side_effect = OSError("MOCKED", "MOCKED", "MOCKED")
        mock_tarfile_open = mocker.patch.object(tarfile, "open")
        mock_tarfile_open.return_value.__enter__.return_value.add = mock_tar_add

        backup_path: Path = config_loader.temp_path / "backup"
        backup_path.mkdir()

        with pytest.raises(SystemExit) as error:
            main([backup_path.as_posix(), "-c", config_loader.temp.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "MOCKED: 'MOCKED'" in logs
        assert error.value.code == 1
