from abc import ABC
from abc import abstractmethod
from typing import Optional
from typing import Tuple

from config import FeatureConfig
from config import config


class HassBaseDiscovery(ABC):
    @staticmethod
    def _get_invert_state(feature) -> bool:
        features_config: FeatureConfig = config.features.get(feature.circuit)

        if features_config:
            return features_config.invert_state

        return False

    def _get_friendly_name(self, feature) -> str:
        friendly_name: str = f"{config.device_name} {feature.circuit_name}"
        features_config: FeatureConfig = config.features.get(feature.circuit)

        if features_config:
            friendly_name = features_config.friendly_name

        return friendly_name

    @staticmethod
    def _get_suggested_area(feature) -> Optional[str]:
        suggested_area: str = ""
        features_config: FeatureConfig = config.features.get(feature.circuit)

        if features_config:
            suggested_area = features_config.suggested_area

        return suggested_area

    @abstractmethod
    def _get_discovery(self, feature) -> Tuple[str, dict]:
        pass

    @abstractmethod
    async def publish(self):
        pass
