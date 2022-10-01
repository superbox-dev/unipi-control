import builtins
import subprocess
from argparse import Namespace
from typing import List

import pytest
from _pytest.capture import CaptureFixture
from _pytest.logging import LogCaptureFixture
from pytest_mock import MockerFixture

from conftest import ConfigLoader
from conftest_data import CONFIG_CONTENT
from conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.config import Config
from unipi_control.run import UnipiControl
from unipi_control.run import parse_args
from unittests.test_unipi_control_data import UNIPI_CONTROL_INSTALLER_WITHOUT_ENABLE_SYSTEMD_OUTPUT
from unittests.test_unipi_control_data import UNIPI_CONTROL_INSTALLER_WITHOUT_OVERWRITE_CONFIG_OUTPUT
from unittests.test_unipi_control_data import UNIPI_CONTROL_INSTALLER_WITH_ENABLE_SYSTEMD_OUTPUT


class TestHappyPathUnipiControl:
    def test_parse_args(self):
        parser = parse_args(["-i", "-y", "-vv"])

        assert True is parser.install
        assert True is parser.yes
        assert 2 == parser.verbose
        assert isinstance(parser, Namespace)

    @pytest.mark.parametrize(
        "side_effect, expected",
        [
            (["Y", "Y"], UNIPI_CONTROL_INSTALLER_WITH_ENABLE_SYSTEMD_OUTPUT),
            (["Y", "N"], UNIPI_CONTROL_INSTALLER_WITHOUT_ENABLE_SYSTEMD_OUTPUT),
            (["N", "N"], UNIPI_CONTROL_INSTALLER_WITHOUT_OVERWRITE_CONFIG_OUTPUT),
        ],
    )
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    def test_installer(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        caplog: LogCaptureFixture,
        capsys: CaptureFixture,
        side_effect: List[str],
        expected: str,
    ):
        config: Config = config_loader.get_config()

        mock_input = mocker.patch.object(builtins, "input")
        mock_input.side_effect = side_effect

        mock_subprocess = mocker.patch.object(subprocess, "check_output")
        mock_subprocess.return_value = "MOCKED STATUS"

        UnipiControl.install(config=config, assume_yes=False)

        logs: list = [record.getMessage() for record in caplog.records]

        if mock_subprocess.called:
            assert "MOCKED STATUS" in logs

        try:
            assert expected % config_loader.temp == capsys.readouterr().out
        except TypeError:
            assert expected == capsys.readouterr().out
