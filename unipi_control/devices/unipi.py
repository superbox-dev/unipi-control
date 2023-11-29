"""Read hardware to initialize devices."""

from typing import List
from typing import Optional

from pymodbus.pdu import ModbusResponse

from unipi_control.config import Config
from unipi_control.config import HardwareMap
from unipi_control.config import HardwareType
from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.devices.unipi_board import UnipiBoard
from unipi_control.devices.unipi_board import UnipiBoardConfig
from unipi_control.devices.eastron import EastronSDM120M
from unipi_control.features.map import FeatureMap
from unipi_control.helpers.typing import ModbusClient
from unipi_control.helpers.typing import ModbusReadData
from unipi_control.modbus.helper import check_modbus_call
from unipi_control.modbus.helper import ModbusHelper


class Unipi:
    """Class that reads all boards from the Unipi PLC, extensions and third-party devices.

    The Unipi PLC has one or more boards and each board has its features (e.g. Relay, Digital Input).
    This class reads out all boards and append it to the boards ``list``.

    Attributes
    ----------
    modbus_client: ModbusClient
        A modbus tcp client.
    hardware: HardwareMap
        The Unipi PLC hardware definitions.
    unipi_boards: list
        All available boards from the Unipi PLC.
    features: FeatureMap
        All registered features (e.g. Relay, Digital Input, ...) from the
        Unipi PLC.
    """

    def __init__(self, config: Config, modbus_client: ModbusClient) -> None:
        self.config: Config = config

        self.modbus_client: ModbusClient = modbus_client
        self.hardware: HardwareMap = HardwareMap(config=config)
        self.features = FeatureMap()
        self.unipi_boards: List[UnipiBoard] = []

        self._modbus_helper: ModbusHelper = ModbusHelper(
            self.config,
            client=modbus_client,
            hardware=self.hardware,
        )

    async def init(self) -> ModbusHelper:
        """Initialize internal and external hardware."""
        UNIPI_LOGGER.debug("%s %s hardware definition(s) found.", LogPrefix.CONFIG, len(self.hardware))

        await self.read_boards()
        await self.read_extensions()

        UNIPI_LOGGER.info("%s %s features initialized.", LogPrefix.CONFIG, len(self.features))

        return self._modbus_helper

    @staticmethod
    def get_firmware(response: ModbusResponse) -> str:
        """Get the Unipi PLC firmware version.

        Parameters
        ----------
        response: ModbusResponse
            Modbus response PDU

        Returns
        -------
        str:
            Unipi PLC firmware version
        """
        versions = getattr(response, "registers", [0, 0])
        return f"{(versions[0] & 0xff00) >> 8}.{(versions[0] & 0x00ff)}"

    async def read_boards(self) -> None:
        """Initialize Unipi PLC boards on Modbus TCP."""
        UNIPI_LOGGER.info("%s Reading SPI boards", LogPrefix.MODBUS)

        self._modbus_helper.connect_tcp()

        for index in (1, 2, 3):
            data: ModbusReadData = {
                "address": 1000,
                "count": 1,
                "slave": index,
            }

            response: Optional[ModbusResponse] = check_modbus_call(self.modbus_client.tcp.read_input_registers, data)

            if response:
                firmware: str = self.get_firmware(response)

                UNIPI_LOGGER.info("%s Found board %s on SPI", LogPrefix.MODBUS, index)
                UNIPI_LOGGER.debug("%s Firmware version on board %s is %s", LogPrefix.MODBUS, index, firmware)

                board = UnipiBoard(
                    config=self.config,
                    modbus_client=self.modbus_client,
                    definition=self.hardware[HardwareType.PLC],
                    modbus_helper=self._modbus_helper,
                    features=self.features,
                    board_config=UnipiBoardConfig(
                        firmware=firmware,
                        major_group=index,
                    ),
                )
                board.parse_features()

                self.unipi_boards.append(board)
            else:
                UNIPI_LOGGER.info("%s No board on SPI %s", LogPrefix.MODBUS, index)

        self._modbus_helper.close_tcp()

    async def read_extensions(self) -> None:
        """Initialize extensions and other devices on Modbus RTU."""
        UNIPI_LOGGER.info("%s Reading extensions", LogPrefix.MODBUS)

        self._modbus_helper.connect_serial()

        for key, definition in self.hardware.items():
            if key == HardwareType.PLC:
                continue

            UNIPI_LOGGER.info(
                "%s [RTU] Found device with unit %s (manufacturer: %s, model: %s)",
                LogPrefix.MODBUS,
                definition.unit,
                definition.manufacturer,
                definition.model,
            )

            if (definition.manufacturer and definition.manufacturer.lower() == "eastron") and (
                definition.model and definition.model == "SDM120M"
            ):
                await EastronSDM120M(
                    config=self.config,
                    modbus_helper=self._modbus_helper,
                    definition=definition,
                    features=self.features,
                ).init()

        self._modbus_helper.close_serial()
