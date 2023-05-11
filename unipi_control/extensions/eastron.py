import asyncio
from typing import Optional

from pymodbus.pdu import ModbusResponse

from unipi_control.config import HardwareDefinition
from unipi_control.features import EastronMeter
from unipi_control.modbus import check_modbus_call


class EastronSDM120M:
    def __init__(self, neuron, definition: HardwareDefinition) -> None:
        """Initialize Eastron SDM120M electricity meter.

        Attributes
        ----------
        neuron: class
            The Neuron class for registering features.
        """
        self.neuron = neuron
        self.definition: HardwareDefinition = definition
        self._sw_version: Optional[str] = None

    def _parse_feature_meter(self, modbus_feature: dict) -> None:
        meter: EastronMeter = EastronMeter(
            neuron=self.neuron,
            definition=self.definition,
            sw_version=self._sw_version,
            **modbus_feature,
        )

        self.neuron.features.register(meter)

    def _parse_feature(self, modbus_feature: dict) -> None:
        feature_type: str = modbus_feature["feature_type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(modbus_feature)

    async def _get_sw_version(self) -> Optional[str]:
        sw_version: str = "Unknown"

        data: dict = {
            "address": 64514,
            "count": 2,
            "slave": self.definition.unit,
        }

        retry: bool = True
        retry_reconnect: int = 0
        retry_limit: int = 5

        while retry:
            retry_reconnect += 1

            response: Optional[ModbusResponse] = await check_modbus_call(
                self.neuron.modbus_client.serial.read_holding_registers, data
            )

            if response:
                meter_code: str = (
                    f"{format(getattr(response, 'registers',[0])[0], '0x')}"
                    f"{format(getattr(response, 'registers',[0])[1], '0x')}"
                )
                sw_version = f"{meter_code[:3]}.{meter_code[3:]}"
                retry = False

            if retry_reconnect == retry_limit:
                retry = False

            await asyncio.sleep(1)

        return sw_version

    def parse_features(self) -> None:
        """Parse features from hardware definition."""
        for modbus_feature in self.definition.modbus_features:
            self._parse_feature(modbus_feature)

    async def init(self) -> None:
        """Initialize Eastron SDM120M device class.

        Read software version from Modbus RTU and parse features.
        """
        self._sw_version = await self._get_sw_version()
        self.parse_features()
