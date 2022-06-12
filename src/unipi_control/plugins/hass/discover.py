from abc import ABC
from abc import abstractmethod
from typing import Optional
from typing import Tuple

from config import Config
from config import FeatureConfig


class HassBaseDiscovery(ABC):
    def __init__(self, config: Config):
        self.config: Config = config

    def _get_invert_state(self, feature) -> bool:
        features_config: FeatureConfig = self.config.features.get(feature.circuit)

        if features_config:
            return features_config.invert_state

        return False

    def _get_friendly_name(self, feature) -> str:
        friendly_name: str = f"{self.config.device_name} {feature.circuit_name}"
        features_config: FeatureConfig = self.config.features.get(feature.circuit)

        if features_config:
            friendly_name = features_config.friendly_name

        return friendly_name

    def _get_suggested_area(self, feature) -> Optional[str]:
        suggested_area: str = ""
        features_config: FeatureConfig = self.config.features.get(feature.circuit)

        if features_config:
            suggested_area = features_config.suggested_area

        return suggested_area

    @abstractmethod
    def _get_discovery(self, feature) -> Tuple[str, dict]:
        pass

    @abstractmethod
    async def publish(self):
        pass
