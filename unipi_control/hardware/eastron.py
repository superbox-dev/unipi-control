"""Initialize Eastron features."""

import typing
from typing import Optional
from typing import TYPE_CHECKING

from unipi_control.config import Config
from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.features.eastron import Eastron
from unipi_control.features.eastron import EastronHardware
from unipi_control.features.eastron import EastronProps
from unipi_control.features.eastron import EastronModbus
from unipi_control.features.map import FeatureMap
from unipi_control.features.constants import FeatureType
from unipi_control.hardware.map import EastronModbusFeature
from unipi_control.hardware.map import HardwareDefinition
from unipi_control.modbus.helpers import ModbusReadData
from unipi_control.modbus.helpers import check_modbus_call
from unipi_control.modbus.helpers import ModbusHelper

if TYPE_CHECKING:
    from pymodbus.pdu import ModbusResponse


class EastronSDM120M:
    def __init__(
        self,
        config: Config,
        modbus_helper: ModbusHelper,
        definition: HardwareDefinition,
        features: FeatureMap,
    ) -> None:
        """Initialize Eastron SDM120M electricity meter."""
        self.config: Config = config
        self.modbus_helper: ModbusHelper = modbus_helper
        self.definition: HardwareDefinition = definition
        self.features: FeatureMap = features
        self._sw_version: Optional[str] = None

    def _parse_feature_meter(self, modbus_feature: EastronModbusFeature) -> None:
        meter: Eastron = Eastron(
            config=self.config,
            modbus=EastronModbus(
                helper=self.modbus_helper,
                val_reg=modbus_feature["val_reg"],
            ),
            hardware=EastronHardware(
                feature_type=FeatureType[modbus_feature["feature_type"]],
                definition=self.definition,
                version=self._sw_version,
            ),
            props=EastronProps(
                friendly_name=modbus_feature["friendly_name"],
                device_class=modbus_feature.get("device_class"),
                state_class=modbus_feature.get("state_class"),
                unit_of_measurement=modbus_feature.get("unit_of_measurement"),
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

        response: Optional[ModbusResponse] = await check_modbus_call(
            self.modbus_helper.client.serial.read_holding_registers, data
        )

        if response:
            meter_code: str = (
                f"{format(getattr(response, 'registers',[0])[0], '0x')}"
                f"{format(getattr(response, 'registers',[0])[1], '0x')}"
            )
            sw_version = f"{meter_code[:3]}.{meter_code[3:]}"

        return sw_version

    def parse_features(self) -> None:
        """Parse features from hardware definition."""
        for modbus_feature in self.definition.modbus_features:
            self._parse_feature(typing.cast(EastronModbusFeature, modbus_feature))

    async def init(self) -> None:
        """Initialize Eastron SDM120M device class.

        Read Firmware version from Modbus RTU and parse features.
        """
        self._sw_version = await self._get_sw_version()
        UNIPI_LOGGER.debug("%s Firmware version on Eastron SDM120 is %s", LogPrefix.MODBUS, self._sw_version)

        self.parse_features()
