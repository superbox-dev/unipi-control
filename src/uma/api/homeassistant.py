import json
import os

import paho.mqtt.client as mqtt

from api.settings import (
    API,
    HA,
    logger,
)


class HomeAssistant:
    """HomeAssistant class for discovery topics."""

    def __init__(self, client, devices):
        self.client = client
        self.devices = devices

    def _read_firmware(self, value_path) -> str:
        group: str = os.path.abspath(os.path.join(os.path.realpath(value_path), *([os.pardir] * 2)))
        firmeware: str = os.path.join(group, "firmware_version")

        with open(firmeware, "r") as f:
            return f.read().rstrip()

    def _publish_relay(self, key, device_class) -> None:
        topic: str = f"""{HA["discovery_prefix"]}/switch/{API["device_name"]}/{device_class.circuit}/config"""
        firmware: str = self._read_firmware(device_class.value_path)
        unique_id: str = f"""{API["device_name"]}_{device_class.circuit}"""

        discovery: dict = {
            "name": device_class.dev_name,
            "unique_id": unique_id,
            "state_topic": f"{key}/get",
            "command_topic": f"{key}/set",
            "payload_on": "1",
            "payload_off": "0",
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "retain": "true",
            "device": {
                "name": f"""{HA["device"]["manufacturer"]} {device_class.dev_name}""",
                "identifiers": unique_id,
                "sw_version": firmware,
                **HA["device"],
            }
        }

        payload: str = json.dumps(discovery)
        rc, mid = self.client.publish(topic, payload, qos=1, retain=True)

        self._mqtt_log(rc, mid, topic, payload)

    def _publish_input(self, key, device_class) -> None:
        topic: str = f"""{HA["discovery_prefix"]}/binary_sensor/{API["device_name"]}/{device_class.circuit}/config"""
        firmware: str = self._read_firmware(device_class.value_path)
        unique_id: str = f"""{API["device_name"]}_{device_class.circuit}"""

        discovery: dict = {
            "name": device_class.dev_name,
            "unique_id": unique_id,
            "state_topic": f"{key}/get",
            "payload_on": "1",
            "payload_off": "0",
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "device": {
                "name": f"""{HA["device"]["manufacturer"]} {device_class.dev_name}""",
                "identifiers": unique_id,
                "sw_version": firmware,
                **HA["device"],
            }
        }

        payload: str = json.dumps(discovery)
        rc, mid = self.client.publish(topic, payload, qos=1, retain=True)

        self._mqtt_log(rc, mid, topic, payload)

    def _mqtt_log(self, rc, mid, topic, payload) -> None:
        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Send `{payload}` to topic `{topic}` - Message ID: {mid}")
        else:
            logger.error(f"Failed to send message to topic `{topic}` - Message ID: {mid}")

    def publish(self) -> None:
        """Publish topics for discovery."""
        for key, device_class in self.devices.items():
            if device_class.dev == "relay":
                self._publish_relay(key, device_class)
            elif device_class.dev == "input":
                self._publish_input(key, device_class)
