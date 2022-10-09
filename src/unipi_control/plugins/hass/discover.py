from abc import ABC
from abc import abstractmethod
from typing import Optional
from typing import Tuple

from unipi_control.config import Config
from unipi_control.config import FeatureConfig


class HassBaseDiscovery(ABC):
    def __init__(self, config: Config):
        self.config: Config = config

    def _get_invert_state(self, feature) -> bool:
        """Check if invert state is enabled in the config."""
        features_config: Optional[FeatureConfig] = self.config.features.get(feature.circuit)

        if features_config:
            return features_config.invert_state

        return False

    def _get_friendly_name(self, feature) -> str:
        """Get the friendly name from the config. Used for ``Name`` in Home Assistant."""
        friendly_name: str = f"{self.config.device_info.name} {feature.circuit_name}"
        features_config: Optional[FeatureConfig] = self.config.features.get(feature.circuit)

        if features_config:
            friendly_name = features_config.friendly_name

        return friendly_name

    def _get_suggested_area(self, feature) -> Optional[str]:
        """Get the suggested area from the config. Used for ``Area`` in Home Assistant."""
        suggested_area: Optional[str] = None
        features_config: Optional[FeatureConfig] = self.config.features.get(feature.circuit)

        if features_config:
            suggested_area = features_config.suggested_area

        return suggested_area

    def _get_object_id(self, feature) -> Optional[str]:
        """Get the object ID from the config. Used for ``Entity ID`` in Home Assistant."""
        object_id: Optional[str] = None
        features_config: Optional[FeatureConfig] = self.config.features.get(feature.circuit)

        if features_config:
            object_id = features_config.id

        return object_id

    @abstractmethod
    def _get_discovery(self, feature) -> Tuple[str, dict]:
        pass

    @abstractmethod
    async def publish(self):
        pass
