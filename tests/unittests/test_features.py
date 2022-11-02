# pylint: disable=protected-access
from dataclasses import dataclass
from dataclasses import field
from typing import Optional
from unittest.mock import MagicMock

import pytest

from unipi_control.config import ConfigException
from unipi_control.features import DigitalOutput
from unipi_control.features import FeatureItem
from unipi_control.features import Led
from unipi_control.features import Relay
from unipi_control.modbus import ModbusClient
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT


@dataclass
class FeatureOptions:
    object_id: str = field(default_factory=str)
    feature_type: str = field(default_factory=str)


@dataclass
class FeatureExpected:
    topic_feature_name: Optional[str] = field(default=None)
    value: Optional[int] = field(default=None)
    repr: Optional[str] = field(default=None)
    coil: Optional[int] = field(default=None)


class TestHappyPathFeatures:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader, options, expected",
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(object_id="di_2_15", feature_type="DI"),
                FeatureExpected(topic_feature_name="input", value=1, repr="Digital Input 2.15", coil=None),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(object_id="do_1_01", feature_type="DO"),
                FeatureExpected(topic_feature_name="relay", value=0, repr="Digital Output 1.01", coil=0),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(object_id="ro_2_13", feature_type="RO"),
                FeatureExpected(topic_feature_name="relay", value=0, repr="Relay 2.13", coil=112),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(object_id="ro_2_14", feature_type="RO"),
                FeatureExpected(topic_feature_name="relay", value=1, repr="Relay 2.14", coil=113),
            ),
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                FeatureOptions(object_id="led_1_01", feature_type="LED"),
                FeatureExpected(topic_feature_name="led", value=0, repr="LED 1.01", coil=8),
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

        feature: FeatureItem = _neuron.features.by_object_id(options.object_id, feature_type=[options.feature_type])

        assert feature.topic == f"mocked_unipi/{expected.topic_feature_name}/{options.object_id}"
        assert str(feature) == expected.repr

        feature._value = False
        assert feature.changed == bool(expected.value)
        assert feature.value == expected.value

        if isinstance(feature, (Relay, DigitalOutput, Led)):
            assert feature.val_coil == expected.coil
            assert feature.payload == ("ON" if expected.value == 1 else "OFF")

            response = await feature.set_state(False)
            assert not response.isError()


class TestUnhappyPathFeatures:
    @pytest.mark.parametrize(
        "_config_loader, object_id, expected",
        [
            (
                (CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT),
                "INVALID",
                "[CONFIG] 'INVALID' not found in FeatureMap!",
            )
        ],
        indirect=["_config_loader"],
    )
    def test_invalid_feature_by_object_id(
        self, _config_loader: ConfigLoader, _neuron: Neuron, object_id: str, expected: str
    ):
        with pytest.raises(ConfigException) as error:
            _neuron.features.by_object_id(object_id, feature_type=["DO", "RO"])

        assert str(error.value) == expected
