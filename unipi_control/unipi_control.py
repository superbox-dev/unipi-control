"""Unipi Control entry point for read configuration, initialize modbus and connect to mqtt."""

import argparse
import asyncio
import sys
from asyncio import Task
from pathlib import Path
from typing import Set

from pymodbus.client.serial import ModbusSerialClient
from pymodbus.client.tcp import ModbusTcpClient
from typing import List
from typing import Optional
from unipi_control.config import Config
from unipi_control.config import DEFAULT_CONFIG_DIR
from unipi_control.config import LogPrefix

from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.argparse import init_argparse
from unipi_control.helpers.exceptions import ConfigError
from unipi_control.helpers.exceptions import UnexpectedError

from unipi_control.helpers.typing import ModbusClient
from unipi_control.mqtt.helper import MqttHelper
from unipi_control.devices.unipi import Unipi

from unipi_control.version import __version__
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unipi_control.modbus.helper import ModbusHelper


class UnipiControl:
    """Control Unipi I/O directly with MQTT commands.

    Unipi Control use Modbus for fast access to the I/O and provide MQTT
    topics for reading and writing the circuits. Optionally you can enable
    the Home Assistant MQTT discovery for binary sensors, sensors, switches,
    lights and covers.
    """

    def __init__(self, config: Config, modbus_client: ModbusClient) -> None:
        self.config: Config = config
        self.modbus_client: ModbusClient = modbus_client
        self.unipi: Unipi = Unipi(config=config, modbus_client=modbus_client)

    @classmethod
    def parse_args(cls, args: List[str]) -> argparse.Namespace:
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
        parser.add_argument(
            "-c",
            "--config",
            action="store",
            default=DEFAULT_CONFIG_DIR,
            help=f"path to the configuration (default: {DEFAULT_CONFIG_DIR})",
        )

        parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

        return parser.parse_args(args)

    async def run(self) -> None:
        """Connect to Modbus/MQTT and initialize hardware features."""
        modbus_helper: ModbusHelper = self.unipi.init()
        mqtt_helper: MqttHelper = MqttHelper(unipi=self.unipi)

        tasks: Set[Task] = set()

        tasks.add(asyncio.create_task(modbus_helper.scan_tcp()))
        tasks.add(asyncio.create_task(modbus_helper.scan_serial()))
        tasks.add(asyncio.create_task(mqtt_helper.run()))
        await asyncio.gather(*tasks)


def main(argv: Optional[List[str]] = None) -> None:
    """Entrypoint for Unipi Control."""
    if argv is None:
        argv = sys.argv[1:]

    unipi_control: Optional[UnipiControl] = None
    args: argparse.Namespace = UnipiControl.parse_args(argv)

    try:
        config: Config = Config(config_base_dir=Path(args.config))
        config.logging.init(log=args.log, verbose=args.verbose)

        unipi_control = UnipiControl(
            config=config,
            modbus_client=ModbusClient(
                tcp=ModbusTcpClient(
                    host=config.modbus_tcp.host,
                    port=config.modbus_tcp.port,
                ),
                serial=ModbusSerialClient(
                    port=config.modbus_serial.port,
                    baudrate=config.modbus_serial.baud_rate,
                    parity=config.modbus_serial.parity,
                ),
            ),
        )

        asyncio.run(unipi_control.run())
    except ConfigError as error:
        UNIPI_LOGGER.critical("%s %s", LogPrefix.CONFIG, error)
        sys.exit(1)
    except UnexpectedError as error:
        UNIPI_LOGGER.critical(error)
        sys.exit(1)
    except KeyboardInterrupt:
        UNIPI_LOGGER.info("Received exit, exiting")
    except asyncio.CancelledError:
        ...
    finally:
        if unipi_control:
            UNIPI_LOGGER.info("Successfully shutdown the Unipi Control service.")
