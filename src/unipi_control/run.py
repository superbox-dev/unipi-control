#!/usr/bin/env python3
import argparse
import asyncio
import shutil
import subprocess
import sys
import uuid
from asyncio import Task
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Optional
from typing import Set

from asyncio_mqtt import Client
from asyncio_mqtt import Client as MqttClient
from asyncio_mqtt import MqttError
from pymodbus.client.asynchronous import schedulers
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient

from config import Config
from config import HardwareInfo
from config import logger
from covers import CoverMap
from neuron import Neuron
from plugins.covers import CoversMqttPlugin
from plugins.features import FeaturesMqttPlugin
from plugins.hass.binary_sensors import HassBinarySensorsMqttPlugin
from plugins.hass.covers import HassCoversMqttPlugin
from plugins.hass.switches import HassSwitchesMqttPlugin
from version import __version__


class UnipiControl:
    """Control Unipi I/O directly with MQTT commands.

    Unipi Control use Modbus for fast access to the I/O and provide MQTT
    topics for reading and writing the circuits. Optionally you can enable
    the Home Assistant MQTT discovery for binary sensors, switches and covers.
    """

    def __init__(self, config: Config, modbus_client):
        self.config: Config = config
        self.neuron: Neuron = Neuron(config=config, modbus_client=modbus_client, hardware_info=HardwareInfo)

        self._mqtt_client_id: str = f"{config.device_name.lower()}-{uuid.uuid4()}"
        logger.info("[MQTT] Client ID: %s", self._mqtt_client_id)

        self._retry_reconnect: int = 0

    async def _init_tasks(self):
        async with AsyncExitStack() as stack:
            tasks: Set[Task] = set()
            stack.push_async_callback(self._cancel_tasks, tasks)

            mqtt_client: Client = MqttClient(
                self.config.mqtt.host,
                self.config.mqtt.port,
                client_id=self._mqtt_client_id,
                keepalive=self.config.mqtt.keepalive,
            )

            await stack.enter_async_context(mqtt_client)
            self._retry_reconnect = 0

            logger.info("[MQTT] Connected to broker at '%s:%s'", self.config.mqtt.host, self.config.mqtt.port)

            features = FeaturesMqttPlugin(self, mqtt_client)
            features_tasks = await features.init_tasks(stack)
            tasks.update(features_tasks)

            covers = CoverMap(config=self.config, features=self.neuron.features)

            covers_plugin = CoversMqttPlugin(mqtt_client, covers)
            covers_tasks = await covers_plugin.init_tasks(stack)
            tasks.update(covers_tasks)

            if self.config.homeassistant.enabled:
                hass_covers_plugin = HassCoversMqttPlugin(self, mqtt_client, covers)
                hass_covers_tasks = await hass_covers_plugin.init_tasks()
                tasks.update(hass_covers_tasks)

                hass_binary_sensors_plugin = HassBinarySensorsMqttPlugin(self, mqtt_client)
                hass_binary_sensors_tasks = await hass_binary_sensors_plugin.init_tasks()
                tasks.update(hass_binary_sensors_tasks)

                hass_switches_plugin = HassSwitchesMqttPlugin(self, mqtt_client)
                hass_switches_tasks = await hass_switches_plugin.init_tasks()
                tasks.update(hass_switches_tasks)

            await asyncio.gather(*tasks)

    async def _cancel_tasks(self, tasks):
        for task in tasks:
            if task.done():
                continue

            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass

    async def run(self):
        await self.neuron.read_boards()

        reconnect_interval: int = self.config.mqtt.reconnect_interval
        retry_limit: Optional[int] = self.config.mqtt.retry_limit

        while True:
            try:
                logger.info("[MQTT] Connecting to broker ...")
                await self._init_tasks()
            except MqttError as error:
                logger.error(
                    "[MQTT] Error '%s'. Connecting attempt #%s. Reconnecting in %s seconds.",
                    error,
                    self._retry_reconnect + 1,
                    reconnect_interval,
                )
            finally:
                if retry_limit and self._retry_reconnect > retry_limit:
                    sys.exit(1)

                self._retry_reconnect += 1

                await asyncio.sleep(reconnect_interval)


def install_unipi_control(assume_yes: bool):
    src_config_path: Path = Path(__file__).parents[0].joinpath("installer/etc/unipi")
    src_systemd_path: Path = Path(__file__).parents[0].joinpath("installer/etc/systemd/system/unipi-control.service")
    dest_config_path: Path = Path("/etc/unipi")

    print(f"Copy config files to '{dest_config_path}'")

    dirs_exist_ok: bool = False
    copy_config_files: bool = True

    if dest_config_path.exists():
        overwrite_config: str = "y"

        if not assume_yes:
            overwrite_config = input("\nOverwrite existing config files? [Y/n]")

        if overwrite_config.lower() == "y":
            dirs_exist_ok = True
        else:
            copy_config_files = False

    if copy_config_files:
        shutil.copytree(src_config_path, dest_config_path, dirs_exist_ok=dirs_exist_ok)  # type: ignore

    print("Copy systemd service 'unipi-control.service'")
    shutil.copyfile(src_systemd_path, "/etc/systemd/system/unipi-control.service")

    enable_and_start_systemd: str = "y"

    if not assume_yes:
        enable_and_start_systemd = input("\nEnable and start systemd service? [Y/n]")

    if enable_and_start_systemd.lower() == "y":
        print("Enable systemd service 'unipi-control.service'")
        status = subprocess.check_output("systemctl enable --now unipi-control", shell=True)

        if status:
            logger.info(status)
    else:
        print("\nYou can enable the systemd service with the command:")
        print("systemctl enable --now unipi-control")


def main():
    parser = argparse.ArgumentParser(description="Control Unipi I/O with MQTT commands")
    parser.add_argument("-i", "--install", action="store_true", help="install unipi control")
    parser.add_argument("-y", "--yes", action="store_true", help="automatic yes to install prompts")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    try:
        if args.install:
            install_unipi_control(assume_yes=args.yes)
        else:
            loop = asyncio.new_event_loop()
            loop, modbus = AsyncModbusTCPClient(schedulers.ASYNC_IO, loop=loop)

            uc = UnipiControl(config=Config(), modbus_client=modbus.protocol)

            try:
                loop.run_until_complete(uc.run())
            except asyncio.CancelledError:
                pass
            finally:
                logger.info("Successfully shutdown the Unipi Control service.")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
