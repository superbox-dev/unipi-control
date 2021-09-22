import fcntl
import json
import socket
import struct
from dataclasses import asdict
from typing import Optional

from config import config
from config import logger
from devices import devices


def get_hw_addr(ifname: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack("256s", bytes(ifname, "utf-8")[:15]))
    return ":".join("%02x" % b for b in info[18:24])


def get_device_connections() -> list:
    connections: list = []

    for key, interface in socket.if_nameindex():
        hw_addr: str = get_hw_addr(interface)

        if hw_addr != "00:00:00:00:00:00":
            connections.append(["mac", hw_addr])
            break

    return connections


class HomeAssistant:
    def __init__(self, neuron):
        logger.info("[MQTT] Initialize Home Assistant discovery")
        self._hw = neuron.hw

    def _get_mapping(self, circuit) -> dict:
        return config.homeassistant.mapping.get(circuit, {})

    def _get_name(self, device) -> str:
        custom_name: Optional[str] = self._get_mapping(device.circuit).get("name")

        if custom_name:
            return f"{custom_name} - {device.circuit_name}"

        return f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]} - {device.circuit_name}"""

    def _get_suggested_area(self, device) -> str:
        return self._get_mapping(device.circuit).get("suggested_area", "")

    def _get_switch_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/switch/{config.device_name}/{device.circuit}/config"""

        message: dict = {
            "name": self._get_name(device),
            "unique_id": f"""{config.device_name}_{device.circuit}""",
            "state_topic": f"{device.topic}/get",
            "command_topic": f"{device.topic}/set",
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
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    def _get_binary_sensor_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/binary_sensor/{config.device_name}/{device.circuit}/config"""

        message: dict = {
            "name": self._get_name(device),
            "unique_id": f"""{config.device_name}_{device.circuit}""",
            "state_topic": f"{device.topic}/get",
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
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    async def publish(self, mqtt_client) -> None:
        for device in devices.by_name(["RO", "DO"]):
            topic, message = self._get_switch_discovery(device)
            logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
            await mqtt_client.publish(topic, json.dumps(message), qos=1)

        for device in devices.by_name(["DI"]):
            topic, message = self._get_binary_sensor_discovery(device)
            logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
            await mqtt_client.publish(topic, json.dumps(message), qos=1)
