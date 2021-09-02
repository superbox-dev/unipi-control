#!/usr/bin/env python3

import argparse
import asyncio
import json
import os
import _thread
import uuid
from collections import namedtuple
from timeit import default_timer as timer

import paho.mqtt.client as mqtt

from devices import (
    DeviceDigitalInput,
    DeviceDigitalOutput,
    DeviceRelay,
)
from settings import (
    CONFIG,
    logger,
)


class MqttMixin:
    """Mqtt mixin for connecting to Mqtt broker."""

    def connect(self, client_id: str):
        """Connect to mqtt broker.

        Args:
            client_id (str): unique client id
        """
        client = mqtt.Client(client_id)
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message

        client.connect(CONFIG["mqtt"]["host"], CONFIG["mqtt"]["port"])
        client.loop_start()

        return client

    def on_connect(self, client, userdata, flags, rc: int) -> None:
        """Subscribe topics on connect to mqtt broker."""
        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Connected to MQTT Broker at `{client._host}:{client._port}`")
        else:
            logger.error(f"Failed to connect, return code `{rc}`")

        self.subscribe()

    def on_disconnect(self, client, userdata, rc: int) -> None:
        """Stop loop on disconnect from mqtt broker."""
        logger.info(f"Disconnected result code `{rc}`")
        client.loop_stop()

    def on_message(self, client, userdata, message) -> None:
        """Execude subscribe callback in a new thread."""
        logger.debug(f"Received `{message.payload.decode()}` from topic `{message.topic}`")
        _thread.start_new_thread(self.subscribe_thread, (message, ))


class UnipiMqttAPI(MqttMixin):
    """Unipi mqtt APi for read/write SysFS files and send topics."""

    def __init__(self, client_id: str, debug: bool):
        """Connect to mqtt broker.

        Args:
            client_id (str): unique client id
            debug (bool): enable debug logging
        """
        logger.info(f"Client ID: {client_id}")

        self.debug: bool = debug
        self._client = self.connect(client_id)
        self._devices: dict = {}
        self._publish_timer = None
        self._subscribe_timer = None

    @property
    def devices(self) -> dict:
        """Create devices dict with circuit as name and die device class as key."""
        _devices: dict = {}

        for circuit in os.listdir(CONFIG["sysfs"]["devices"]):
            device_path: str = os.path.join(CONFIG["sysfs"]["devices"], circuit)
            
            for device_class in [DeviceRelay, DeviceDigitalInput, DeviceDigitalOutput]:
                if device_class.FOLDER_REGEX.match(circuit):
                    _devices[circuit] = device_class(device_path)

        return _devices

    async def run(self) -> None:
        """Run publish method in a endless asyncio loop."""
        devices: dict = self.devices

        while True:
            self._publish_timer = timer()
            results: list = await asyncio.gather(*[device.get() for device in devices.values()])

            for device in results:
                if device.changed:
                    self.publish(device)

            await asyncio.sleep(250e-3)

    def subscribe_thread(self, message):
        """Run subscribe method in a thread.

        Args:
            message (dict): message dict from the mqtt on_message method.
        """
        self._subscribe_timer = timer()

        async def subscribe_cb(message):
            for device_class in [DeviceRelay, DeviceDigitalOutput]:
                match = device_class.FOLDER_REGEX.search(message.topic)

                if match:
                    await self.devices[match.group(0)].set(
                        json.loads(message.payload.decode())
                    )

        asyncio.run(subscribe_cb(message), debug=self.debug)
        logger.debug(f"Subscribe timer: {timer() - self._subscribe_timer}")

    def subscribe(self) -> None:
        """Subscribe topics for relay devices."""
        for device_name in os.listdir(CONFIG["sysfs"]["devices"]):
            device_path: str = os.path.join(CONFIG["sysfs"]["devices"], device_name)

            for device_class in [DeviceRelay, DeviceDigitalOutput]:
                if device_class.FOLDER_REGEX.match(device_name):
                    device = device_class(device_path)
                    topic: str = f"unipi/{device.dev}/{device.circuit}/set"

                    self._client.subscribe(topic, qos=1)
                    logger.info(f"Subscribe topic `{topic}`")

    def publish(self, device: namedtuple) -> None:
        """Publish topics for all devices.

        Args:
            device (namedtuple): device infos from the device class."
        """
        topic: str = f"unipi/{device.dev}/{device.circuit}/get"

        values: dict = {k: v for k, v in dict(device._asdict()).items() if v is not None}
        values.pop("changed")

        payload: str = json.dumps(values)
        rc, mid = self._client.publish(topic, payload, qos=1)
        logger.debug(f"Publish timer: {timer() - self._publish_timer}")

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
