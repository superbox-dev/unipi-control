from typing import Type
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from _pytest.logging import LogCaptureFixture

from conftest import ConfigLoader
from conftest_data import CONFIG_CONTENT
from conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.config import ConfigException
from unipi_control.features import DigitalOutput
from unipi_control.features import Feature
from unipi_control.features import Led
from unipi_control.features import Relay
from unipi_control.neuron import Neuron


class TestHappyPathFeatures:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "config_loader, circuit, feature_type, expected_topic_feature_name, expected_value, expected_repr",
        [
            ((CONFIG_CONTENT, HARDWARE_DATA_CONTENT), "di_2_15", "DI", "input", 1, "Digital Input 2.15"),
            ((CONFIG_CONTENT, HARDWARE_DATA_CONTENT), "do_1_01", "DO", "relay", 0, "Digital Output 1.01"),
            ((CONFIG_CONTENT, HARDWARE_DATA_CONTENT), "ro_2_13", "RO", "relay", 1, "Relay 2.13"),
            ((CONFIG_CONTENT, HARDWARE_DATA_CONTENT), "ro_2_14", "RO", "relay", 0, "Relay 2.14"),
            ((CONFIG_CONTENT, HARDWARE_DATA_CONTENT), "led_1_01", "LED", "led", 0, "LED 1.01"),
        ],
        indirect=["config_loader"],
    )
    async def test_output_features(
        self,
        modbus_client: AsyncMock,
        config_loader: ConfigLoader,
        neuron: Neuron,
        caplog: LogCaptureFixture,
        circuit: str,
        feature_type: str,
        expected_topic_feature_name: str,
        expected_value: int,
        expected_repr: str,
    ):
        mock_response_is_error = MagicMock()
        mock_response_is_error.isError.return_value = False

        modbus_client.write_coil.return_value = mock_response_is_error

        feature: Type[Feature] = neuron.features.by_circuit(circuit, feature_type=[feature_type])
        feature._value = False

        assert expected_value == feature.value
        assert ("ON" if expected_value == 1 else "OFF") == feature.state

        assert f"mocked_unipi/{expected_topic_feature_name}/{circuit}" == feature.topic
        assert expected_repr == str(feature)
        assert expected_repr == str(feature)
        assert (True if expected_value == 1 else False) == feature.changed

        if isinstance(feature, (Relay, DigitalOutput, Led)):
            response = await feature.set_state(0)
            assert False is response.isError()


class TestUnhappyPathFeatures:
    @pytest.mark.parametrize(
        "config_loader, circuit, expected_log",
        [((CONFIG_CONTENT, HARDWARE_DATA_CONTENT), "INVALID", "[CONFIG] 'INVALID' not found in FeatureMap!")],
        indirect=["config_loader"],
    )
    def test_invalid_feature_by_circuit(
        self, config_loader: ConfigLoader, neuron: Neuron, circuit: str, expected_log: str
    ):
        with pytest.raises(ConfigException) as error:
            neuron.features.by_circuit(circuit, feature_type=["DO", "RO"])

        assert expected_log == str(error.value)
