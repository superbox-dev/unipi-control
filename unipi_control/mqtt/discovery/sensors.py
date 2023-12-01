"""Initialize MQTT subscribe and publish for Home Assistant sensors."""

import json
from typing import Any
from typing import Dict
from typing import Optional
from typing import TYPE_CHECKING
from typing import Tuple
from typing import Union

from unipi_control.config import UNIPI_LOGGER
from unipi_control.features.eastron import Eastron
from unipi_control.helpers.log import LOG_MQTT_PUBLISH
from unipi_control.helpers.text import slugify
from unipi_control.mqtt.discovery.mixin import HassDiscoveryMixin

if TYPE_CHECKING:
    from unipi_control.hardware.map import HardwareDefinition


class HassSensorsDiscovery(HassDiscoveryMixin):
    """Provide the sensors (e.g. meter) as Home Assistant MQTT discovery."""

    def _get_via_device(self, feature: Eastron) -> Optional[str]:
        if (device_name := self.config.device_info.name) != self._get_device_name(feature):
            return device_name

        return None

    def _get_device_name(self, feature: Eastron) -> str:
        suggested_area: Optional[str] = feature.hardware.definition.suggested_area
        device_name: str = self.config.device_info.name
        definition: HardwareDefinition = feature.hardware.definition

        if definition.device_name:
            device_name = definition.device_name

        if suggested_area:
            device_name = f"{device_name} - {suggested_area}"

        return device_name

    def get_discovery(self, feature: Union[Eastron]) -> Tuple[str, Dict[str, Any]]:
        """Get MQTT topic and message for publish with mqtt.

        Parameters
        ----------
        feature:
            All meter features.

        Returns
        -------
        tuple:
            Return mqtt topic and message as tuple.
        """
        topic: str = (
            f"{self.config.homeassistant.discovery_prefix}/sensor"
            f"/{slugify(self.config.device_info.name)}"
            f"/{feature.object_id}/config"
        )

        device_name: str = self._get_device_name(feature)

        message: Dict[str, Any] = {
            "name": feature.friendly_name,
            "unique_id": feature.unique_id,
            "state_topic": f"{feature.topic}/get",
            "qos": 2,
            "force_update": True,
            "device": {
                "name": device_name,
                "identifiers": slugify(device_name),
                "model": self._get_device_model(feature),
                "sw_version": "" if feature.sw_version is None else str(feature.sw_version),
                "manufacturer": self._get_device_manufacturer(feature),
            },
        }

        if feature.object_id:
            message["object_id"] = feature.object_id

        if feature.icon:
            message["icon"] = feature.icon

        if feature.device_class:
            message["device_class"] = feature.device_class

        if feature.state_class:
            message["state_class"] = feature.state_class

        if feature.unit_of_measurement:
            message["unit_of_measurement"] = feature.unit_of_measurement

        if feature.hardware.definition.suggested_area:
            message["device"]["suggested_area"] = feature.hardware.definition.suggested_area

        if via_device := self._get_via_device(feature):
            message["device"]["via_device"] = via_device

        return topic, message

    async def publish(self, feature: Eastron) -> None:
        """Publish MQTT Home Assistant discovery topics for sensors."""
        if isinstance(feature, Eastron):
            topic, message = self.get_discovery(feature)
            json_data: str = json.dumps(message)
            await self.client.publish(topic=topic, payload=json_data, qos=2, retain=True)
            UNIPI_LOGGER.debug(LOG_MQTT_PUBLISH, topic, json_data)
