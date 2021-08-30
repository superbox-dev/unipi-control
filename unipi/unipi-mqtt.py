#!/usr/bin/env python3

import asyncio
import os
import re
from typing import Union

import aiofiles
import paho.mqtt.client as mqtt

from helpers import (
    HelpersMixin,
    logger,
)


class CircuitMixin(HelpersMixin):
    """Circuit class mixin for observe the SysFS devices and publish to Mqtt."""

    def __init__(self, device_path: str, mqttc):
        """Initialize the circuit class.

        Args:
            device_path (str): SysFS path to the circuit file
            mqttc: Mqtt client
        """
        self.device_path: str = device_path
        self.mqttc = mqttc
        self._value: bool = False
        self._file_handle = None

    @property
    def device_name(self) -> str:
        """Get the circuit device name."""
        match = self.FOLDER_REGEX.search(self.device_path)
        start, end = match.span()
        return self.device_path[start:end]

    @property
    def value_path(self) -> str:
        """Get the circuit value file path."""
        return os.path.join(self.device_path, self.VALUE_FILENAME)

    async def _read_value_file(self) -> str:
        """Read circuit value file and return file content."""
        if self._file_handle is None:
            self._file_handle = await aiofiles.open(self.value_path, "r")
            self.show_msg(f"Observe `{self.value_path}`")

        await self._file_handle.seek(0)

        return await self._file_handle.read()

    # async def _write_value_file(self) -> None:
    #     """Write circuit value file."""
    #     async with aiofiles.open(self.value_path, "w") as file_handle:
    #         await file_handle.write('transform')

    #     self.show_msg(f"Set `{self.value_path}`")

    async def get(self) -> None:
        """Get circuit status."""
        updated_value: bool = await self._read_value_file() == "1\n"

        if updated_value != self._value:
            topic: str = f"unipi/circuit/{self.device_name}/get"
            ret = self.mqttc.publish(topic, updated_value)

            if ret[0] == 0:
                msg: str = f"Send `{updated_value}` to topic `{topic}`"
            else:
                msg: str = f"Failed to send message to topic `{topic}`"

            self.show_msg(msg)
            self._value = updated_value

    def set(self) -> None:
        """Set circuit status."""
        self.mqttc.subscribe(f"unipi/circuit/{self.device_name}/set", 0)


class CircuitRO(CircuitMixin):
    """Observe circuit relay output and publish with Mqtt."""

    FOLDER_REGEX = re.compile(r"ro_\d_\d{2}")
    VALUE_FILENAME = "ro_value"


class CircuitDI(CircuitMixin):
    """Observe circuit digital input and publish with Mqtt."""

    FOLDER_REGEX = re.compile(r"di_\d_\d{2}")
    VALUE_FILENAME = "di_value"
  

class UnipiMqtt(HelpersMixin):
    """API class for initialize observe circuits."""

    def __init__(self):
        """Initialize the API class."""
        self.sysfs_path = self.config["sysfs"]["devices"]

        #self.mqttc = mqtt.Client(client_id="unipi-mqtt")
        
        #self.mqttc.on_connect = self.on_connect
        #self.mqttc.on_message = self.on_message
        #self.mqttc.on_disconnect = self.on_disconnect
        #self.mqttc.on_subscribe = self.on_subscribe
        #self.mqttc.on_log = self.on_log

        #self.mqttc.connect(
        #    self.config["mqtt"]["host"],
        #    self.config["mqtt"]["port"],
        #)
        
        #self.mqttc.loop_start()

    @property
    def _devices(self):
        for device_name in os.listdir(self.sysfs_path):
            if CircuitRO.FOLDER_REGEX.match(device_name):
                yield device_name
            elif CircuitDI.FOLDER_REGEX.match(device_name):
                yield device_name

    @property
    def _circuits(self) -> list[Union[CircuitDI, CircuitRO]]:
        circuits: list[Union[CircuitDI, CircuitRO]] = []

        for device_name in self._devices:
            device_path = os.path.join(self.sysfs_path, device_name)

            if CircuitRO.FOLDER_REGEX.match(device_name):
                circuits.append(CircuitRO(device_path, mqttc=self.mqttc))
            elif CircuitDI.FOLDER_REGEX.match(device_name):
                circuits.append(CircuitDI(device_path, mqttc=self.mqttc))

        return circuits
    
    def on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            msg = f"Connected to MQTT Broker at `{client._host}:{client._port}`"
        else:
            msg = f"Failed to connect, return code `{rc}`"

        self.show_msg(msg)
        
        #client.subscribe("unipi/circuit/ro_3_05/set")
        #client.loop_forever()
        #for device_name in self._devices:
        #    device_path = os.path.join(self.sysfs_path, device_name)
        #    
        #    if CircuitRO.FOLDER_REGEX.match(device_name):
        #        print(f"unipi/circuit/{device_name}/set")
        #        client.subscribe(f"unipi/circuit/{device_name}/set")

    def on_message(self, client, userdata, message) -> None:
        self.show_msg(f"Received `{message.payload.decode()}` from `{message.topic}` topic")
        print(message, message.payload, type(message.payload), message.payload.decode(), type(message.payload.decode()))
        if message.retain == 1:
            self.show_msg("This is a retained message")

    def on_disconnect(self, client, userdata, rc) -> None:
        self.show_msg(f"Disconnected result code `{rc}`")
        client.loop_stop()
 
    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.show_msg(f"Subscribed: {mid} ({granted_qos})")

    def on_log(self, client, userdata, level, buf) -> None:
        self.show_msg(f"log: {buf}")

    def run(self) -> None:
        self.mqttc = mqtt.Client(client_id="unipi-mqtt")
        
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_message = self.on_message
        #self.mqttc.on_disconnect = self.on_disconnect
        #self.mqttc.on_subscribe = self.on_subscribe
        self.mqttc.on_log = self.on_log

        self.mqttc.connect(
            self.config["mqtt"]["host"],
            self.config["mqtt"]["port"],
        )
        
        #self.mqttc.loop_start()
        self.mqttc.subscribe("unipi/circuit/ro_3_05/set")
        self.mqttc.loop_forever()
        
        #while True:
            #asyncio.gather(*[circuit.get() for circuit in self._circuits])
            #await asyncio.sleep(250e-3)
        
            #asyncio.run(self._tasks(self._circuits))

    async def _tasks(self, circuits: list[Union[CircuitDI, CircuitRO]]) -> None:
        while True:
            asyncio.gather(*[circuit.get() for circuit in circuits])
            await asyncio.sleep(250e-3)


if __name__ == "__main__":
    try:
        #asyncio.run(UnipiMqtt().run())
        UnipiMqtt().run()
    except KeyboardInterrupt:
        logger.info("Process interrupted")
    except Exception as e:
        print(e)
