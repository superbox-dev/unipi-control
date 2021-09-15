#!/usr/bin/env python3

import os
import argparse
import asyncio
import json
import sys
import _thread
import time
import uuid
from collections import namedtuple
from timeit import default_timer as timer
from typing import Optional

import paho.mqtt.client as mqtt

from api.devices import (
    DeviceDigitalInput,
    DeviceDigitalOutput,
    DeviceRelay,
)
from api.homeassistant import HomeAssistant
from api.settings import (
    CLIENT,
    logger,
)


class UnipiMqttClient:
    """Unipi Mqtt client class for subscribe/publish topics."""

    def __init__(self, client_id: str, debug: bool):
        """Connect to mqtt broker.

        Args:
            client_id (str): unique client id
            debug (bool): enable debug logging
        """
        logger.info(f"Client ID: {client_id}")

        self.client = mqtt.Client(client_id)
        self.debug: bool = debug

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        self.client.connected_flag: bool = False

        self._devices: dict = {}
        self._publish_timer = None
        self._subscribe_timer = None
        
        self._retry = 0
        self._connected_once = False

        self._ha: Optional[HomeAssistant] = None

    @property
    def devices(self) -> dict:
        """Create devices dict with circuit as name and die device class as key."""
        _devices: dict = {}

        for circuit in os.listdir(CLIENT["sysfs"]["devices"]):
            device_path: str = os.path.join(CLIENT["sysfs"]["devices"], circuit)

            for device_class in [DeviceRelay, DeviceDigitalInput, DeviceDigitalOutput]:
                if device_class.FOLDER_REGEX.match(circuit):
                    device = device_class(device_path)
                    key: str = f"""{CLIENT["device_name"]}/{device.dev}/{device.dev_type}/{device.circuit}"""
                    _devices[key] = device

        return _devices

    async def run(self) -> None:
        """Run MQTT in a endless asyncio loop."""
        devices: dict = self.devices

        while True:
            self.client.loop(0.01)
            
            if self.client.connected_flag:
                self._retry = 0

                self._publish_timer = timer()
                results: list = await asyncio.gather(*[device.get() for device in devices.values()])

                for device in results:
                    if device.changed:
                        self.publish(device)
                    
                if not self._ha:    
                    self._ha = HomeAssistant(client=self.client, devices=self.devices)
                    self._ha.publish()

            if not self.client.connected_flag:
                try:
                    logger.info(f"Connecting attempt #{self._retry + 1}")            

                    self.client.connect(
                        CLIENT["mqtt"]["host"],
                        port=CLIENT["mqtt"]["port"],
                        keepalive=CLIENT["mqtt"]["connection"]["keepalive"],
                    )
                    
                    while not self.client.connected_flag:
                        logger.info("Connecting to MQTT broker ...")
                        self.client.loop(0.01)
                        time.sleep(1)
                except Exception:
                    logger.error(f"""Can't connect to MQTT broker at `{CLIENT["mqtt"]["host"]}:{CLIENT["mqtt"]["port"]}`""")
                    self._retry += 1
                    retry_limit: Optional[int] = CLIENT["mqtt"]["connection"]["retry_limit"]
                    
                    if retry_limit and self._retry > retry_limit:
                        sys.exit(1)

                    time.sleep(CLIENT["mqtt"]["connection"]["retry_interval"])

            await asyncio.sleep(250e-3)

    def on_connect(self, client, userdata, flags, rc: int) -> None:
        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Connected to MQTT broker at `{client._host}:{client._port}`")
            client.connected_flag = True

            self.subscribe(client)
        else:
            logger.error(f"Failed to connect! {mqtt.error_string(rc)}`")
            sys.exit(1)

    def on_disconnect(self, client, userdata, rc: int) -> None:
        logger.debug(f"Disconnected! {mqtt.error_string(rc)}")
        client.connected_flag = False

    def on_message(self, client, userdata, message) -> None:
        """Execude subscribe callback in a new thread."""
        logger.debug(f"Received `{message.payload.decode()}` from topic `{message.topic}`")
        _thread.start_new_thread(self.on_message_thread, (message, ))

    def on_message_thread(self, message):
        """Run on_message method in a thread.

        Args:
            message (dict): message dict from the mqtt on_message method.
        """
        self._subscribe_timer = timer()

        async def on_message_cb(message):
            key: str = message.topic[:-len("/set")]
            device = self.devices.get(key)
            
            if device:
                func = getattr(device, "set", None)

                if func:
                    await func(message.payload.decode())

                    # msg = message.payload.decode()
                    # try:
                    #     data: str = json.loads(msg)
                    # except ValueError as e:
                    #     logger.error(f"""Message `{msg}` is not a valid JSON - message not processed, error is "{e}".""")
                    # else:    
                    #     await func(json.loads(message.payload.decode()))
        
        asyncio.run(on_message_cb(message), debug=self.debug)
        logger.debug(f"Subscribe timer: {timer() - self._subscribe_timer}")

    def subscribe(self, client) -> None:
        """Subscribe topics for relay devices."""
        for device_name in os.listdir(CLIENT["sysfs"]["devices"]):
            device_path: str = os.path.join(CLIENT["sysfs"]["devices"], device_name)
            
            for device_class in [DeviceRelay, DeviceDigitalOutput]:
                if device_class.FOLDER_REGEX.match(device_name):
                    device = device_class(device_path)
                    topic: str = f"""{CLIENT["device_name"]}/{device.dev}/{device.dev_type}/{device.circuit}/set"""

                    client.subscribe(topic, qos=0)
                    logger.debug(f"Subscribe topic `{topic}`")

    def publish(self, device: namedtuple) -> None:
        """Publish topics for all devices.

        Args:
            device (namedtuple): device infos from the device class."
        """
        topic: str = f"""{CLIENT["device_name"]}/{device.dev}/{device.dev_type}/{device.circuit}/get"""
        values: dict = {k: v for k, v in dict(device._asdict()).items() if v is not None}
        values.pop("changed")

        payload: str = json.dumps(values)
        rc, mid = self.client.publish(topic, payload, qos=1)
        logger.debug(f"Publish timer: {timer() - self._publish_timer}")

        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"Send `{payload}` to topic `{topic}` - Message ID: {mid}")
        else:
            logger.error(f"Failed to send message to topic `{topic}` - Message ID: {mid}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, type=bool, help="Debug")
    args = parser.parse_args()

    try:
        asyncio.run(
            UnipiMqttClient(
                client_id=f"""{CLIENT["device_name"]}-{uuid.uuid4()}""", 
                debug=args.debug
            ).run(),
            debug=args.debug,
        )
    except KeyboardInterrupt:
        logger.info("Process interrupted")


if __name__ == "__main__":
    main()
