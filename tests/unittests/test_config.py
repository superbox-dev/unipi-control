import pytest
from _pytest.logging import LogCaptureFixture

from conftest import ConfigLoader
from conftest_data import HARDWARE_DATA_CONTENT
from unittests.test_config_data import CONFIG_DUPLICATE_COVERS_CIRCUITS
from unittests.test_config_data import CONFIG_INVALID_COVER_PROPERTY
from unittests.test_config_data import CONFIG_INVALID_COVER_TOPIC_NAME
from unittests.test_config_data import CONFIG_INVALID_COVER_TYPE
from unittests.test_config_data import CONFIG_INVALID_DEVICE_NAME
from unittests.test_config_data import CONFIG_INVALID_FEATURE_PROPERTY
from unittests.test_config_data import CONFIG_INVALID_FEATURE_TYPE
from unittests.test_config_data import CONFIG_INVALID_HOMEASSISTANT_DISCOVERY_PREFIX
from unittests.test_config_data import CONFIG_MISSING_COVER_KEY


# class TestHappyPathConfig:
#     @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
#     def test_hardware_data(self, mocker: MockerFixture, config_loader: ConfigLoader, caplog: LogCaptureFixture):
#         config: Config = config_loader.get_config()
#
#         mock_config_open.read().return_value = "".join(ee_bytes)
#
#         mock_struct_unpack: MagicMock = mocker.patch("unipi_control.config.struct.unpack")
#         mock_struct_unpack.return_value = ["MOCKED_SERIAL"]
#
#         hardware: HardwareData = HardwareData(config=config)
#         print(hardware)


class TestUnhappyPathConfig:
    @pytest.mark.parametrize(
        "config_loader, expected_log",
        [
            (
                (CONFIG_INVALID_DEVICE_NAME, HARDWARE_DATA_CONTENT),
                "[CONFIG] Invalid value 'invalid device name' in 'device_name'. The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_HOMEASSISTANT_DISCOVERY_PREFIX, HARDWARE_DATA_CONTENT),
                "[CONFIG] [HOMEASSISTANT] Invalid value 'invalid discovery name' in 'discovery_prefix'. The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_FEATURE_TYPE, HARDWARE_DATA_CONTENT),
                "[CONFIG] Expected features to be <class 'dict'>, got 'INVALID'",
            ),
            (
                (CONFIG_INVALID_FEATURE_PROPERTY, HARDWARE_DATA_CONTENT),
                "[CONFIG] Invalid feature property: {'friendly_name': 'MOCKED_FRIENDLY_NAME - DI_3_01', 'suggested_area': 'MOCKED AREA 1', 'invalid_property': 'INVALID'}",
            ),
            (
                (CONFIG_INVALID_COVER_PROPERTY, HARDWARE_DATA_CONTENT),
                "[CONFIG] Invalid cover property: {'friendly_name': 'MOCKED_FRIENDLY_NAME - BLIND', 'cover_type': 'blind', 'topic_name': 'MOCKED_BLIND_TOPIC_NAME', 'cover_run_time': 35.5, 'tilt_change_time': 1.5, 'circuit_up': 'ro_3_01', 'circuit_down': 'ro_3_02', 'invalid_property': 'INVALID'}",
            ),
            (
                (CONFIG_INVALID_COVER_TOPIC_NAME, HARDWARE_DATA_CONTENT),
                "[CONFIG] [COVER] Invalid value 'invalid topic name' in 'topic_name'. The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_COVER_TYPE, HARDWARE_DATA_CONTENT),
                "[CONFIG] [COVER] Invalid value 'INVALID' in 'cover_type'. The following values are allowed: blind roller_shutter garage_door.",
            ),
            (
                (CONFIG_MISSING_COVER_KEY, HARDWARE_DATA_CONTENT),
                "[CONFIG] [COVER] Required key 'topic_name' is missing! CoverConfig(id='', friendly_name='MOCKED_FRIENDLY_NAME - BLIND', suggested_area='', cover_type='blind', topic_name='', cover_run_time=35.5, tilt_change_time=1.5, circuit_up='ro_3_01', circuit_down='ro_3_02')",
            ),
            (
                (CONFIG_DUPLICATE_COVERS_CIRCUITS, HARDWARE_DATA_CONTENT),
                "[CONFIG] [COVER] Duplicate circuits found in 'covers'. Driving both signals up and down at the same time can damage the motor!",
            ),
        ],
        indirect=["config_loader"],
    )
    def test_validation(self, config_loader: ConfigLoader, caplog: LogCaptureFixture, expected_log: str):
        with pytest.raises(SystemExit) as error:
            config_loader.get_config()
            assert 1 == error.value

        logs: list = [record.getMessage() for record in caplog.records]

        assert expected_log in logs

    # @pytest.mark.parametrize(
    #     "config_loader, hardware_info, expected_log",
    #     [
    #         (
    #             (CONFIG_CONTENT, HARDWARE_DATA_CONTENT),
    #             {"model": "UNKNOWN_MODEL"},
    #             "[CONFIG] No valid YAML definition for active Neuron device! Device name is UNKNOWN_MODEL",
    #         ),
    #         (
    #             (CONFIG_CONTENT, HARDWARE_DATA_CONTENT),
    #             {"model": None},
    #             "[CONFIG] Hardware is not supported!",
    #         ),
    #     ],
    #     indirect=["config_loader"],
    # )
    # def test_hardware_data_exceptions(
    #     self,
    #     mocker: MockerFixture,
    #     config_loader: ConfigLoader,
    #     caplog: LogCaptureFixture,
    #     hardware_info: dict,
    #     expected_log: str,
    # ):
    #     mock_hardware_info: PropertyMock = mocker.patch(
    #         "unipi_control.config.HardwareInfo", new_callable=PropertyMock()
    #     )
    #     mock_hardware_info.return_value = MockHardwareInfo(**hardware_info)
    #     config: Config = config_loader.get_config()
    #
    #     with pytest.raises(SystemExit) as error:
    #         HardwareData(config=config)
    #         assert 1 == error.value
    #
    #     logs: list = [record.getMessage() for record in caplog.records]
    #
    #     assert expected_log in logs
