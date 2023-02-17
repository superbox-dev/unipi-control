from typing import Optional
from typing import Union

from asyncio_mqtt import Client

from unipi_control.config import Config
from unipi_control.config import HardwareData
from unipi_control.features import BaseFeature
from unipi_control.features import NeuronFeature


class HassDiscoveryMixin:
    def __init__(self, neuron, mqtt_client: Client) -> None:
        self.neuron = neuron
        self.mqtt_client: Client = mqtt_client

        self.config: Config = neuron.config
        self.hardware: HardwareData = neuron.hardware

    def _get_via_device(self, feature: Union[BaseFeature]) -> Optional[str]:
        if (device_name := self.config.device_info.name) != self._get_device_name(feature):
            return device_name

        return None

    def _get_device_name(self, feature: Union[BaseFeature]) -> str:
        suggested_area: Optional[str] = feature.suggested_area
        device_name: str = self.config.device_info.name

        if feature.definition.device_name:
            device_name = feature.definition.device_name

        if suggested_area:
            device_name = f"{device_name} - {suggested_area}"

        return device_name

    def _get_device_model(self, feature: Optional[Union[BaseFeature]] = None) -> str:
        device_model: str = f'{self.hardware["neuron"].name} {self.hardware["neuron"].model}'

        if feature and feature.definition.model:
            device_model = f"{feature.definition.model}"

        return device_model

    def _get_device_manufacturer(self, feature: Optional[BaseFeature] = None) -> str:
        device_manufacturer: str = self.config.device_info.manufacturer

        if feature and feature.definition.manufacturer:
            device_manufacturer = f"{feature.definition.manufacturer}"

        return device_manufacturer

    @staticmethod
    def _get_invert_state(feature: NeuronFeature) -> bool:
        if feature.features_config and feature.features_config.invert_state:
            return feature.features_config.invert_state

        return False
