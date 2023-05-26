"""Test config converter."""

from argparse import Namespace
from pathlib import Path

import pytest

from tests.unit.conftest import ConfigLoader
from tests.unit.conftest_data import CONFIG_CONTENT
from tests.unit.tools.test_config_converter_data import CONVERTED_MODEL_CONTENT
from tests.unit.tools.test_config_converter_data import EVOK_MODEL_CONTENT
from tests.unit.tools.test_config_converter_data import INVALID_EVOK_MODEL_CONTENT
from unipi_control.helpers.exception import UnexpectedError
from unipi_control.tools.config_converter import UnipiConfigConverter
from unipi_control.tools.config_converter import parse_args


class TestHappyPathUnipiConfigConverter:
    def test_parse_args(self) -> None:
        """Test cli arguments for 'unipi-config-converter'."""
        parser = parse_args(["input", "output"])

        assert parser.input == "input"
        assert parser.output == "output"
        assert not parser.force
        assert isinstance(parser, Namespace)

    @pytest.mark.parametrize(
        ("config_loader", "force"), [(CONFIG_CONTENT, False), (CONFIG_CONTENT, True)], indirect=["config_loader"]
    )
    def test_config_converter(self, config_loader: ConfigLoader, force: bool) -> None:
        """Test content output of converted yaml file."""
        if not force:
            config_loader.hardware_data_file_path.unlink()

        evok_hardware_path: Path = config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(EVOK_MODEL_CONTENT)

        UnipiConfigConverter(config=config_loader.get_config(), force=force).convert(
            source=evok_hardware_yaml, target=Path(config_loader.hardware_data_file_path.parent)
        )

        assert config_loader.hardware_data_file_path.read_text() == CONVERTED_MODEL_CONTENT


class TestUnhappyPathUnipiConfigConverter:
    @pytest.mark.parametrize("config_loader", [CONFIG_CONTENT], indirect=True)
    def test_invalid_input_yaml_file(self, config_loader: ConfigLoader) -> None:
        """Test that input yaml file raises UnexpectedError for invalid yaml file."""
        config_loader.hardware_data_file_path.unlink()

        evok_hardware_path: Path = config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(INVALID_EVOK_MODEL_CONTENT)

        with pytest.raises(UnexpectedError) as error:
            UnipiConfigConverter(config=config_loader.get_config(), force=False).convert(
                source=evok_hardware_yaml, target=Path(config_loader.hardware_data_file_path.parent)
            )

        assert str(error.value) == "INPUT is not a valid YAML file!"

    @pytest.mark.parametrize("config_loader", [CONFIG_CONTENT], indirect=True)
    def test_output_yaml_file_already_exists(self, config_loader: ConfigLoader) -> None:
        """Test that output yaml file raises UnexpectedError if file already exists."""
        evok_hardware_path: Path = config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(EVOK_MODEL_CONTENT)

        with pytest.raises(UnexpectedError) as error:
            UnipiConfigConverter(config=config_loader.get_config(), force=False).convert(
                source=evok_hardware_yaml, target=Path(config_loader.hardware_data_file_path.parent)
            )

        assert str(error.value) == "OUTPUT YAML file already exists!"

    @pytest.mark.parametrize("config_loader", [CONFIG_CONTENT], indirect=True)
    def test_input_is_not_a_file(self, config_loader: ConfigLoader) -> None:
        """Test that input yaml file raises UnexpectedError if input is not a file."""
        evok_hardware_path: Path = config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()

        with pytest.raises(UnexpectedError) as error:
            UnipiConfigConverter(config=config_loader.get_config(), force=False).convert(
                source=evok_hardware_path, target=Path(config_loader.hardware_data_file_path.parent)
            )

        assert str(error.value) == "INPUT is not a file!"

    @pytest.mark.parametrize("config_loader", [CONFIG_CONTENT], indirect=True)
    def test_output_is_a_file(self, config_loader: ConfigLoader) -> None:
        """Test that output yaml directory raises UnexpectedError if output is a file."""
        evok_hardware_path: Path = config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(EVOK_MODEL_CONTENT)

        with pytest.raises(UnexpectedError) as error:
            UnipiConfigConverter(config=config_loader.get_config(), force=False).convert(
                source=evok_hardware_yaml, target=Path(config_loader.hardware_data_file_path)
            )

        assert str(error.value) == "OUTPUT is a file not a directory!"

    @pytest.mark.parametrize("config_loader", [CONFIG_CONTENT], indirect=True)
    def test_output_directory_not_exists(self, config_loader: ConfigLoader) -> None:
        """Test that output yaml directory raises UnexpectedError if not exists."""
        evok_hardware_path: Path = config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(EVOK_MODEL_CONTENT)

        with pytest.raises(UnexpectedError) as error:
            UnipiConfigConverter(config=config_loader.get_config(), force=False).convert(
                source=evok_hardware_yaml, target=config_loader.temp / "NOT_EXISTS"
            )

        assert str(error.value) == "OUTPUT directory not exists!"
