import argparse
import asyncio
import sys
import uuid
from asyncio import Task
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Final
from typing import Optional
from typing import Set

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
from unipi_control.log import LOG_NAME
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

    def __init__(self, config: Config, modbus_client: ModbusClient) -> None:
        self.config: Config = config
        self.modbus_client: ModbusClient = modbus_client
        self.neuron: Neuron = Neuron(config=config, modbus_client=modbus_client)

    async def _init_tasks(self, stack: AsyncExitStack, mqtt_client: Client) -> None:
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
    async def _cancel_tasks(tasks) -> None:
        for task in tasks:
            if task.done():
                continue

            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                pass

    async def _modbus_connect(self) -> None:
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

    async def run(self) -> None:
        """Connect to Modbus and initialize Unipi Neuron hardware."""
        await self._modbus_connect()
        await self.neuron.init()

        await mqtt_connect(
            mqtt_config=self.config.mqtt,
            logger=logger,
            mqtt_client_id=f"{slugify(self.config.device_info.name)}-{uuid.uuid4()}",
            callback=self._init_tasks,
        )


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
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main() -> None:
    """Entrypoint for Unipi Control."""
    unipi_control: Optional[UnipiControl] = None

    try:
        args: argparse.Namespace = parse_args(sys.argv[1:])

        config: Config = Config()
        config.logging.init(LOG_NAME, log=args.log, log_path=Path("/var/log"), verbose=args.verbose)

        unipi_control = UnipiControl(
            config=config,
            modbus_client=ModbusClient(
                tcp=AsyncModbusTcpClient(host="localhost"),
                serial=AsyncModbusSerialClient(
                    port="/dev/extcomm/0/0",
                    baudrate=config.modbus.baud_rate,
                    parity=config.modbus.parity,
                    timeout=30,
                ),
            ),
        )

        asyncio.run(unipi_control.run())
    except ConfigException as error:
        logger.error("%s %s", LogPrefix.CONFIG, error)
        sys.exit(1)
    except UnexpectedException as error:
        logger.error(error)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        pass
    finally:
        if unipi_control:
            logger.info("Successfully shutdown the Unipi Control service.")
