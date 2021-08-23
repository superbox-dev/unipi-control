#!/usr/bin/env python3

import argparse
import asyncio
import os
import re

import aiofiles

from helpers import (
    ConfigMixin,
    logger,
    VerboseMixin
)
from mqtt import Mqtt

SLEEP_INTERVAL: str = 250e-3
SYSFS_ROOT: str = "/sys/devices/platform/unipi_plc"


class DigitalInput(ConfigMixin, VerboseMixin):
    FOLDER_REGEX = re.compile(r"di_\d_\d{2}")

    def __init__(self, path: str, mqttc, value: bool = False, verbose: bool = False):
        self.path = path
        self.mqttc = mqttc
        self._verbose = verbose
        self._value = value
        self._file_handle = None

    @property
    def title(self) -> str:
        match = self.FOLDER_REGEX.search(self.path)
        start, end = match.span()
        return self.path[start:end]

    @property
    def value_path(self):
        return os.path.join(self.path, "di_value")

    async def _observe(self):
        """Read file, keep handle open"""
        if self._file_handle is None:
            self._file_handle = await aiofiles.open(self.value_path, "r")
            self.show_msg(f"Observe `{self.value_path}`")

        await self._file_handle.seek(0)

        return await self._file_handle.read()

    async def update(self):
        """Update internal value with latest"""
        updated_value: bool = await self._observe() == "1\n"

        if updated_value != self._value:
            topic: str = self.get_topic(self.title)
            ret = self.mqttc.publish(f"unipi/{topic}", updated_value)

            if ret[0] == 0:
                self.show_msg(f"Send `{updated_value}` to topic `unipi/{topic}`")
            else:
                self.show_msg(f"Failed to send message to topic unipi/{topic}")

            self._value = updated_value


class PublisherMqtt(Mqtt):
    def on_disconnect(self, client, userdata, rc=0) -> None:
        super().on_disconnect(self, client, userdata, rc=0)
        self.client.loop_stop()


class SysFS(ConfigMixin):
    def __init__(self, args):
        self.root = args.sysfs_root
        self._verbose = args.verbose
        self._di_to_observe: list = list(self.config["observe"].keys())
        
        mqtt = Mqtt(client_id="unipi-sysfs",  verbose=self._verbose)
        self.mqttc = mqtt.run()
        self.mqttc.connect_async(self.config["mqtt"]["host"], self.config["mqtt"]["port"])

    def listen(self):
        self.mqttc.loop_start()
        digital_inputs: list = self._enable_digital_inputs()
        asyncio.run(self._poll(digital_inputs, SLEEP_INTERVAL))

    @staticmethod
    async def _poll(digital_inputs: list, sleep_time: int):
        while True:
            tasks: list = [digital_input.update() for digital_input in digital_inputs]
            asyncio.gather(*tasks)
            await asyncio.sleep(sleep_time)

    def _enable_digital_inputs(self) -> list[DigitalInput]:
        regex = DigitalInput.FOLDER_REGEX
        paths: list[DigitalInput] = []

        for root, dirs, files in os.walk(self.root):
            for d in dirs:
                if regex.match(d) is not None and d in self._di_to_observe:
                    paths.append(DigitalInput(os.path.join(root, d), mqttc=self.mqttc, verbose=self._verbose))

        return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep", type=float, default=SLEEP_INTERVAL, help="Sleep time between updates")
    parser.add_argument("--sysfs_root", default=SYSFS_ROOT, help="sysfs root folder to scan for digital inputs")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    sysfs = SysFS(args=args)

    try:
        sysfs.listen()
    except KeyboardInterrupt:
        logger.info("Process interrupted")
    except Exception as e:
        print(e)
