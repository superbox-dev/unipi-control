import asyncio
import json
from asyncio import Task
from typing import Any
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from unipi_control.config import Config
from unipi_control.config import HardwareData
from unipi_control.config import logger
from unipi_control.features import FeatureState
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.plugins.hass.discover import HassBaseDiscovery


class HassSwitchesDiscovery(HassBaseDiscovery):
    """Provide the switches (e.g. relay) as Home Assistant MQTT discovery.

    Attributes
    ----------
    hardware : HardwareData
        The Unipi Neuron hardware definitions.
    """

    publish_feature_types: List[str] = ["RO", "DO"]

    def __init__(self, neuron, mqtt_client):
        self.config: Config = neuron.config
        self.hardware: HardwareData = neuron.hardware

        self._neuron = neuron
        self._mqtt_client = mqtt_client

        super().__init__(config=neuron.config)

    def _get_discovery(self, feature) -> Tuple[str, dict]:
        topic: str = (
            f"{self.config.homeassistant.discovery_prefix}/switch/"
            f"{self.config.device_info.name.lower()}/{feature.circuit}/config"
        )

        message: dict = {}

        if feature.circuit not in self.config.get_cover_circuits():
            object_id: Optional[str] = self._get_object_id(feature)
            invert_state: bool = self._get_invert_state(feature)
            suggested_area: Optional[str] = self._get_suggested_area(feature)
            device_name: str = self.config.device_info.name

            if suggested_area:
                device_name = f"{device_name}: {suggested_area}"

            message = {
                "name": self._get_friendly_name(feature),
                "unique_id": f"{self.config.device_info.name.lower()}_{feature.circuit}",
                "command_topic": f"{feature.topic}/set",
                "state_topic": f"{feature.topic}/get",
                "qos": 2,
                "device": {
                    "name": device_name,
                    "identifiers": device_name,
                    "model": f"""{self.hardware["neuron"]["name"]} {self.hardware["neuron"]["model"]}""",
                    "sw_version": self._neuron.boards[feature.major_group - 1].firmware,
                    "manufacturer": self.config.device_info.manufacturer,
                },
            }

            if object_id:
                message["object_id"] = object_id

            if suggested_area:
                message["device"]["suggested_area"] = suggested_area

            if invert_state:
                message["payload_on"] = FeatureState.OFF
                message["payload_off"] = FeatureState.ON

        return topic, message

    async def publish(self):
        for feature in self._neuron.features.by_feature_type(self.publish_feature_types):
            topic, message = self._get_discovery(feature)

            if message:
                json_data: str = json.dumps(message)
                await self._mqtt_client.publish(topic, json_data, qos=2, retain=True)
                logger.debug(LOG_MQTT_PUBLISH, topic, json_data)


class HassSwitchesMqttPlugin:
    """Provide Home Assistant MQTT commands for switches."""

    def __init__(self, neuron, mqtt_client):
        self._hass = HassSwitchesDiscovery(neuron, mqtt_client)

    async def init_tasks(self) -> Set[Task]:
        tasks: Set[Task] = set()

        task: Task[Any] = asyncio.create_task(self._hass.publish())
        tasks.add(task)

        return tasks
