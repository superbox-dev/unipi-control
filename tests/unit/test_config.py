"""Test configuration."""
import logging
import re
import uuid
from typing import NamedTuple

import pytest
from _pytest.capture import CaptureFixture  # pylint: disable=import-private-name

from tests.unit.conftest import ConfigLoader
from tests.unit.conftest_data import CONFIG_CONTENT
from tests.unit.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.unit.conftest_data import HARDWARE_DATA_CONTENT
from tests.unit.test_config_data import CONFIG_DUPLICATE_COVERS_CIRCUITS
from tests.unit.test_config_data import CONFIG_DUPLICATE_COVER_ID
from tests.unit.test_config_data import CONFIG_DUPLICATE_MODBUS_UNIT
from tests.unit.test_config_data import CONFIG_DUPLICATE_OBJECT_ID
from tests.unit.test_config_data import CONFIG_INVALID
from tests.unit.test_config_data import CONFIG_INVALID_COVER_ID
from tests.unit.test_config_data import CONFIG_INVALID_COVER_TYPE
from tests.unit.test_config_data import CONFIG_INVALID_DEVICE_CLASS
from tests.unit.test_config_data import CONFIG_INVALID_DEVICE_NAME
from tests.unit.test_config_data import CONFIG_INVALID_FEATURE_ID
from tests.unit.test_config_data import CONFIG_INVALID_FEATURE_TYPE
from tests.unit.test_config_data import CONFIG_INVALID_HOMEASSISTANT_DISCOVERY_PREFIX
from tests.unit.test_config_data import CONFIG_INVALID_LOG_LEVEL
from tests.unit.test_config_data import CONFIG_INVALID_MODBUS_BAUD_RATE
from tests.unit.test_config_data import CONFIG_INVALID_MODBUS_PARITY
from tests.unit.test_config_data import CONFIG_INVALID_MQTT_PORT_TYPE
from tests.unit.test_config_data import CONFIG_LOGGING_LEVEL
from tests.unit.test_config_data import CONFIG_MISSING_COVER_KEY
from tests.unit.test_config_data import CONFIG_MISSING_DEVICE_NAME
from tests.unit.test_config_data import HARDWARE_DATA_INVALID_KEY
from tests.unit.test_config_data import HARDWARE_DATA_IS_INVALID_YAML
from tests.unit.test_config_data import HARDWARE_DATA_IS_LIST
from unipi_control.config import Config
from unipi_control.helpers.exception import ConfigError
from unipi_control.helpers.typing import ModbusClient
from unipi_control.neuron import Neuron


class LoggingLevelParams(NamedTuple):
    log: str
    verbose: int


class LoggingOutputParams(NamedTuple):
    level: int
    log: str
    message: str


class TestHappyPathConfig:
    @pytest.mark.parametrize(
        ("config_loader", "params", "expected"),
        [
            (
                CONFIG_LOGGING_LEVEL,
                LoggingLevelParams(log="stdout", verbose=0),
                logging.ERROR,
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingLevelParams(log="systemd", verbose=0),
                logging.ERROR,
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingLevelParams(log="systemd", verbose=1),
                logging.WARNING,
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingLevelParams(log="systemd", verbose=2),
                logging.INFO,
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingLevelParams(log="systemd", verbose=3),
                logging.DEBUG,
            ),
        ],
        indirect=["config_loader"],
    )
    def test_logging_level(self, config_loader: ConfigLoader, params: LoggingLevelParams, expected: int) -> None:
        """Test verbose arguments change log level."""
        uniqid = str(uuid.uuid4())
        logger: logging.Logger = logging.getLogger(uniqid)

        config: Config = config_loader.get_config()
        config.logging.init(logger=logger, log=params.log, verbose=params.verbose)

        assert logger.level == expected

    @pytest.mark.parametrize(
        ("config_loader", "params", "expected"),
        [
            (
                CONFIG_LOGGING_LEVEL,
                LoggingOutputParams(level=logging.CRITICAL, log="stdout", message="MOCKED MESSAGE"),
                r"^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2},\d{3} \| CRITICAL \| MOCKED MESSAGE\n$",
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingOutputParams(level=logging.CRITICAL, log="systemd", message="MOCKED MESSAGE"),
                r"<2>MOCKED MESSAGE\n",
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingOutputParams(level=logging.ERROR, log="systemd", message="MOCKED MESSAGE"),
                r"<3>MOCKED MESSAGE\n",
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingOutputParams(level=logging.WARNING, log="systemd", message="MOCKED MESSAGE"),
                r"<4>MOCKED MESSAGE\n",
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingOutputParams(level=logging.INFO, log="systemd", message="MOCKED MESSAGE"),
                r"<6>MOCKED MESSAGE\n",
            ),
            (
                CONFIG_LOGGING_LEVEL,
                LoggingOutputParams(level=logging.DEBUG, log="systemd", message="MOCKED MESSAGE"),
                r"<7>MOCKED MESSAGE\n",
            ),
        ],
        indirect=["config_loader"],
    )
    def test_logging_output(
        self, config_loader: ConfigLoader, params: LoggingOutputParams, expected: str, capsys: CaptureFixture
    ) -> None:
        """Test log handler output."""
        uniqid = str(uuid.uuid4())
        logger: logging.Logger = logging.getLogger(uniqid)

        config: Config = config_loader.get_config()
        config.logging.init(logger=logger, log=params.log, verbose=3)

        logger.log(level=params.level, msg=params.message)

        assert re.compile(expected).search(capsys.readouterr().err)


