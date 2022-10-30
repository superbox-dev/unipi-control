import pytest

from unipi_control.config import ConfigException
from unittests.conftest import ConfigLoader
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT
from .test_config_data import CONFIG_DUPLICATE_COVERS_CIRCUITS
from .test_config_data import CONFIG_DUPLICATE_COVER_ID
from .test_config_data import CONFIG_DUPLICATE_FEATURE_ID
from .test_config_data import CONFIG_DUPLICATE_MODBUS_UNIT
from .test_config_data import CONFIG_INVALID
from .test_config_data import CONFIG_INVALID_COVER_ID
from .test_config_data import CONFIG_INVALID_COVER_TYPE
from .test_config_data import CONFIG_INVALID_DEVICE_NAME
from .test_config_data import CONFIG_INVALID_FEATURE_ID
from .test_config_data import CONFIG_INVALID_FEATURE_TYPE
from .test_config_data import CONFIG_INVALID_HOMEASSISTANT_DISCOVERY_PREFIX
from .test_config_data import CONFIG_INVALID_LOG_LEVEL
from .test_config_data import CONFIG_INVALID_MODBUS_BAUD_RATE
from .test_config_data import CONFIG_INVALID_MODBUS_PARITY
from .test_config_data import CONFIG_MISSING_COVER_KEY


class TestUnhappyPathConfig:
    @pytest.mark.parametrize(
        "_config_loader, expected",
        [
            (
                (CONFIG_INVALID_DEVICE_NAME, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[DEVICEINFO] Invalid value 'INVALID DEVICE NAME' in 'name'. The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (
                    CONFIG_INVALID_HOMEASSISTANT_DISCOVERY_PREFIX,
                    HARDWARE_DATA_CONTENT,
                    EXTENSION_HARDWARE_DATA_CONTENT,
                ),
                "[HOMEASSISTANT] Invalid value 'invalid discovery name' in 'discovery_prefix'. The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_FEATURE_TYPE, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "Expected features to be <class 'dict'>, got 'INVALID'",
            ),
            (
                (CONFIG_INVALID_COVER_ID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Invalid value 'invalid id' in 'id'. The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_COVER_TYPE, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Invalid value 'INVALID' in 'cover_type'. The following values are allowed: blind roller_shutter garage_door.",
            ),
            (
                (CONFIG_MISSING_COVER_KEY, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Required key 'id' is missing! CoverConfig(id='', friendly_name='MOCKED_FRIENDLY_NAME - BLIND', suggested_area='', cover_type='blind', cover_run_time=35.5, tilt_change_time=1.5, circuit_up='ro_3_01', circuit_down='ro_3_02')",
            ),
            (
                (CONFIG_DUPLICATE_COVERS_CIRCUITS, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Duplicate circuits found in 'covers'. Driving both signals up and down at the same time can damage the motor!",
            ),
            (
                (CONFIG_INVALID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                """Can't read YAML file!\n  in "<unicode string>", line 2, column 21:\n      name: MOCKED_UNIPI:\n                        ^""",
            ),
            (
                (CONFIG_INVALID_LOG_LEVEL, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[LOGGING] Invalid log level 'invalid'. The following log levels are allowed: error warning info debug.",
            ),
            (
                (CONFIG_DUPLICATE_COVER_ID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Duplicate ID 'mocked_duplicate_id' found in 'covers'!",
            ),
            (
                (CONFIG_DUPLICATE_FEATURE_ID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[FEATURE] Duplicate ID 'mocked_duplicate_id' found in 'features'!",
            ),
            (
                (CONFIG_INVALID_FEATURE_ID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[FEATURE] Invalid value 'invalid id' in 'id'. The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_MODBUS_BAUD_RATE, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[MODBUS] Invalid baud rate '2401. The following baud rates allowed: 2400 4800 9600 19200 38400 57600 115200.",
            ),
            (
                (CONFIG_INVALID_MODBUS_PARITY, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[MODBUS] Invalid value 'S' in 'parity'. The following parity options are allowed: E O N.",
            ),
            (
                (CONFIG_DUPLICATE_MODBUS_UNIT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[MODBUS] Duplicate modbus unit '1' found in 'units'!",
            ),
        ],
        indirect=["_config_loader"],
    )
    def test_validation(self, _config_loader: ConfigLoader, expected: str):
        with pytest.raises(ConfigException) as error:
            _config_loader.get_config()

        assert str(error.value) == expected
