import json
from typing import Optional

from config import config
from config import ha_config
from config import logger
from devices import devices
from utils import get_device_connections
from utils import get_device_topic


class HomeAssistant:
    def __init__(self, neuron):
        logger.info("[MQTT] Initialize Home Assistant discovery")
        self._hw = neuron.hw

    @staticmethod
    def _get_mapping(circuit) -> dict:
        return ha_config.get("mapping", {}).get(circuit, {})

    def _get_name(self, device) -> str:
        custom_name: Optional[str] = self._get_mapping(device.circuit).get("name")

        if custom_name:
            return f"{custom_name} - {device.circuit_name}"

        return f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]} - {device.circuit_name}"""

    def _get_suggested_area(self, device) -> str:
        return self._get_mapping(device.circuit).get("suggested_area", "")

    def _get_switch_discovery(self, device) -> tuple:
        topic: str = f"""{ha_config["discovery_prefix"]}/switch/{config["device_name"]}/{device.circuit}/config"""

        message: dict = {
            "name": self._get_name(device),
            "unique_id": f"""{config["device_name"]}_{device.circuit}""",
            "state_topic": f"{get_device_topic(device)}/get",
            "command_topic": f"{get_device_topic(device)}/set",
            "payload_on": "1",
            "payload_off": "0",
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "retain": "true",
            "device": {
                "name": self._hw["neuron"]["name"],
                "connections": get_device_connections(),
                "model": self._hw["neuron"]["model"],
                # "suggested_area": self._get_suggested_area(device),
                # TODO: read firmeware from board
                "sw_version": self._hw["neuron"]["version"],
                **ha_config["device"],
            }
        }

        return topic, message

    def _get_binary_sensor_discovery(self, device) -> tuple:
        topic: str = f"""{ha_config["discovery_prefix"]}/binary_sensor/{config["device_name"]}/{device.circuit}/config"""

        message: dict = {
            "name": self._get_name(device),
            "unique_id": f"""{config["device_name"]}_{device.circuit}""",
            "state_topic": f"{get_device_topic(device)}/get",
            "payload_on": "1",
            "payload_off": "0",
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "device": {
                "name": self._hw["neuron"]["name"],
                "connections": get_device_connections(),
                "model": self._hw["neuron"]["model"],
                # "suggested_area": self._get_suggested_area(device_class),
                # TODO: read firmeware from board
                "sw_version": self._hw["neuron"]["version"],
                **ha_config["device"],
            }
        }

        return topic, message

    async def publish(self, mqtt_client) -> None:
        for device in devices.by_name(["RO", "DO"]):
            topic, message = self._get_switch_discovery(device)
            logger.debug(f"""[MQTT][{topic}] Publishing message: {message}""")
            await mqtt_client.publish(topic, json.dumps(message), qos=1)

        for device in devices.by_name(["DI"]):
            topic, message = self._get_binary_sensor_discovery(device)
            logger.debug(f"""[MQTT][{topic}] Publishing message: {message}""")
            await mqtt_client.publish(topic, json.dumps(message), qos=1)
