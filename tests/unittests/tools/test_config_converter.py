from argparse import Namespace
from pathlib import Path

import pytest

from unipi_control.exception import UnexpectedException
from unipi_control.tools.config_converter import UnipiConfigConverter
from unipi_control.tools.config_converter import parse_args
from unittests.conftest import ConfigLoader
from unittests.conftest_data import CONFIG_CONTENT
from unittests.tools.test_config_converter_data import CONVERTED_MODEL_CONTENT
from unittests.tools.test_config_converter_data import EVOK_MODEL_CONTENT
from unittests.tools.test_config_converter_data import INVALID_EVOK_MODEL_CONTENT


class TestHappyPathUnipiConfigConverter:
    def test_parse_args(self) -> None:
        parser = parse_args(["input", "output"])

        assert parser.input == "input"
        assert parser.output == "output"
        assert not parser.force
        assert isinstance(parser, Namespace)

    @pytest.mark.parametrize(
        "_config_loader, force", [(CONFIG_CONTENT, False), (CONFIG_CONTENT, True)], indirect=["_config_loader"]
    )
    def test_config_converter(self, _config_loader: ConfigLoader, force: bool) -> None:
        if not force:
            _config_loader.hardware_data_file_path.unlink()

        evok_hardware_path: Path = _config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(EVOK_MODEL_CONTENT)

        UnipiConfigConverter(config=_config_loader.get_config(), force=force).convert(
            source=evok_hardware_yaml, target=Path(_config_loader.hardware_data_file_path.parent)
        )

        assert _config_loader.hardware_data_file_path.read_text() == CONVERTED_MODEL_CONTENT


class TestUnhappyPathUnipiConfigConverter:
    @pytest.mark.parametrize("_config_loader", [(CONFIG_CONTENT)], indirect=True)
    def test_invalid_input_yaml_file(self, _config_loader: ConfigLoader) -> None:
        _config_loader.hardware_data_file_path.unlink()

        evok_hardware_path: Path = _config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(INVALID_EVOK_MODEL_CONTENT)

        with pytest.raises(UnexpectedException) as error:
            UnipiConfigConverter(config=_config_loader.get_config(), force=False).convert(
                source=evok_hardware_yaml, target=Path(_config_loader.hardware_data_file_path.parent)
            )

        assert str(error.value) == "INPUT is not a valid YAML file!"

    @pytest.mark.parametrize("_config_loader", [(CONFIG_CONTENT)], indirect=True)
    def test_output_yaml_file_already_exists(self, _config_loader: ConfigLoader) -> None:
        evok_hardware_path: Path = _config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(EVOK_MODEL_CONTENT)

        with pytest.raises(UnexpectedException) as error:
            UnipiConfigConverter(config=_config_loader.get_config(), force=False).convert(
                source=evok_hardware_yaml, target=Path(_config_loader.hardware_data_file_path.parent)
            )

        assert str(error.value) == "OUTPUT YAML file already exists!"

    @pytest.mark.parametrize("_config_loader", [(CONFIG_CONTENT)], indirect=True)
    def test_input_is_not_a_file(self, _config_loader: ConfigLoader) -> None:
        evok_hardware_path: Path = _config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()

        with pytest.raises(UnexpectedException) as error:
            UnipiConfigConverter(config=_config_loader.get_config(), force=False).convert(
                source=evok_hardware_path, target=Path(_config_loader.hardware_data_file_path.parent)
            )

        assert str(error.value) == "INPUT is not a file!"

    @pytest.mark.parametrize("_config_loader", [(CONFIG_CONTENT)], indirect=True)
    def test_output_is_a_file(self, _config_loader: ConfigLoader) -> None:
        evok_hardware_path: Path = _config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(EVOK_MODEL_CONTENT)

        with pytest.raises(UnexpectedException) as error:
            UnipiConfigConverter(config=_config_loader.get_config(), force=False).convert(
                source=evok_hardware_yaml, target=Path(_config_loader.hardware_data_file_path)
            )

        assert str(error.value) == "OUTPUT is a file not a directory!"

    @pytest.mark.parametrize("_config_loader", [(CONFIG_CONTENT)], indirect=True)
    def test_output_directory_not_exists(self, _config_loader: ConfigLoader) -> None:
        evok_hardware_path: Path = _config_loader.hardware_data_file_path.parent / "evok"
        evok_hardware_path.mkdir()
        evok_hardware_yaml: Path = evok_hardware_path / "MOCKED_MODEL.yaml"
        evok_hardware_yaml.write_text(EVOK_MODEL_CONTENT)

        with pytest.raises(UnexpectedException) as error:
            UnipiConfigConverter(config=_config_loader.get_config(), force=False).convert(
                source=evok_hardware_yaml, target=_config_loader.temp / "NOT_EXISTS"
            )

        assert str(error.value) == "OUTPUT directory not exists!"
