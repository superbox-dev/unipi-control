import json
import os
from typing import Optional

import paho.mqtt.client as mqtt

from api.settings import (
    CLIENT,
    HA,
    logger,
)


class HomeAssistant:
    """HomeAssistant class for discovery topics."""

    def __init__(self, client, devices):
        logger.info("Initialize Home Assistant MQTT discovery")

        self.client = client
        self.devices = devices

    def _get_mapping(self, circuit) -> dict:
        return HA.get("mapping", {}).get(circuit, {})

    def _get_name(self, device_class) -> str:
        custom_name: Optional[str] = self._get_mapping(device_class.circuit).get("name")

        if custom_name:
            return f"{custom_name} ({device_class.dev_name})"

        return device_class.dev_name

    def _get_suggested_area(self, device_class) -> str:
        return self._get_mapping(device_class.circuit).get("suggested_area", "")

    def _read_firmware(self, value_path) -> str:
        group: str = os.path.abspath(os.path.join(os.path.realpath(value_path), *([os.pardir] * 2)))
        firmeware: str = os.path.join(group, "firmware_version")

        with open(firmeware, "r") as f:
            return f.read().rstrip()

    def _publish_relay(self, key, device_class) -> None:
        topic: str = f"""{HA["discovery_prefix"]}/switch/{CLIENT["device_name"]}/{device_class.circuit}/config"""
        firmware: str = self._read_firmware(device_class.value_path)
        unique_id: str = f"""{CLIENT["device_name"]}_{device_class.circuit}"""

        discovery: dict = {
            "name": self._get_name(device_class),
            "unique_id": unique_id,
            "state_topic": f"{key}/get",
            "command_topic": f"{key}/set",
            "payload_on": "1",
            "payload_off": "0",
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "retain": "true",
            "device": {
                # "suggested_area": self._get_suggested_area(device_class),
                "sw_version": firmware,
                **HA["device"],
            }
        }

        payload: str = json.dumps(discovery)
        rc, mid = self.client.publish(topic, payload, qos=1, retain=True)

        self._mqtt_log(rc, mid, topic, payload)

    def _publish_input(self, key, device_class) -> None:
        topic: str = f"""{HA["discovery_prefix"]}/binary_sensor/{CLIENT["device_name"]}/{device_class.circuit}/config"""
        firmware: str = self._read_firmware(device_class.value_path)
        unique_id: str = f"""{CLIENT["device_name"]}_{device_class.circuit}"""

        discovery: dict = {
            "name": self._get_name(device_class),
            "unique_id": unique_id,
            "state_topic": f"{key}/get",
            "payload_on": "1",
            "payload_off": "0",
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "device": {
                # "suggested_area": self._get_suggested_area(device_class),
                "sw_version": firmware,
                **HA["device"],
            }
        }

        payload: str = json.dumps(discovery)
        rc, mid = self.client.publish(topic, payload, qos=1, retain=True)

        self._mqtt_log(rc, mid, topic, payload)

    def _mqtt_log(self, rc, mid, topic, payload) -> None:
        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"Send `{payload}` to topic `{topic}` - Message ID: {mid}")
        else:
            logger.error(f"Failed to send message to topic `{topic}` - Message ID: {mid}")

    def publish(self) -> None:
        """Publish topics for discovery."""
        for key, device_class in self.devices.items():
            if device_class.dev == "relay":
                self._publish_relay(key, device_class)
            elif device_class.dev == "input":
                self._publish_input(key, device_class)
