# pylint: disable=protected-access
from dataclasses import dataclass
from dataclasses import field
from typing import Optional
from typing import Type
from unittest.mock import MagicMock

import pytest

from unipi_control.config import ConfigException
from unipi_control.features import DigitalOutput
from unipi_control.features import Feature
from unipi_control.features import Led
from unipi_control.features import Relay
from unipi_control.modbus.cache import ModbusClient
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT
from unittests.conftest_data import THIRD_PARTY_HARDWARE_DATA_CONTENT


@dataclass
class FeatureOptions:
    circuit: str = field(default_factory=str)
    feature_type: str = field(default_factory=str)


@dataclass
class FeatureExpected:
    topic_feature_name: Optional[str] = field(default=None)
    value: Optional[int] = field(default=None)
    repr: Optional[str] = field(default=None)


class TestHappyPathFeatures:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader, options, expected",
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, THIRD_PARTY_HARDWARE_DATA_CONTENT),
                FeatureOptions(circuit="di_2_15", feature_type="DI"),
                FeatureExpected(topic_feature_name="input", value=1, repr="Digital Input 2.15"),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, THIRD_PARTY_HARDWARE_DATA_CONTENT),
                FeatureOptions(circuit="do_1_01", feature_type="DO"),
                FeatureExpected(topic_feature_name="relay", value=0, repr="Digital Output 1.01"),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, THIRD_PARTY_HARDWARE_DATA_CONTENT),
                FeatureOptions(circuit="ro_2_13", feature_type="RO"),
                FeatureExpected(topic_feature_name="relay", value=0, repr="Relay 2.13"),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, THIRD_PARTY_HARDWARE_DATA_CONTENT),
                FeatureOptions(circuit="ro_2_14", feature_type="RO"),
                FeatureExpected(topic_feature_name="relay", value=1, repr="Relay 2.14"),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, THIRD_PARTY_HARDWARE_DATA_CONTENT),
                FeatureOptions(circuit="led_1_01", feature_type="LED"),
                FeatureExpected(topic_feature_name="led", value=0, repr="LED 1.01"),
            ),
        ],
        indirect=["_config_loader"],
    )
    async def test_output_features(
        self,
        _modbus_client: ModbusClient,
        _config_loader: ConfigLoader,
        _neuron: Neuron,
        options: FeatureOptions,
        expected: FeatureExpected,
    ):
        mock_response_is_error = MagicMock()
        mock_response_is_error.isError.return_value = False

        _modbus_client.tcp.write_coil.return_value = mock_response_is_error

        feature: Type[Feature] = _neuron.features.by_circuit(options.circuit, feature_type=[options.feature_type])
        feature._value = False

        assert feature.value == expected.value
        assert feature.state == ("ON" if expected.value == 1 else "OFF")

        assert feature.topic == f"mocked_unipi/{expected.topic_feature_name}/{options.circuit}"
        assert str(feature) == expected.repr
        assert feature.changed == bool(expected.value)

        if isinstance(feature, (Relay, DigitalOutput, Led)):
            response = await feature.set_state(0)
            assert not response.isError()


class TestUnhappyPathFeatures:
    @pytest.mark.parametrize(
        "_config_loader, circuit, expected",
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, THIRD_PARTY_HARDWARE_DATA_CONTENT),
                "INVALID",
                "[CONFIG] 'INVALID' not found in FeatureMap!",
            )
        ],
        indirect=["_config_loader"],
    )
    def test_invalid_feature_by_circuit(
        self, _config_loader: ConfigLoader, _neuron: Neuron, circuit: str, expected: str
    ):
        with pytest.raises(ConfigException) as error:
            _neuron.features.by_circuit(circuit, feature_type=["DO", "RO"])

        assert str(error.value) == expected
