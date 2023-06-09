"""Unit tests for input and output features."""

from typing import NamedTuple
from typing import Optional
from typing import Union
from unittest.mock import MagicMock

import pytest
from pymodbus.pdu import ModbusResponse

from tests.conftest import MockModbusClient
from tests.conftest_data import CONFIG_CONTENT
from tests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.features.extensions import EastronMeter
from unipi_control.features.neuron import DigitalInput
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Led
from unipi_control.features.neuron import Relay
from unipi_control.helpers.exception import ConfigError
from unipi_control.neuron import Neuron


class FeatureOptions(NamedTuple):
    feature_id: str
    feature_type: str


class FeatureExpected(NamedTuple):
    topic_feature_name: Optional[str] = None
    value: Optional[Union[float, int]] = None
    str_output: Optional[str] = None
    coil: Optional[int] = None


class TestHappyPathFeatures:
    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("config_loader", "options", "expected"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="di_2_15", feature_type="DI"),
                FeatureExpected(topic_feature_name="input", value=1, str_output="Digital Input 2.15", coil=None),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="do_1_01", feature_type="DO"),
                FeatureExpected(topic_feature_name="relay", value=0, str_output="Digital Output 1.01", coil=0),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="ro_2_13", feature_type="RO"),
                FeatureExpected(topic_feature_name="relay", value=0, str_output="Relay 2.13", coil=112),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="ro_2_14", feature_type="RO"),
                FeatureExpected(topic_feature_name="relay", value=1, str_output="Relay 2.14", coil=113),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="led_1_01", feature_type="LED"),
                FeatureExpected(topic_feature_name="led", value=0, str_output="LED 1.01", coil=8),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="active_power_1", feature_type="METER"),
                FeatureExpected(topic_feature_name="meter", value=37.7, str_output="Active Power"),
            ),
        ],
        indirect=["config_loader"],
    )
    async def test_output_features(
        self, modbus_client: MockModbusClient, neuron: Neuron, options: FeatureOptions, expected: FeatureExpected
    ) -> None:
        """Test values from the output features."""
        mock_response = MagicMock(spec=ModbusResponse)
        mock_response.isError.return_value = False

        modbus_client.tcp.write_coil.return_value = mock_response

        feature: Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter] = neuron.features.by_feature_id(
            options.feature_id, feature_types=[options.feature_type]
        )

        assert feature.topic == f"mocked_unipi/{expected.topic_feature_name}/{options.feature_id}"
        assert str(feature) == expected.str_output

        feature.saved_value = False

        assert feature.changed == bool(expected.value)
        assert feature.value == expected.value

        if isinstance(feature, (Relay, DigitalOutput, Led)):
            assert feature.val_coil == expected.coil
            assert feature.payload == ("ON" if expected.value == 1 else "OFF")
            assert await feature.set_state(False)
        elif isinstance(feature, EastronMeter):
            assert feature.payload == expected.value

    @pytest.mark.asyncio()
    @pytest.mark.parametrize(
        ("config_loader", "modbus_client", "expected"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                {"eastron_sw_version_failed": True},
                "Unknown",
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                {"eastron_sw_version_failed": False},
                "202.04",
            ),
        ],
        indirect=["config_loader", "modbus_client"],
    )
    async def test_eastron_sw_version(self, neuron: Neuron, expected: str) -> None:
        """Test eastron software version."""
        feature: Union[DigitalInput, DigitalOutput, Led, Relay, EastronMeter] = neuron.features.by_feature_id(
            "active_power_1", feature_types=["METER"]
        )

        assert feature.sw_version == expected


class TestUnhappyPathFeatures:
    @pytest.mark.parametrize(
        ("config_loader", "feature_id", "expected"),
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "INVALID",
                "[CONFIG] 'INVALID' not found in FeatureMap!",
            )
        ],
        indirect=["config_loader"],
    )
    def test_invalid_feature_by_feature_id(self, neuron: Neuron, feature_id: str, expected: str) -> None:
        """Test that invalid feature id raises ConfigError when reading feature by feature id."""
        with pytest.raises(ConfigError) as error:
            neuron.features.by_feature_id(feature_id, feature_types=["DO", "RO"])

        assert str(error.value) == expected
