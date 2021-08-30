#!/usr/bin/env python3

import asyncio
import os
import uuid

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
        if rc == 0:
            logger.info(f"Connected to MQTT Broker at `{client._host}:{client._port}`")
        else:
            logger.error("Failed to connect, return code `{rc}`")

        self.subscribe()

    def on_disconnect(self, client, userdata, rc: int) -> None:
        logger.info(f"Disconnected result code `{rc}`")
        client.loop_stop()

    def on_message(self, client, userdata, message) -> None:
        logger.debug(f"Received `{message.payload.decode()}` from topic `{message.topic}`")


class UnipiMqtt(MqttMixin):
    def __init__(self, client_id: str):
        logger.info(f"Client ID: {client_id}")
        self.client = self.connect(client_id)
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
            results = await asyncio.gather(*[device.get() for device in devices.values()])

            for device in results:
                if device.changed:
                    self.publish(device)

            await asyncio.sleep(250e-3)

    def on_message(self, client, userdata, message) -> None:
        super().on_message(client, userdata, message)

        match = DeviceRelay.FOLDER_REGEX.search(message.topic)

        if match:
            self.devices[match.group(0)].set(message.payload.decode())

    def subscribe(self) -> None:
        for device_name in os.listdir(CONFIG["sysfs"]["devices"]):
            device_path: str = os.path.join(CONFIG["sysfs"]["devices"], device_name)

            if DeviceRelay.FOLDER_REGEX.match(device_name):
                device = DeviceRelay(device_path)
                topic: str = f"unipi/{device.name}/{device.circuit}/set"

                self.client.subscribe(topic, qos=1)
                logger.info(f"Subscribe circuit `{topic}`")

    def publish(self, device) -> None:
        topic: str = f"unipi/{device.name}/{device.circuit}/get"
        value: bool = device.value
        result: tuple = self.client.publish(topic, value, qos=1)

        if result[0] == 0:
            logger.info(f"Send `{value}` to topic `{topic}`")
        else:
            logger.error(f"Failed to send message to topic `{topic}`")


if __name__ == "__main__":
    client_id: str = f"unipi-{uuid.uuid4()}"

    try:
        asyncio.run(UnipiMqtt(client_id).run())
    except KeyboardInterrupt:
        logger.info("Process interrupted")
    except Exception as e:
        print(e)
