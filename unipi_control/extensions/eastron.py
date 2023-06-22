"""Initialize Eastron features."""

import asyncio
import typing
from typing import Optional
from typing import TYPE_CHECKING

from unipi_control.config import Config
from unipi_control.features.extensions import EastronMeter
from unipi_control.features.extensions import Hardware
from unipi_control.features.extensions import MeterProps
from unipi_control.features.extensions import Modbus
from unipi_control.features.map import FeatureMap
from unipi_control.features.utils import FeatureType
from unipi_control.helpers.typing import EastronModbusFeature
from unipi_control.helpers.typing import HardwareDefinition
from unipi_control.helpers.typing import ModbusClient
from unipi_control.helpers.typing import ModbusReadData
from unipi_control.modbus import ModbusCacheData
from unipi_control.modbus import check_modbus_call

if TYPE_CHECKING:
    from pymodbus.pdu import ModbusResponse


class EastronSDM120M:
    RETRY_LIMIT: int = 5

    def __init__(
        self,
        config: Config,
        modbus_client: ModbusClient,
        modbus_cache_data: ModbusCacheData,
        definition: HardwareDefinition,
        features: FeatureMap,
    ) -> None:
        """Initialize Eastron SDM120M electricity meter."""
        self.config: Config = config
        self.modbus_client: ModbusClient = modbus_client
        self.modbus_cache_data: ModbusCacheData = modbus_cache_data
        self.definition: HardwareDefinition = definition
        self.features: FeatureMap = features
        self._sw_version: Optional[str] = None

    def _parse_feature_meter(self, modbus_feature: EastronModbusFeature) -> None:
        meter: EastronMeter = EastronMeter(
            config=self.config,
            modbus=Modbus(
                cache=self.modbus_cache_data,
                val_reg=modbus_feature["val_reg"],
            ),
            hardware=Hardware(
                feature_type=FeatureType[modbus_feature["feature_type"]],
                definition=self.definition,
                version=self._sw_version,
            ),
            props=MeterProps(
                friendly_name=modbus_feature["friendly_name"],
                device_class=modbus_feature.get("device_class", None),
                state_class=modbus_feature.get("state_class", None),
                unit_of_measurement=modbus_feature.get("unit_of_measurement", None),
            ),
        )

        self.features.register(meter)

    def _parse_feature(self, modbus_feature: EastronModbusFeature) -> None:
        feature_type: str = modbus_feature["feature_type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(modbus_feature)

    async def _get_sw_version(self) -> Optional[str]:
        sw_version: str = "Unknown"

        data: ModbusReadData = {
            "address": 64514,
            "count": 2,
            "slave": self.definition.unit,
        }

        retry: bool = True
        retry_reconnect: int = 0

        while retry:
            retry_reconnect += 1

            response: Optional[ModbusResponse] = await check_modbus_call(
                self.modbus_client.serial.read_holding_registers, data
            )

            if response:
                meter_code: str = (
                    f"{format(getattr(response, 'registers',[0])[0], '0x')}"
                    f"{format(getattr(response, 'registers',[0])[1], '0x')}"
                )
                sw_version = f"{meter_code[:3]}.{meter_code[3:]}"
                retry = False

            if retry_reconnect == self.RETRY_LIMIT:
                retry = False

            await asyncio.sleep(1)

        return sw_version

    def parse_features(self) -> None:
        """Parse features from hardware definition."""
        for modbus_feature in self.definition.modbus_features:
            self._parse_feature(typing.cast(EastronModbusFeature, modbus_feature))

    async def init(self) -> None:
        """Initialize Eastron SDM120M device class.

        Read software version from Modbus RTU and parse features.
        """
        self._sw_version = await self._get_sw_version()
        self.parse_features()
