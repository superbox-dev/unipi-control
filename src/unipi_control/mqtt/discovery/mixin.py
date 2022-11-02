from typing import Optional
from typing import Union

from asyncio_mqtt import Client

from unipi_control.config import Config
from unipi_control.config import HardwareData
from unipi_control.features import FeatureItem
from unipi_control.integrations.covers import Cover


class HassDiscoveryMixin:
    def __init__(self, neuron, mqtt_client: Client):
        self.neuron = neuron
        self.mqtt_client: Client = mqtt_client

        self.config: Config = neuron.config
        self.hardware: HardwareData = neuron.hardware

    def _get_topic(self, name: str, item: Union[FeatureItem, Cover]) -> str:
        return (
            f"{self.config.homeassistant.discovery_prefix}/{name}/"
            f"{self.config.device_info.name.lower()}/{item.object_id}/config"
        )

    def _get_unique_id(self, feature: FeatureItem) -> str:
        return f"{self.config.device_info.name.lower()}_{feature.object_id}"

    def _get_device_name(self, feature: FeatureItem) -> str:
        suggested_area: Optional[str] = self._get_suggested_area(feature)
        device_name: str = self.config.device_info.name

        if feature.definition.device_name:
            device_name = feature.definition.device_name

        if suggested_area:
            device_name = f"{device_name}: {suggested_area}"

        return device_name

    def _get_device_model(self, feature: Optional[FeatureItem] = None) -> str:
        device_model: str = f'{self.hardware["neuron"].name} {self.hardware["neuron"].model}'

        if feature and feature.definition.model:
            device_model = f"{feature.definition.model}"

        return device_model

    def _get_device_manufacturer(self, feature: Optional[FeatureItem] = None) -> str:
        device_manufacturer: str = self.config.device_info.manufacturer

        if feature and feature.definition.manufacturer:
            device_manufacturer = f"{feature.definition.manufacturer}"

        return device_manufacturer

    def _get_invert_state(self, feature: FeatureItem) -> bool:
        """Check if invert state is enabled in the config."""

        if features_config := self.config.features.get(feature.object_id):
            return features_config.invert_state

        return False

    def _get_friendly_name(self, feature: FeatureItem) -> str:
        """Get the friendly name from the config. Used for ``Name`` in Home Assistant."""
        friendly_name: str = f"{self.config.device_info.name}: {feature.friendly_name}"

        if features_config := self.config.features.get(feature.object_id):
            friendly_name = features_config.friendly_name

        return friendly_name

    def _get_suggested_area(self, feature: FeatureItem) -> Optional[str]:
        """Get the suggested area from the config. Used for ``Area`` in Home Assistant."""
        suggested_area: Optional[str] = None

        if feature.definition.suggested_area:
            suggested_area = feature.definition.suggested_area

        if features_config := self.config.features.get(feature.object_id):
            suggested_area = features_config.suggested_area

        return suggested_area

    def _get_object_id(self, feature: FeatureItem) -> Optional[str]:
        """Get the object ID from the config. Used for ``Entity ID`` in Home Assistant."""
        object_id: Optional[str] = None

        if features_config := self.config.features.get(feature.object_id):
            object_id = features_config.id.lower()

        return object_id
