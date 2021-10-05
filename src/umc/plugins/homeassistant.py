import asyncio
import json
from dataclasses import asdict
from typing import Optional

from umc.config import config
from umc.config import logger
from umc.devices import devices


class HomeAssistantMqttPlugin:
    def __init__(self, umc, mqtt_client):
        logger.info("[MQTT] Initialize Home Assistant MQTT plugin")
        self.umc = umc
        self.mqtt_client = mqtt_client
        self._hw = umc.neuron.hw

    async def init(self, stack) -> set:
        tasks = set()

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    def _get_mapping(self, circuit) -> dict:
        return config.homeassistant.mapping.get(circuit, {})

    def _get_name(self, device) -> str:
        custom_name: Optional[str] = self._get_mapping(device.circuit).get("name")

        if custom_name:
            return custom_name

        return f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}"""

    def _get_switch_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/switch/{config.device_name.lower()}/{device.circuit}/config"""

        message: dict = {
            "name": f"{self._get_name(device)} - {device.circuit_name}",
            "unique_id": f"""{config.device_name.lower()}_{device.circuit}""",
            "state_topic": f"{device.topic}/get",
            "command_topic": f"{device.topic}/set",
            "payload_on": 1,
            "payload_off": 0,
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "retain": "true",
            "device": {
                "name": f"{config.device_name} {device.major_group}/{len(self.umc.neuron.boards)}",
                # "connections": get_device_connections(),
                "identifiers": f"{config.device_name.lower()} {device.major_group}",
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                "sw_version": self.umc.neuron.boards[device.major_group - 1].firmware,
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    def _get_binary_sensor_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/binary_sensor/{config.device_name.lower()}/{device.circuit}/config"""

        message: dict = {
            "name": f"{self._get_name(device)} - {device.circuit_name}",
            "unique_id": f"""{config.device_name.lower()}_{device.circuit}""",
            "state_topic": f"{device.topic}/get",
            "payload_on": 1,
            "payload_off": 0,
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "device": {
                "name": f"{config.device_name} {device.major_group}/{len(self.umc.neuron.boards)}",
                # "connections": get_device_connections(),
                "identifiers": f"{config.device_name.lower()} {device.major_group}",
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                "sw_version": self.umc.neuron.boards[device.major_group - 1].firmware,
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    async def _publish(self) -> None:
        for device in devices.by_name(["RO", "DO"]):
            topic, message = self._get_switch_discovery(device)
            logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
            await self.mqtt_client.publish(topic, json.dumps(message), qos=1)

        for device in devices.by_name(["DI"]):
            topic, message = self._get_binary_sensor_discovery(device)
            logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
            await self.mqtt_client.publish(topic, json.dumps(message), qos=1)
