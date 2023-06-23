"""Unipi Control entry point for read configuration, initialize modbus and connect to mqtt."""

import argparse
import asyncio
import sys
import uuid
from asyncio import Task
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Awaitable
from typing import Callable
from typing import List
from typing import NoReturn
from typing import Optional
from typing import Set

from asyncio_mqtt import Client
from asyncio_mqtt import MqttError
from pymodbus.client.serial import AsyncModbusSerialClient
from pymodbus.client.tcp import AsyncModbusTcpClient

from unipi_control.config import Config
from unipi_control.config import DEFAULT_CONFIG_PATH
from unipi_control.config import LogPrefix
from unipi_control.config import MqttConfig
from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.argparse import init_argparse
from unipi_control.helpers.exception import ConfigError
from unipi_control.helpers.exception import UnexpectedError
from unipi_control.helpers.text import slugify
from unipi_control.helpers.typing import ModbusClient
from unipi_control.integrations.covers import CoverMap
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
        covers.init()

        covers_plugin = CoversMqttPlugin(mqtt_client, covers)
        await covers_plugin.init_tasks(stack, tasks)

        if self.config.homeassistant.enabled:
            await HassCoversMqttPlugin(self.neuron, mqtt_client, covers).init_tasks(tasks)
            await HassBinarySensorsMqttPlugin(self.neuron, mqtt_client).init_tasks(tasks)
            await HassSensorsMqttPlugin(self.neuron, mqtt_client).init_tasks(tasks)
            await HassSwitchesMqttPlugin(self.neuron, mqtt_client).init_tasks(tasks)

        await asyncio.gather(*tasks)

    @staticmethod
    async def _cancel_tasks(tasks: Set[Task]) -> None:
        for task in tasks:
            if task.done():
                continue

            try:
                task.cancel()
                await task
            except asyncio.CancelledError:
                ...

    async def _modbus_connect(self) -> None:
        await self.modbus_client.tcp.connect()  # type: ignore[no-untyped-call]

        if self.modbus_client.tcp.connected:
            UNIPI_LOGGER.info(
                "%s TCP client connected to %s:%s",
                LogPrefix.MODBUS,
                self.modbus_client.tcp.params.host,
                self.modbus_client.tcp.params.port,
            )
        else:
            exception_message_tcp: str = (
                f"{LogPrefix.MODBUS} TCP client can't connect to "
                f"{self.modbus_client.tcp.params.host}:{self.modbus_client.tcp.params.port}"
            )
            raise UnexpectedError(exception_message_tcp)

        await self.modbus_client.serial.connect()  # type: ignore[no-untyped-call]

        if self.modbus_client.serial.connected:
            UNIPI_LOGGER.info(
                "%s Serial client connected to %s",
                LogPrefix.MODBUS,
                self.modbus_client.serial.params.port,
            )
        else:
            exception_message_serial: str = (
                f"{LogPrefix.MODBUS} Serial client can't connect to {self.modbus_client.serial.params.port}"
            )
            raise UnexpectedError(exception_message_serial)

    @staticmethod
    async def mqtt_connect(
        mqtt_config: MqttConfig,
        mqtt_client_id: str,
        callback: Callable[[AsyncExitStack, Client], Awaitable[None]],
    ) -> NoReturn:
        """Connect to MQTT broker and automatically retry on disconnect.

        Parameters
        ----------
        mqtt_config: MqttConfig
            MQTT config class with hostname, port, keepalive, retry limit and reconnect interval.
        mqtt_client_id: str
            A unique MQTT client ID.
        callback: Callback
            A callback function that executed after successful MQTT connect.
        """
        UNIPI_LOGGER.info("%s Client ID: %s", LogPrefix.MQTT, mqtt_client_id)

        reconnect_interval: int = mqtt_config.reconnect_interval
        retry_limit: Optional[int] = mqtt_config.retry_limit
        retry_reconnect: int = 0

        while True:
            try:
                UNIPI_LOGGER.info("%s Connecting to broker ...", LogPrefix.MQTT)

                async with AsyncExitStack() as stack:
                    mqtt_client: Client = Client(
                        mqtt_config.host,
                        mqtt_config.port,
                        client_id=mqtt_client_id,
                        keepalive=mqtt_config.keepalive,
                    )

                    await stack.enter_async_context(mqtt_client)
                    retry_reconnect = 0

                    UNIPI_LOGGER.info(
                        "%s Connected to broker at '%s:%s'", LogPrefix.MQTT, mqtt_config.host, mqtt_config.port
                    )

                    await callback(stack, mqtt_client)
            except MqttError as error:
                UNIPI_LOGGER.error(
                    "%s Error '%s'. Connecting attempt #%s. Reconnecting in %s seconds.",
                    LogPrefix.MQTT,
                    error,
                    retry_reconnect + 1,
                    reconnect_interval,
                )
            finally:
                if retry_limit and retry_reconnect > retry_limit:
                    sys.exit(1)

                retry_reconnect += 1

                await asyncio.sleep(reconnect_interval)

    async def run(self) -> NoReturn:
        """Connect to Modbus and initialize Unipi Neuron hardware."""
        await self._modbus_connect()
        await self.neuron.init()

        await self.mqtt_connect(
            mqtt_config=self.config.mqtt,
            mqtt_client_id=f"{slugify(self.config.device_info.name)}-{uuid.uuid4()}",
            callback=self._init_tasks,
        )


def parse_args(args: List[str]) -> argparse.Namespace:
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
        default=DEFAULT_CONFIG_PATH,
        help=f"path to the configuration (default: {DEFAULT_CONFIG_PATH})",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args(args)


def main(argv: Optional[List[str]] = None) -> None:
    """Entrypoint for Unipi Control."""
    if argv is None:
        argv = sys.argv[1:]

    unipi_control: Optional[UnipiControl] = None

    try:
        args: argparse.Namespace = parse_args(argv)

        config: Config = Config(config_base_path=Path(args.config))
        config.logging.init(log=args.log, verbose=args.verbose)

        unipi_control = UnipiControl(
            config=config,
            modbus_client=ModbusClient(
                tcp=AsyncModbusTcpClient(
                    host="localhost",
                    timeout=0.5,
                    retries=3,
                    retry_on_empty=True,
                ),
                serial=AsyncModbusSerialClient(
                    port="/dev/extcomm/0/0",
                    baudrate=config.modbus.baud_rate,
                    parity=config.modbus.parity,
                    timeout=1,
                    retries=3,
                    retry_on_empty=True,
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
        ...
    except asyncio.CancelledError:
        ...
    finally:
        if unipi_control:
            UNIPI_LOGGER.info("Successfully shutdown the Unipi Control service.")
