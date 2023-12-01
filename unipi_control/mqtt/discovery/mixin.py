"""Mixin for Home Assistant MQTT discovery."""
from typing import TYPE_CHECKING
from typing import Union

from aiomqtt import Client

from unipi_control.features.eastron import Eastron
from unipi_control.features.unipi import UnipiFeature
from unipi_control.hardware.unipi import Unipi

if TYPE_CHECKING:
    from unipi_control.config import Config
    from unipi_control.hardware.map import HardwareMap


class HassDiscoveryMixin:
    def __init__(self, unipi: Unipi, client: Client) -> None:
        self.config: Config = unipi.config
        self.unipi = unipi
        self.client: Client = client

        self.hardware: HardwareMap = unipi.hardware

    @staticmethod
    def _get_device_model(feature: Union[UnipiFeature, Eastron]) -> str:
        return f"{feature.hardware.definition.model}"

    def _get_device_manufacturer(self, feature: Union[UnipiFeature, Eastron]) -> str:
        if feature.hardware.definition.manufacturer:
            return f"{feature.hardware.definition.manufacturer}"

        return self.config.device_info.manufacturer

    @staticmethod
    def _get_invert_state(feature: UnipiFeature) -> bool:
        if feature.features_config and feature.features_config.invert_state:
            return feature.features_config.invert_state

        return False
