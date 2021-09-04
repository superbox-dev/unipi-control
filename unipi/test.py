#!/usr/bin/env python3

import argparse

import paho.mqtt.client as mqtt

from api.settings import API


class Mqtt:
    """Publish to the topic."""

    def __init__(self):
        """Conect to the mqtt broker."""
        self.client = mqtt.Client(client_id="unipi-mqtt")
        self.client.connect(API["mqtt"]["host"], API["mqtt"]["port"])
        self.client.loop_start()

    def publish(self, topic: str, payload: str) -> None:
        """Publish to the topic.

        Args:
            topic (str): Topic name
            payload (str): Dict as JSON string.
        """
        rc, mid = self.client.publish(topic, payload, qos=1)

        if rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Send `{payload}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic `{topic}`")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", type=str, help="Topic")
    parser.add_argument("payload", type=str, help="Payload")

    args = parser.parse_args()

    Mqtt().publish(topic=args.topic, payload=args.payload)
