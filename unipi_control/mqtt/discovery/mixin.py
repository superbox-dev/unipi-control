"""Helpers for MQTT subscribe and publish."""
from typing import TYPE_CHECKING
from typing import Union

from aiomqtt import Client

from unipi_control.features.extensions import EastronMeter
from unipi_control.features.neuron import NeuronFeature
from unipi_control.neuron import Neuron

if TYPE_CHECKING:
    from unipi_control.config import Config
    from unipi_control.config import HardwareMap


class HassDiscoveryMixin:
    def __init__(self, neuron: Neuron, mqtt_client: Client) -> None:
        self.neuron = neuron
        self.mqtt_client: Client = mqtt_client

        self.config: Config = neuron.config
        self.hardware: HardwareMap = neuron.hardware

    @staticmethod
    def _get_device_model(feature: Union[NeuronFeature, EastronMeter]) -> str:
        return f"{feature.hardware.definition.model}"

    def _get_device_manufacturer(self, feature: Union[NeuronFeature, EastronMeter]) -> str:
        if feature.hardware.definition.manufacturer:
            return f"{feature.hardware.definition.manufacturer}"

        return self.config.device_info.manufacturer

    @staticmethod
    def _get_invert_state(feature: NeuronFeature) -> bool:
        if feature.features_config and feature.features_config.invert_state:
            return feature.features_config.invert_state

        return False
