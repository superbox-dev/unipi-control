#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import _thread
import uuid
from collections import namedtuple

import paho.mqtt.client as mqtt

from devices import (
    DeviceDigitalInput,
    DeviceRelay,
)
from settings import (
    CONFIG,
    logger,
)


class MqttMixin:
    def connect(self, client_id):
        client = mqtt.Client(client_id)
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message

        client.connect(CONFIG["mqtt"]["host"], CONFIG["mqtt"]["port"])
        client.loop_start()

        return client

    def on_connect(self, client, userdata, flags, rc: int) -> None:
        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Connected to MQTT Broker at `{client._host}:{client._port}`")
        else:
            logger.error("Failed to connect, return code `{rc}`")

        self.subscribe()

    def on_disconnect(self, client, userdata, rc: int) -> None:
        logger.info(f"Disconnected result code `{rc}`")
        client.loop_stop()

    def on_message(self, client, userdata, message) -> None:
        logger.debug(f"Received `{message.payload.decode()}` from topic `{message.topic}`")
        _thread.start_new_thread(self.subscribe_thread, (message, ))


class UnipiMqttAPI(MqttMixin):
    def __init__(self, client_id: str, debug: bool):
        logger.info(f"Client ID: {client_id}")

        self.debug: bool = debug
        self._client = self.connect(client_id)
        self._devices: dict = {}

    @property
    def devices(self) -> dict:
        _devices: dict = {}

        for circuit in os.listdir(CONFIG["sysfs"]["devices"]):
            device_path: str = os.path.join(CONFIG["sysfs"]["devices"], circuit)

            if DeviceRelay.FOLDER_REGEX.match(circuit):
                _devices[circuit] = DeviceRelay(device_path)
            elif DeviceDigitalInput.FOLDER_REGEX.match(circuit):
                _devices[circuit] = DeviceDigitalInput(device_path)

        return _devices

    async def run(self) -> None:
        devices: dict = self.devices

        while True:
            results: list = await asyncio.gather(*[device.get() for device in devices.values()])

            for device in results:
                if device.changed:
                    self.publish(device)

            await asyncio.sleep(250e-3)

    def subscribe_thread(self, message):
        async def subscribe_cb(message):
            match = DeviceRelay.FOLDER_REGEX.search(message.topic)
            
            if match:
                await self.devices[match.group(0)].set(
                    json.loads(message.payload.decode())
                )
        
        asyncio.run(subscribe_cb(message), debug=self.debug)

    def subscribe(self) -> None:
        for device_name in os.listdir(CONFIG["sysfs"]["devices"]):
            device_path: str = os.path.join(CONFIG["sysfs"]["devices"], device_name)

            if DeviceRelay.FOLDER_REGEX.match(device_name):
                device = DeviceRelay(device_path)
                topic: str = f"unipi/{device.dev}/{device.circuit}/set"

                self._client.subscribe(topic, qos=1)
                logger.info(f"Subscribe topic `{topic}`")

    def publish(self, device: namedtuple) -> None:
        topic: str = f"unipi/{device.dev}/{device.circuit}/get"
        
        values: dict = dict(device._asdict())
        values.pop("changed")
        
        payload: str = json.dumps(values)
        rc, mid = self._client.publish(topic, payload, qos=1)

        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Send `{payload}` to topic `{topic}` - Message ID: {mid}")
        else:
            logger.error(f"Failed to send message to topic `{topic}` - Message ID: {mid}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, type=bool, help="Debug")
    args = parser.parse_args()

    client_id: str = f"unipi-{uuid.uuid4()}"

    try:
        asyncio.run(UnipiMqttAPI(client_id, debug=args.debug).run(), debug=args.debug)
    except KeyboardInterrupt:
        logger.info("Process interrupted")
    except Exception as e:
        print(e)
