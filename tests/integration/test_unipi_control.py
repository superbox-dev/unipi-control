"""Integration tests for unipi-config-backup cli command."""
from typing import List

import pytest
from _pytest.logging import LogCaptureFixture  # pylint: disable=import-private-name

from tests.conftest import ConfigLoader
from tests.conftest_data import CONFIG_CONTENT
from tests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.unipi_control import main


# class TestHappyPathUnipiControl:
#     @pytest.mark.parametrize(
#         ("config_loader", "modbus_client", "hardware_info"),
#         [
#             (
#                 (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
#                 {
#                     "name": "MOCKED_NAME",
#                     "model": "MOCKED_MODEL",
#                     "version": "MOCKED_VERSION",
#                     "serial": "MOCKED_SERIAL",
#                 },
#             )
#         ],
#         indirect=["config_loader", "modbus_client"],
#     )
#     def test_unipi_control(
#         self,
#         config_loader: ConfigLoader,
#         hardware_info: Dict[str, str],
#         caplog: LogCaptureFixture,
#         mocker: MockerFixture,
#     ) -> None:
#         """Test for unipi-control cli."""
#         mock_hardware_info: PropertyMock = mocker.patch(
#             "unipi_control.config.HardwareInfo", new_callable=PropertyMock()
#         )
#         mock_hardware_info.return_value = MockHardwareInfo(**hardware_info)
#
#         main(["-c", config_loader.temp.as_posix()])
#
#         logs: List[str] = [record.getMessage() for record in caplog.records]
#         print(logs)


class TestUnhappyPathUnipiControl:
    @pytest.mark.parametrize(
        "config_loader",
        [
            (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
        ],
        indirect=["config_loader"],
    )
    def test_hardware_is_not_supported(self, config_loader: ConfigLoader, caplog: LogCaptureFixture) -> None:
        """Test for hardware is not supported."""
        with pytest.raises(SystemExit) as error:
            main(["-c", config_loader.temp.as_posix()])

        logs: List[str] = [record.getMessage() for record in caplog.records]

        assert "[CONFIG] Hardware is not supported!" in logs
        assert error.value.code == 1
