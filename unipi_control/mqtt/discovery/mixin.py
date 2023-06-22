"""Helpers for MQTT subscribe and publish."""

from typing import Optional, TYPE_CHECKING
from typing import Union

from asyncio_mqtt import Client

from unipi_control.features.extensions import EastronMeter
from unipi_control.features.neuron import NeuronFeature
from unipi_control.neuron import Neuron

if TYPE_CHECKING:
    from unipi_control.config import Config
    from unipi_control.config import HardwareMap
    from unipi_control.helpers.typing import HardwareDefinition


class HassDiscoveryMixin:
    def __init__(self, neuron: Neuron, mqtt_client: Client) -> None:
        self.neuron = neuron
        self.mqtt_client: Client = mqtt_client

        self.config: Config = neuron.config
        self.hardware: HardwareMap = neuron.hardware

    def _get_via_device(self, feature: Union[NeuronFeature, EastronMeter]) -> Optional[str]:
        if (device_name := self.config.device_info.name) != self._get_device_name(feature):
            return device_name

        return None

    def _get_device_name(self, feature: Union[NeuronFeature, EastronMeter]) -> str:
        suggested_area: Optional[str] = feature.suggested_area
        device_name: str = self.config.device_info.name
        definition: HardwareDefinition = feature.hardware.definition

        if definition.device_name:
            device_name = definition.device_name

        if suggested_area:
            device_name = f"{device_name} - {suggested_area}"

        return device_name

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
