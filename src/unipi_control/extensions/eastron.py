from typing import Optional

from unipi_control.config import HardwareDefinition
from unipi_control.features import EastronMeter


class EastronSDM120M:
    def __init__(self, neuron, definition: HardwareDefinition):
        """Initialize Eastron SDM120M electricity meter.

        Attributes
        ----------
        neuron: class
            The Neuron class for registering features.
        """
        self.neuron = neuron
        self.definition: HardwareDefinition = definition
        self._sw_version: Optional[str] = None

    def _parse_feature_meter(self, modbus_feature: dict):
        meter: EastronMeter = EastronMeter(
            neuron=self.neuron,
            definition=self.definition,
            sw_version=self._sw_version,
            **modbus_feature,
        )

        self.neuron.features.register(meter)

    def _parse_feature(self, modbus_feature: dict):
        feature_type: str = modbus_feature["feature_type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(modbus_feature)

    async def _get_sw_version(self) -> Optional[str]:
        response = await self.neuron.modbus_client.serial.read_holding_registers(
            address=64514, count=2, slave=self.definition.unit
        )

        if response.isError():
            return None

        meter_code: str = f"{format(response.registers[0], '0x')}{format(response.registers[1], '0x')}"

        return f"{meter_code[:3]}.{meter_code[3:]}"

    def parse_features(self):
        for modbus_feature in self.definition.modbus_features:
            self._parse_feature(modbus_feature)

    async def init(self):
        self._sw_version = await self._get_sw_version()
        self.parse_features()
