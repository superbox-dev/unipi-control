from typing import NamedTuple

from superbox_utils.text.text import slugify
from unipi_control.config import HardwareDefinition
from unipi_control.features import BaseFeature


class MeterModbusInfo(NamedTuple):
    start_reg: int
    count_reg: int


class Meter(BaseFeature):
    def __init__(
        self,
        neuron,
        definition: HardwareDefinition,
        **kwargs,
    ):
        super().__init__(neuron, definition, kwargs["feature_type"])

        self._friendly_name: str = kwargs["friendly_name"]

    @property
    def unique_name(self) -> str:
        return f"{slugify(self.friendly_name)}_{self.definition.unit}"

    @property
    def friendly_name(self) -> str:
        return f"{self._friendly_name} {self.definition.unit}"

    @property
    def topic(self) -> str:
        """Unique name for the MQTT topic."""
        return f"{super().topic}/{self.unique_name}"

    @property
    def value(self) -> int:
        return 0


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

    def _parse_feature_meter(self, modbus_feature: dict):
        meter: Meter = Meter(
            neuron=self.neuron,
            definition=self.definition,
            **modbus_feature,
        )

        self.neuron.features.register(meter)

    def _parse_feature(self, modbus_feature: dict):
        feature_type: str = modbus_feature["feature_type"].lower()

        if func := getattr(self, f"_parse_feature_{feature_type}", None):
            func(modbus_feature)

    def parse_features(self):
        for modbus_feature in self.definition.modbus_features:
            self._parse_feature(modbus_feature)
