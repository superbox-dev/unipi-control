import asyncio
import json
from dataclasses import asdict

from config import config
from config import logger


class HassBinarySensorsDiscovery:
    def __init__(self, uc, mqtt_client):
        self.uc = uc
        self.mqtt_client = mqtt_client
        self._hw = uc.neuron.hw

    def _get_friendly_name(self, device) -> str:
        devices_config: dict = config.devices.get(device.circuit, {})
        friendly_name: str = devices_config.get('friendly_name', f"""{config.device_name} - {device.circuit_name}""")

        return friendly_name

    def _get_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/binary_sensor/{config.device_name.lower()}/{device.circuit}/config"""

        message: dict = {
            "name": self._get_friendly_name(device),
            "unique_id": f"""{config.device_name.lower()}_{device.circuit}""",
            "state_topic": f"{device.topic}/get",
            "qos": 2,
            "device": {
                "name": config.device_name,
                "identifiers": config.device_name.lower(),
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                "sw_version": self.uc.neuron.boards[device.major_group - 1].firmware,
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    async def publish(self) -> None:
        for device in self.uc.neuron.devices.by_device_type(["DI"]):
            topic, message = self._get_discovery(device)
            json_data: str = json.dumps(message)
            logger.info(f"""[MQTT][{topic}] Publishing message: {json_data}""")
            await self.mqtt_client.publish(topic, json_data, qos=1)


class HassBinarySensorsMqttPlugin:
    def __init__(self, uc, mqtt_client):
        self.mqtt_client = mqtt_client
        self._hass = HassBinarySensorsDiscovery(uc, mqtt_client)

    async def init_task(self, stack) -> set:
        tasks = set()

        task = asyncio.create_task(self._hass.publish())
        tasks.add(task)

        return tasks
