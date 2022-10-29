from typing import NamedTuple

from superbox_utils.text.text import slugify
from unipi_control.config import Config
from unipi_control.config import HardwareDefinition
from unipi_control.modbus import ModbusClient


class MeterModbusInfo(NamedTuple):
    start_reg: int
    count_reg: int


class MeterFeature:
    feature_name: str = "meter"

    def __init__(
        self,
        neuron,
        short_name: str,
        description: str,
        modbus_info: MeterModbusInfo,
        definition: HardwareDefinition,
    ):
        self.config: Config = neuron.config
        self.modbus_client: ModbusClient = neuron.modbus_client

        self.short_name: str = short_name
        self.description: str = description
        self.modbus_info: MeterModbusInfo = modbus_info
        self.definition: HardwareDefinition = definition

    def __repr__(self) -> str:
        return (
            f"{self.description} (Unit {self.definition.unit} - {self.definition.manufacturer} {self.definition.model})"
        )

    @property
    def unique_name(self):
        return f"meter_{self.definition.unit}_{slugify(self.description)}"

    @property
    def topic(self) -> str:
        """Unique name for the MQTT topic."""
        topic: str = f"{self.config.device_info.name.lower()}/unit/{self.definition.unit}"
        topic += f"/{self.feature_name}/{slugify(self.description)}"

        return topic


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

        # self._definition: dict = neuron.hardware["definitions"][HardwareGroup.THIRD_PARTY][
        #     HardwareType.ELECTRICITY_METER
        # ]
        # self._unit: int = self._definition["unit"]

    def _parse_feature_meter(self, modbus_feature: dict):
        meter: MeterFeature = MeterFeature(
            neuron=self.neuron,
            short_name=modbus_feature["type"],
            description=modbus_feature["description"],
            modbus_info=MeterModbusInfo(
                start_reg=modbus_feature["start_reg"],
                count_reg=modbus_feature["count"],
            ),
            definition=self.definition,
        )

        self.neuron.features.register(meter)

    def _parse_feature(self, modbus_feature: dict):
        feature_type: str = modbus_feature["type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(modbus_feature)

    def parse_features(self):
        for modbus_feature in self.definition.modbus_features:
            self._parse_feature(modbus_feature)
