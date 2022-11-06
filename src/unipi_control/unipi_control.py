#!/usr/bin/env python3
import argparse
import asyncio
import shutil
import subprocess
import uuid
from asyncio import Task
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Final
from typing import Set

import sys
from asyncio_mqtt import Client
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.client import AsyncModbusTcpClient

from superbox_utils.argparse import init_argparse
from superbox_utils.config.exception import ConfigException
from superbox_utils.core.exception import UnexpectedException
from superbox_utils.mqtt.connect import mqtt_connect
from superbox_utils.text.text import slugify
from unipi_control.config import Config
from unipi_control.config import LogPrefix
from unipi_control.config import logger
from unipi_control.integrations.covers import CoverMap
from unipi_control.logging import LOG_NAME
from unipi_control.modbus import ModbusClient
from unipi_control.mqtt.discovery.binary_sensors import HassBinarySensorsMqttPlugin
from unipi_control.mqtt.discovery.covers import HassCoversMqttPlugin
from unipi_control.mqtt.discovery.sensors import HassSensorsMqttPlugin
from unipi_control.mqtt.discovery.switches import HassSwitchesMqttPlugin
from unipi_control.mqtt.features import MeterFeaturesMqttPlugin
from unipi_control.mqtt.features import NeuronFeaturesMqttPlugin
from unipi_control.mqtt.integrations.covers import CoversMqttPlugin
from unipi_control.neuron import Neuron
from unipi_control.version import __version__


class UnipiControl:
    """Control Unipi I/O directly with MQTT commands.

    Unipi Control use Modbus for fast access to the I/O and provide MQTT
    topics for reading and writing the circuits. Optionally you can enable
    the Home Assistant MQTT discovery for binary sensors, sensors, switches and covers.
    """

    NAME: Final[str] = "unipi-control"

    def __init__(self, config: Config, modbus_client: ModbusClient):
        self.config: Config = config
        self.modbus_client: ModbusClient = modbus_client
        self.neuron: Neuron = Neuron(config=config, modbus_client=modbus_client)

    async def _init_tasks(self, stack: AsyncExitStack, mqtt_client: Client):
        tasks: Set[Task] = set()
        stack.push_async_callback(self._cancel_tasks, tasks)

        await NeuronFeaturesMqttPlugin(self.neuron, mqtt_client).init_tasks(stack, tasks)
        await MeterFeaturesMqttPlugin(self.neuron, mqtt_client).init_tasks(tasks)

        covers = CoverMap(self.config, self.neuron.features)
        covers_plugin = CoversMqttPlugin(mqtt_client, covers)
        await covers_plugin.init_tasks(stack, tasks)

        if self.config.homeassistant.enabled:
            await HassCoversMqttPlugin(self.neuron, mqtt_client, covers).init_tasks(tasks)
            await HassBinarySensorsMqttPlugin(self.neuron, mqtt_client).init_tasks(tasks)
            await HassSensorsMqttPlugin(self.neuron, mqtt_client).init_tasks(tasks)
            await HassSwitchesMqttPlugin(self.neuron, mqtt_client).init_tasks(tasks)

        await asyncio.gather(*tasks)

    @staticmethod
    async def _cancel_tasks(tasks):
        for task in tasks:
            if task.done():
                continue

            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass

    async def _modbus_connect(self):
        await self.modbus_client.tcp.connect()

        if self.modbus_client.tcp.connected:
            logger.info(
                "%s TCP client connected to %s:%s",
                LogPrefix.MODBUS,
                self.modbus_client.tcp.params.host,
                self.modbus_client.tcp.params.port,
            )
        else:
            raise UnexpectedException(
                f"TCP client can't connect to {self.modbus_client.tcp.params.host}:{self.modbus_client.tcp.params.port}"
            )

        await self.modbus_client.serial.connect()

        if self.modbus_client.serial.connected:
            logger.info(
                "%s Serial client connected to %s",
                LogPrefix.MODBUS,
                self.modbus_client.serial.params.port,
            )
        else:
            raise UnexpectedException(f"Serial client can't connect to {self.modbus_client.serial.params.port}")

    async def run(self):
        """Connect to Modbus TCP and RTU and initialize Unipi Neuron hardware."""
        await self._modbus_connect()
        await self.neuron.init()

        await mqtt_connect(
            mqtt_config=self.config.mqtt,
            logger=logger,
            mqtt_client_id=f"{slugify(self.config.device_info.name)}-{uuid.uuid4()}",
            callback=self._init_tasks,
        )

    @classmethod
    def install(cls, config: Config, assume_yes: bool):
        """Interactive installer for Unipi Control.

        Parameters
        ----------
        config: Config
            Unipi Control configugration
        assume_yes: bool
            Non-interactive mode. Accept all prompts with ``yes``.
        """
        src_config_path: Path = Path(__file__).parents[0] / "installer/etc/unipi"
        src_systemd_path: Path = Path(__file__).parents[0] / f"installer/etc/systemd/system/{cls.NAME}.service"
        dest_config_path: Path = config.config_base_path

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
            print(f"Copy config files to '{dest_config_path}'")
            shutil.copytree(src_config_path, dest_config_path, dirs_exist_ok=dirs_exist_ok)

        print(f"Copy systemd service '{cls.NAME}.service'")
        shutil.copyfile(src_systemd_path, f"{config.systemd_path}/{cls.NAME}.service")

        enable_and_start_systemd: str = "y"

        if not assume_yes:
            enable_and_start_systemd = input("\nEnable and start systemd service? [Y/n]")

        if enable_and_start_systemd.lower() == "y":
            print(f"Enable systemd service '{cls.NAME}.service'")

            if status := subprocess.check_output(f"systemctl enable --now {cls.NAME}", shell=True):
                logger.info(status)
        else:
            print("\nYou can enable the systemd service with the command:")
            print(f"systemctl enable --now {cls.NAME}")


def parse_args(args: list) -> argparse.Namespace:
    """Initialize argument parser options.

    Parameters
    ----------
    args: list
        Arguments as list.

    Returns
    -------
    Argparse namespace
    """
    parser: argparse.ArgumentParser = init_argparse(description="Control Unipi I/O with MQTT commands")
    parser.add_argument("-i", "--install", action="store_true", help=f"install {UnipiControl.NAME}")
    parser.add_argument("-y", "--yes", action="store_true", help="automatic yes to install prompts")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main():
    """Entrypoint for Unipi Control script."""
    try:
        args: argparse.Namespace = parse_args(sys.argv[1:])

        config: Config = Config()
        config.logging.update_level(LOG_NAME, verbose=args.verbose)

        if args.install:
            UnipiControl.install(config=config, assume_yes=args.yes)
        else:
            unipi_control: UnipiControl = UnipiControl(
                config=config,
                modbus_client=ModbusClient(
                    tcp=AsyncModbusTcpClient(host="localhost"),
                    serial=AsyncModbusSerialClient(
                        port="/dev/extcomm/0/0",
                        baudrate=config.modbus.baud_rate,
                        parity=config.modbus.parity,
                        timeout=10,
                    ),
                ),
            )

            asyncio.run(unipi_control.run())
    except ConfigException as e:
        logger.error("%s %s", LogPrefix.CONFIG, e)
        sys.exit(1)
    except UnexpectedException as e:
        logger.error(e)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Successfully shutdown the Unipi Control service.")


if __name__ == "__main__":
    main()