class TestUnhappyPathConfig:
    @pytest.mark.parametrize(
        ("config_loader", "expected"),
        [
            (
                (CONFIG_INVALID_DEVICE_NAME, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[DEVICEINFO] Invalid value 'INVALID DEVICE NAME$' in 'name'. "
                "The following characters are prohibited: a-z 0-9 -_ space",
            ),
            (
                (
                    CONFIG_INVALID_HOMEASSISTANT_DISCOVERY_PREFIX,
                    HARDWARE_DATA_CONTENT,
                    EXTENSION_HARDWARE_DATA_CONTENT,
                ),
                "[HOMEASSISTANT] Invalid value 'invalid discovery name' in 'discovery_prefix'. "
                "The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_FEATURE_TYPE, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "Expected features to be <class 'dict'>, got 'INVALID'",
            ),
            (
                (CONFIG_INVALID_COVER_TYPE, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "Expected covers to be <class 'list'>, got 'INVALID'",
            ),
            (
                (CONFIG_INVALID_MQTT_PORT_TYPE, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "Expected port to be <class 'int'>, got 'INVALID'",
            ),
            (
                (CONFIG_INVALID_COVER_ID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Invalid value 'invalid id' in 'object_id'. "
                "The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_DEVICE_CLASS, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Invalid value 'INVALID' in 'device_class'. "
                "The following values are allowed: blind roller_shutter garage_door.",
            ),
            (
                (CONFIG_MISSING_COVER_KEY, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Required key 'object_id' is missing! "
                "CoverConfig(object_id='', friendly_name='MOCKED_FRIENDLY_NAME - BLIND', suggested_area='', "
                "device_class='blind', cover_run_time=35.5, tilt_change_time=1.5, cover_up='ro_3_01', "
                "cover_down='ro_3_02')",
            ),
            (
                (CONFIG_DUPLICATE_COVERS_CIRCUITS, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Duplicate circuits found in 'covers'. "
                "Driving both signals up and down at the same time can damage the motor!",
            ),
            (
                (CONFIG_INVALID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                'Can\'t read YAML file!\n  in "<unicode string>", line 2, column 21:\n'
                "      name: MOCKED UNIPI:\n                        ^",
            ),
            (
                (CONFIG_INVALID_LOG_LEVEL, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[LOGGING] Invalid log level 'invalid'. "
                "The following log levels are allowed: error warning info debug.",
            ),
            (
                (CONFIG_DUPLICATE_COVER_ID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[COVER] Duplicate ID 'mocked_duplicate_id' found in 'covers'!",
            ),
            (
                (CONFIG_DUPLICATE_OBJECT_ID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[FEATURE] Duplicate ID 'mocked_duplicate_id' found in 'features'!",
            ),
            (
                (CONFIG_INVALID_FEATURE_ID, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[FEATURE] Invalid value 'invalid id' in 'object_id'. "
                "The following characters are prohibited: a-z 0-9 -_",
            ),
            (
                (CONFIG_INVALID_MODBUS_BAUD_RATE, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[MODBUS] Invalid baud rate '2401'. "
                "The following baud rates are allowed: 2400 4800 9600 19200 38400 57600 115200.",
            ),
            (
                (CONFIG_INVALID_MODBUS_PARITY, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[MODBUS] Invalid value 'S' in 'parity'. The following parity options are allowed: E O N.",
            ),
            (
                (CONFIG_DUPLICATE_MODBUS_UNIT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[MODBUS] Duplicate modbus unit '1' found in 'units'!",
            ),
            (
                (CONFIG_MISSING_DEVICE_NAME, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "[MODBUS] Device name for unit '1' is missing!",
            ),
        ],
        indirect=["config_loader"],
    )
    def test_validation(self, config_loader: ConfigLoader, expected: str) -> None:
        """Test yaml config raises ConfigError when validation failed."""
        with pytest.raises(ConfigError) as error:
            config_loader.get_config()

        assert str(error.value) == expected

    @pytest.mark.parametrize(
        ("config_loader", "expected"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_INVALID_KEY, EXTENSION_HARDWARE_DATA_CONTENT),
                "\nKeyError: 'modbus_register_blocks'",
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_IS_LIST, EXTENSION_HARDWARE_DATA_CONTENT),
                "",
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_IS_INVALID_YAML, EXTENSION_HARDWARE_DATA_CONTENT),
                '\nCan\'t read YAML file!\n  in "<unicode string>", line 1, column 25:\n'
                "    modbus_features: INVALID:\n                            ^",
            ),
        ],
        indirect=["config_loader"],
    )
    def test_invalid_neuron_hardware_definition(
        self, config_loader: ConfigLoader, modbus_client: ModbusClient, expected: str
    ) -> None:
        """Test invalid neuron hardware definition."""
        config: Config = config_loader.get_config()

        with pytest.raises(ConfigError) as error:
            Neuron(config=config, modbus_client=modbus_client)

        assert str(error.value) == f"[CONFIG] Definition is invalid: {config_loader.hardware_data_file_path}{expected}"
