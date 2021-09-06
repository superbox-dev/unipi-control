import json

import paho.mqtt.client as mqtt

from api.settings import (
    HA,
    logger,
)


class HomeAssistant:
    """HomeAssistant class for discovery topics."""

    def __init__(self, client, devices):
        self.client = client
        self.devices = devices

    def publish(self) -> None:
        """Publish topics for discovery."""
        for key, device_class in self.devices.items():
            if device_class.dev == "relay":
                topic: str = f"""{HA["discovery_prefix"]}/switch/unipi/{device_class.circuit}/config"""

                discovery: dict = {
                    "name": device_class.dev_name,
                    "unique_id": device_class.circuit,
                    "state_topic": f"{key}/get",
                    "command_topic": f"{key}/set",
                    "payload_on": "1",
                    "payload_off": "0",
                    "value_template": "{{ value_json.value }}",
                    "qos": 1,
                    "retain": "true",
                    "device": {
                        "identifiers": device_class.circuit,
                        **HA["device"],
                    }
                }

                payload: str = json.dumps(discovery)
                rc, mid = self.client.publish(topic, payload, qos=1, retain=True)    

                if rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"Send `{payload}` to topic `{topic}` - Message ID: {mid}")
                else:
                    logger.error(f"Failed to send message to topic `{topic}` - Message ID: {mid}")
