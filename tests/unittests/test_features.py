# pylint: disable=protected-access
from dataclasses import dataclass
from dataclasses import field
from typing import Optional
from typing import Union
from unittest.mock import MagicMock

import pytest
from pymodbus.pdu import ModbusResponse

from unipi_control.config import ConfigException
from unipi_control.features import DigitalInput
from unipi_control.features import DigitalOutput
from unipi_control.features import Led
from unipi_control.features import MeterFeature
from unipi_control.features import Relay
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest import MockModbusClient
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT


@dataclass
class FeatureOptions:
    feature_id: str = field(default_factory=str)
    feature_type: str = field(default_factory=str)


@dataclass
class FeatureExpected:
    topic_feature_name: Optional[str] = field(default=None)
    value: Optional[Union[float, int]] = field(default=None)
    repr: Optional[str] = field(default=None)
    coil: Optional[int] = field(default=None)


class TestHappyPathFeatures:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader, options, expected",
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="di_2_15", feature_type="DI"),
                FeatureExpected(topic_feature_name="input", value=1, repr="Digital Input 2.15", coil=None),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="do_1_01", feature_type="DO"),
                FeatureExpected(topic_feature_name="relay", value=0, repr="Digital Output 1.01", coil=0),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="ro_2_13", feature_type="RO"),
                FeatureExpected(topic_feature_name="relay", value=0, repr="Relay 2.13", coil=112),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="ro_2_14", feature_type="RO"),
                FeatureExpected(topic_feature_name="relay", value=1, repr="Relay 2.14", coil=113),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="led_1_01", feature_type="LED"),
                FeatureExpected(topic_feature_name="led", value=0, repr="LED 1.01", coil=8),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(feature_id="active_power_1", feature_type="METER"),
                FeatureExpected(topic_feature_name="meter", value=37.7, repr="Active Power"),
            ),
        ],
        indirect=["_config_loader"],
    )
    async def test_output_features(
        self,
        _modbus_client: MockModbusClient,
        _config_loader: ConfigLoader,
        _neuron: Neuron,
        options: FeatureOptions,
        expected: FeatureExpected,
    ) -> None:
        mock_response = MagicMock(spec=ModbusResponse)
        mock_response.isError.return_value = False

        _modbus_client.tcp.write_coil.return_value = mock_response

        feature: Union[DigitalInput, DigitalOutput, Led, Relay, MeterFeature] = _neuron.features.by_feature_id(
            options.feature_id, feature_types=[options.feature_type]
        )

        assert feature.topic == f"mocked_unipi/{expected.topic_feature_name}/{options.feature_id}"
        assert str(feature) == expected.repr

        feature._value = False

        assert feature.changed == bool(expected.value)
        assert feature.value == expected.value

        if isinstance(feature, (Relay, DigitalOutput, Led)):
            assert feature.val_coil == expected.coil
            assert feature.payload == ("ON" if expected.value == 1 else "OFF")
            assert await feature.set_state(False)
        elif isinstance(feature, MeterFeature):
            assert feature.payload == expected.value


class TestUnhappyPathFeatures:
    @pytest.mark.parametrize(
        "_config_loader, feature_id, expected",
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "INVALID",
                "[CONFIG] 'INVALID' not found in FeatureMap!",
            )
        ],
        indirect=["_config_loader"],
    )
    def test_invalid_feature_by_feature_id(
        self, _config_loader: ConfigLoader, _neuron: Neuron, feature_id: str, expected: str
    ) -> None:
        with pytest.raises(ConfigException) as error:
            _neuron.features.by_feature_id(feature_id, feature_types=["DO", "RO"])

        assert str(error.value) == expected
