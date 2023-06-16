"""Integration tests for unipi-config-converter cli command."""
from pathlib import Path
from typing import List

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from pytest_asyncio.plugin import SubRequest

from tests.integration.tools.test_config_converter_data import (
    EVOK_MODEL_CONTENT,
    CONVERTED_MODEL_CONTENT,
    INVALID_EVOK_MODEL_CONTENT,
)
from unipi_control.tools.config_converter import main


@pytest.fixture(name="evok_hardware_yaml")
def create_evok_hardware_yaml(request: SubRequest, tmp_path: Path) -> Path:
    """Create evok hardware yaml file in temporary directory."""
    evok_hardware_path: Path = tmp_path / "evok"
    evok_hardware_path.mkdir()
    evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
    evok_hardware_yaml.write_text(request.param)

    return evok_hardware_yaml


class TestHappyPathUnipiConfigConverter:
    @pytest.mark.parametrize("evok_hardware_yaml", [EVOK_MODEL_CONTENT], indirect=["evok_hardware_yaml"])
    def test_unipi_config_converter(self, evok_hardware_yaml: Path, caplog: LogCaptureFixture) -> None:
        """Test content output of converted yaml file."""
        hardware_data_file_path = evok_hardware_yaml.parent.parent / "MOCKED_MODEL.yaml"
        main([evok_hardware_yaml.as_posix(), hardware_data_file_path.parent.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert f"YAML file written to: {hardware_data_file_path.as_posix()}" in logs
        assert hardware_data_file_path.read_text() == CONVERTED_MODEL_CONTENT


class TestUnappyPathUnipiConfigConverter:
    @pytest.mark.parametrize("evok_hardware_yaml", [INVALID_EVOK_MODEL_CONTENT], indirect=["evok_hardware_yaml"])
    def test_invalid_input_yaml_file(self, evok_hardware_yaml: Path, caplog: LogCaptureFixture) -> None:
        """Test that input yaml file raises UnexpectedError for invalid yaml file."""
        hardware_data_file_path = evok_hardware_yaml.parent.parent / "MOCKED_MODEL.yaml"

        with pytest.raises(SystemExit) as error:
            main([evok_hardware_yaml.as_posix(), hardware_data_file_path.parent.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "INPUT is not a valid YAML file!" in logs
        assert error.value.code == 1

    @pytest.mark.parametrize("evok_hardware_yaml", [EVOK_MODEL_CONTENT], indirect=["evok_hardware_yaml"])
    def test_output_yaml_file_already_exists(self, evok_hardware_yaml: Path, caplog: LogCaptureFixture) -> None:
        """Test that output yaml file raises UnexpectedError if file already exists."""
        hardware_data_file_path = evok_hardware_yaml.parent.parent / "MOCKED_MODEL.yaml"
        hardware_data_file_path.write_text(CONVERTED_MODEL_CONTENT)

        with pytest.raises(SystemExit) as error:
            main([evok_hardware_yaml.as_posix(), hardware_data_file_path.parent.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "OUTPUT YAML file already exists!" in logs
        assert error.value.code == 1

    @pytest.mark.parametrize("evok_hardware_yaml", [INVALID_EVOK_MODEL_CONTENT], indirect=["evok_hardware_yaml"])
    def test_input_is_not_a_file(self, evok_hardware_yaml: Path, caplog: LogCaptureFixture) -> None:
        """Test that input yaml file raises UnexpectedError if input is not a file."""
        hardware_data_file_path = evok_hardware_yaml.parent.parent / "MOCKED_MODEL.yaml"

        with pytest.raises(SystemExit) as error:
            main([evok_hardware_yaml.parent.as_posix(), hardware_data_file_path.parent.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "INPUT is not a file!" in logs
        assert error.value.code == 1

    @pytest.mark.parametrize("evok_hardware_yaml", [INVALID_EVOK_MODEL_CONTENT], indirect=["evok_hardware_yaml"])
    def test_output_is_a_file(self, evok_hardware_yaml: Path, caplog: LogCaptureFixture) -> None:
        """Test that output yaml directory raises UnexpectedError if output is a file."""
        hardware_data_file_path = evok_hardware_yaml.parent.parent / "MOCKED_MODEL.yaml"
        hardware_data_file_path.write_text(CONVERTED_MODEL_CONTENT)

        with pytest.raises(SystemExit) as error:
            main([evok_hardware_yaml.as_posix(), hardware_data_file_path.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "OUTPUT is a file not a directory!" in logs
        assert error.value.code == 1

    @pytest.mark.parametrize("evok_hardware_yaml", [INVALID_EVOK_MODEL_CONTENT], indirect=["evok_hardware_yaml"])
    def test_output_directory_not_exists(self, evok_hardware_yaml: Path, caplog: LogCaptureFixture) -> None:
        """Test that output yaml directory raises UnexpectedError if not exists."""
        hardware_data_file_path = evok_hardware_yaml.parent.parent / "NOT_EXISTS"

        with pytest.raises(SystemExit) as error:
            main([evok_hardware_yaml.as_posix(), hardware_data_file_path.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "OUTPUT directory not exists!" in logs
        assert error.value.code == 1
