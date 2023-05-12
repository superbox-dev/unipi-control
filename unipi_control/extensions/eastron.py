import asyncio
from typing import Optional

from pymodbus.pdu import ModbusResponse

from unipi_control.config import BoardConfig
from unipi_control.config import Config
from unipi_control.config import NeuronHardware
from unipi_control.features.extensions import EastronMeter
from unipi_control.features.extensions import Hardware
from unipi_control.features.extensions import MeterProps
from unipi_control.features.extensions import Modbus
from unipi_control.features.map import FeatureType
from unipi_control.modbus import check_modbus_call


class EastronSDM120M:
    def __init__(
        self,
        config: Config,
        board_config: BoardConfig,
        neuron_hardware: NeuronHardware,
    ) -> None:
        """Initialize Eastron SDM120M electricity meter."""
        self.config: Config = config
        self.board_config: BoardConfig = board_config
        self.neuron_hardware: NeuronHardware = neuron_hardware
        self._sw_version: Optional[str] = None

    def _parse_feature_meter(self, modbus_feature: dict) -> None:
        meter: EastronMeter = EastronMeter(
            config=self.config,
            modbus=Modbus(
                cache=self.neuron_hardware.modbus_cache_data,
                val_reg=modbus_feature["val_reg"],
            ),
            hardware=Hardware(
                feature_type=FeatureType[modbus_feature["feature_type"]],
                definition=self.neuron_hardware.definition,
                version=self._sw_version,
            ),
            props=MeterProps(
                friendly_name=modbus_feature["friendly_name"],
                device_class=modbus_feature.get("device_class"),
                state_class=modbus_feature.get("state_class"),
                unit_of_measurement=modbus_feature.get("unit_of_measurement"),
            ),
        )

        self.neuron_hardware.features.register(meter)

    def _parse_feature(self, modbus_feature: dict) -> None:
        feature_type: str = modbus_feature["feature_type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(modbus_feature)

    async def _get_sw_version(self) -> Optional[str]:
        sw_version: str = "Unknown"

        data: dict = {
            "address": 64514,
            "count": 2,
            "slave": self.neuron_hardware.definition.unit,
        }

        retry: bool = True
        retry_reconnect: int = 0
        retry_limit: int = 5

        while retry:
            retry_reconnect += 1

            response: Optional[ModbusResponse] = await check_modbus_call(
                self.board_config.modbus_client.serial.read_holding_registers, data
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
        for modbus_feature in self.neuron_hardware.definition.modbus_features:
            self._parse_feature(modbus_feature)

    async def init(self) -> None:
        """Initialize Eastron SDM120M device class.

        Read software version from Modbus RTU and parse features.
        """
        self._sw_version = await self._get_sw_version()
        self.parse_features()
