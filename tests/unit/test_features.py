"""Test input and output features."""

from dataclasses import dataclass
from dataclasses import field
from typing import Optional
from typing import Union
from unittest.mock import MagicMock

import pytest
from pymodbus.pdu import ModbusResponse

from tests.unit.conftest import MockModbusClient
from tests.unit.conftest_data import CONFIG_CONTENT
from tests.unit.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.unit.conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.features.extensions import EastronMeter
from unipi_control.features.neuron import DigitalInput
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Led
from unipi_control.features.neuron import Relay
from unipi_control.helpers.exception import ConfigError
from unipi_control.neuron import Neuron


@dataclass
class FeatureOptions:
    feature_id: str = field(default_factory=str)
    feature_type: str = field(default_factory=str)


@dataclass
class FeatureExpected:
    topic_feature_name: Optional[str] = field(default=None)
    value: Optional[Union[float, int]] = field(default=None)
    str_output: Optional[str] = field(default=None)
    coil: Optional[int] = field(default=None)


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
