"""Initialize MQTT subscribe and publish for Home Assistant covers."""

import json
from typing import Any
from typing import Dict
from typing import Tuple

from aiomqtt import Client

from unipi_control.config import Config
from unipi_control.config import DEVICE_CLASSES
from unipi_control.config import HardwareMap
from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.log import LOG_MQTT_PUBLISH
from unipi_control.helpers.text import slugify
from unipi_control.integrations.covers import Cover
from unipi_control.integrations.covers import CoverMap
from unipi_control.devices.unipi import Unipi


class HassCoversDiscovery:
    """Provide the covers as Home Assistant MQTT discovery."""

    def __init__(self, covers: CoverMap, unipi: Unipi, mqtt_client: Client) -> None:
        self.mqtt_client: Client = mqtt_client
        self.covers: CoverMap = covers

        self.config: Config = unipi.config
        self.hardware: HardwareMap = unipi.hardware

    def get_discovery(self, cover: Cover) -> Tuple[str, Dict[str, Any]]:
        """Get MQTT topic and message for publish with MQTT.

        Parameters
        ----------
        cover:
            The Cover class.

        Returns
        -------
        tuple:
            Return MQTT topic and message as tuple.
        """
        topic: str = (
            f"{self.config.homeassistant.discovery_prefix}/cover"
            f"/{slugify(self.config.device_info.name)}/{cover.settings.object_id}/config"
        )
        device_name: str = self.config.device_info.name

        message: Dict[str, Any] = {
            "name": cover.settings.friendly_name,
            "unique_id": cover.unique_id,
            "object_id": cover.settings.object_id,
            "device_class": cover.settings.device_class,
            "command_topic": f"{cover.topic}/set",
            "state_topic": f"{cover.topic}/state",
            "qos": 2,
            "optimistic": False,
            "device": {
                "name": device_name,
                "identifiers": slugify(device_name),
                "model": f"{self.hardware.info.name} {self.hardware.info.model}",
                "manufacturer": self.config.device_info.manufacturer,
            },
        }

        if self.config.device_info.suggested_area:
            message["device"]["suggested_area"] = self.config.device_info.suggested_area

        if cover.settings.cover_run_time:
            message["position_topic"] = f"{cover.topic}/position"
            message["set_position_topic"] = f"{cover.topic}/position/set"

        if cover.properties.set_tilt:
            message["tilt_status_topic"] = f"{cover.topic}/tilt"
            message["tilt_command_topic"] = f"{cover.topic}/tilt/set"

        return topic, message

    async def publish(self) -> None:
        """Publish MQTT Home Assistant discovery topics for covers."""
        for cover in self.covers.by_device_classes(DEVICE_CLASSES):
            topic, message = self.get_discovery(cover)
            json_data: str = json.dumps(message)
            await self.mqtt_client.publish(topic=topic, payload=json_data, qos=2, retain=True)
            UNIPI_LOGGER.debug(LOG_MQTT_PUBLISH, topic, json_data)
