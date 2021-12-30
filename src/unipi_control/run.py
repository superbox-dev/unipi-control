#!/usr/bin/env python3
import argparse
import asyncio
import shutil
import signal
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
from config import config
from config import logger
from covers import CoverMap
from neuron import Neuron
from plugins.covers import CoversMqttPlugin
from plugins.features import FeaturesMqttPlugin
from plugins.hass.binary_sensors import HassBinarySensorsMqttPlugin
from plugins.hass.covers import HassCoversMqttPlugin
from plugins.hass.switches import HassSwitchesMqttPlugin
from pymodbus.client.asynchronous import schedulers
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusTCPClient
from termcolor import colored


class UnipiControl:
    """Control Unipi I/O directly with MQTT commands.

    Unipi Control use Modbus for fast access to the I/O and provide MQTT
    topics for reading and writing the circuits. Optionally you can enable
    the Home Assistant MQTT discovery for binary sensors, switches and covers.
    """

    def __init__(self, modbus_client):
        self.neuron = Neuron(modbus_client)

        self._mqtt_client_id: str = f"{config.device_name.lower()}-{uuid.uuid4()}"
        logger.info("[MQTT] Client ID: %s", self._mqtt_client_id)

        self._tasks: Set[Task] = set()
        self._retry_reconnect: int = 0

    async def _init_tasks(self):
        async with AsyncExitStack() as stack:
            mqtt_client: Client = MqttClient(
                config.mqtt.host,
                config.mqtt.port,
                client_id=self._mqtt_client_id,
                keepalive=config.mqtt.keepalive,
            )

            await stack.enter_async_context(mqtt_client)
            self._retry_reconnect = 0

            logger.info('[MQTT] Connected to broker at "%s:%s"', config.mqtt.host, config.mqtt.port)

            features = FeaturesMqttPlugin(self, mqtt_client)
            tasks = await features.init_tasks(stack)
            self._tasks.update(tasks)

            covers = CoverMap(features=self.neuron.features)

            covers_plugin = CoversMqttPlugin(mqtt_client, covers)
            tasks = await covers_plugin.init_tasks(stack)
            self._tasks.update(tasks)

            if config.homeassistant.enabled:
                hass_covers_plugin = HassCoversMqttPlugin(self, mqtt_client, covers)
                tasks = await hass_covers_plugin.init_tasks()
                self._tasks.update(tasks)

                hass_binary_sensors_plugin = HassBinarySensorsMqttPlugin(self, mqtt_client)
                tasks = await hass_binary_sensors_plugin.init_tasks()
                self._tasks.update(tasks)

                hass_switches_plugin = HassSwitchesMqttPlugin(self, mqtt_client)
                tasks = await hass_switches_plugin.init_tasks()
                self._tasks.update(tasks)

            await asyncio.gather(*self._tasks)

    async def shutdown(self, s=None):
        if s:
            logger.info("Received exit signal %s...", s.name)

        tasks = [t for t in self._tasks if t is not t.done()]

        if tasks:
            logger.info("Cancelling %s outstanding tasks.", len(tasks))

        [task.cancel() for task in tasks]

        await asyncio.gather(*tasks)

    async def run(self):
        await self.neuron.read_boards()

        reconnect_interval: int = config.mqtt.reconnect_interval
        retry_limit: Optional[int] = config.mqtt.retry_limit

        while True:
            try:
                logger.info("[MQTT] Connecting to broker ...")
                await self._init_tasks()
            except MqttError as error:
                logger.error(
                    '[MQTT] Error "%s". Connecting attempt #%s. Reconnecting in %s seconds.',
                    error,
                    self._retry_reconnect + 1,
                    reconnect_interval,
                )
            finally:
                if retry_limit and self._retry_reconnect > retry_limit:
                    sys.exit(1)

                self._retry_reconnect += 1

                await asyncio.sleep(reconnect_interval)


def install_unipi_control():
    src_config_path: Path = Path(__file__).parents[0].joinpath("installer/etc/unipi")
    src_systemd_path: Path = Path(__file__).parents[0].joinpath("installer/lib/systemd/system/unipi-control.service")
    dest_config_path: Path = Path("/etc/unipi")

    print(colored(f"-> Copy config files to {dest_config_path}", "green"))

    dirs_exist_ok: bool = False
    copy_config_files: bool = True

    if dest_config_path.exists():
        overwrite_config: str = input("Overwrite existing config files? [Y/n]")

        if overwrite_config.lower() == "y":
            dirs_exist_ok = True
        else:
            copy_config_files = False

    if copy_config_files:
        shutil.copytree(src_config_path, dest_config_path, dirs_exist_ok=dirs_exist_ok)

    print(colored('-> Copy systemd service "unipi-control.service"', "green"))
    shutil.copyfile(src_systemd_path, "/lib/systemd/system/unipi-control.service")

    enable_and_start_systemd: str = input("Enable and start systemd service? [Y/n]")

    if enable_and_start_systemd.lower() == "y":
        print(colored('-> Enable systemd service "unipi-control.service"', "green"))
        status = subprocess.check_output("systemctl enable --now unipi-control", shell=True)
        logger.info(status)
    else:
        print(
            colored(
                "\nYou can enable the systemd service with the command:",
                "white",
                attrs=[
                    "bold",
                ],
            )
        )
        print(
            colored(
                "systemctl enable --now unipi-control",
                "magenta",
                attrs=[
                    "bold",
                ],
            )
        )


def main():
    parser = argparse.ArgumentParser(description="Control Unipi I/O with MQTT commands")
    parser.add_argument("-i", "--install", action="store_true", help="Install Unipi Control")
    args = parser.parse_args()

    if args.install:
        install_unipi_control()
    else:
        loop = asyncio.new_event_loop()
        loop, modbus = ModbusTCPClient(schedulers.ASYNC_IO, loop=loop)

        uc = UnipiControl(modbus.protocol)

        for _signal in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(_signal, lambda s=_signal: asyncio.create_task(uc.shutdown(s)))

        try:
            loop.run_until_complete(uc.run())
        except KeyboardInterrupt:
            pass
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Successfully shutdown the Unipi Control service.")


if __name__ == "__main__":
    main()
