import builtins
import subprocess
from argparse import Namespace
from typing import List

import pytest
from _pytest.capture import CaptureFixture  # pylint: disable=import-private-name
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name
from pytest_mock import MockerFixture

from unipi_control.config import Config
from unipi_control.unipi_control import UnipiControl
from unipi_control.unipi_control import parse_args
from unittests.conftest import ConfigLoader
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT
from .test_unipi_control_data import UNIPI_CONTROL_INSTALLER_WITHOUT_ENABLE_SYSTEMD_OUTPUT
from .test_unipi_control_data import UNIPI_CONTROL_INSTALLER_WITHOUT_OVERWRITE_CONFIG_OUTPUT
from .test_unipi_control_data import UNIPI_CONTROL_INSTALLER_WITH_ENABLE_SYSTEMD_OUTPUT


class TestHappyPathUnipiControl:
    def test_parse_args(self) -> None:
        parser = parse_args(["-i", "-y", "-vv"])

        assert parser.install is True
        assert parser.yes is True
        assert parser.verbose == 2
        assert isinstance(parser, Namespace)

    @pytest.mark.parametrize(
        "side_effect, expected",
        [
            (["Y", "Y"], UNIPI_CONTROL_INSTALLER_WITH_ENABLE_SYSTEMD_OUTPUT),
            (["Y", "N"], UNIPI_CONTROL_INSTALLER_WITHOUT_ENABLE_SYSTEMD_OUTPUT),
            (["N", "N"], UNIPI_CONTROL_INSTALLER_WITHOUT_OVERWRITE_CONFIG_OUTPUT),
        ],
    )
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    def test_installer(
        self,
        _config_loader: ConfigLoader,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
        capsys: CaptureFixture,
        side_effect: List[str],
        expected: str,
    ) -> None:
        config: Config = _config_loader.get_config()

        mock_input = mocker.patch.object(builtins, "input")
        mock_input.side_effect = side_effect

        mock_subprocess = mocker.patch.object(subprocess, "check_output")
        mock_subprocess.return_value = "MOCKED STATUS"

        UnipiControl.install(config=config, assume_yes=False)

        logs: list = [record.getMessage() for record in caplog.records]

        if mock_subprocess.called:
            assert "MOCKED STATUS" in logs

        assert capsys.readouterr().out == expected.replace("{config_loader_temp}", _config_loader.temp.as_posix())
