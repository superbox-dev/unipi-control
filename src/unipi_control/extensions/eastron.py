from unipi_control.config import HardwareDefinition
from unipi_control.features import Meter


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
