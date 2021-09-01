#!/usr/bin/env python3

import argparse
import json

import paho.mqtt.client as mqtt

from settings import CONFIG


class TestMqtt:
    def __init__(self):
        self.client = mqtt.Client(client_id="unipi-mqtt")
        self.client.connect(CONFIG["mqtt"]["host"], CONFIG["mqtt"]["port"])
        self.client.loop_start()

    def set(self, topic: str, value: str) -> None:
        topic: str = f"{topic}/set"
        
        values: dict = {
            "value": "0",
        }

        if value.lower() in ["t", "1", "true", "on"]:
            values["value"] = "1"

        payload: str = json.dumps(values)    
        rc, mid = self.client.publish(topic, payload)
        
        if rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"Send `{payload}` to topic `{topic}`")
        else:
            print(f"Failed to send message to topic `{topic}`")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("topic", type=str, help="Topic")
    parser.add_argument("value", type=str, help="Value")

    args = parser.parse_args()

    TestMqtt().set(topic=args.topic, value=args.value)
