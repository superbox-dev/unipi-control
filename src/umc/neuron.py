from api.settings import logger
from config import HardwareDefinition
from devices import devices


class FeatureMixin:
    def __init__(self, circuit: str, *args, **kwargs):
        self.circuit = circuit
        self._circuit_name = circuit.replace("_", ".")


class Relay(FeatureMixin):
    name = "Relay"
    dev = "relay"
    dev_type = "physical"


class DigitalOutput(FeatureMixin):
    name = "Digital Output"
    dev = "relay"
    dev_type = "digital"


class DigitalInput(FeatureMixin):
    name = "Digital Input"
    dev = "input"
    dev_type = "digital"


class AnlogOutput(FeatureMixin):
    name = "Analog Output"
    dev = "output"
    dev_type = "analog"


class AnlogInput(FeatureMixin):
    name = "Analog Input"
    dev = "input"
    dev_type = "analog"


class Led(FeatureMixin):
    name = "LED"
    dev = "led"


class Watchdog(FeatureMixin):
    name = "Watchdog"
    dev = "wd"


class Register(FeatureMixin):
    name = "Register"
    dev = "register"


class Board:
    def __init__(self, major_group: int):
        hw = HardwareDefinition()

        self.major_group: int = major_group
        self._modbus_features: list = hw["neuron_definition"]["modbus_features"]

    def _parse_feature_ro(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                _device = Relay(
                    circuit="%s_%s_%02d" % (feature_type.lower(), major_group, index + 1),
                    coil=modbus_feature['val_coil'] + index,
                    **modbus_feature,
                )

                devices.register(feature_type, _device)

    def _parse_feature_di(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                _device = DigitalInput(
                    circuit="%s_%02d" % (major_group, index + 1),
                    reg=modbus_feature['val_reg'] + index,
                    **modbus_feature,
                )

                devices.register(feature_type, _device)

    def _parse_feature_do(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                _device = DigitalOutput(
                    circuit="%s_%02d" % (major_group, index + 1),
                    coil=modbus_feature['val_coil'] + index,
                    **modbus_feature,
                )

                devices.register(feature_type, _device)

    def _parse_feature_ao(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                _device = AnlogOutput(
                    circuit="%s_%02d" % (major_group, index + 1),
                    reg=modbus_feature['val_reg'] + index,
                    **modbus_feature,
                )

                devices.register(feature_type, _device)

    def _parse_feature_ai(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                _device = AnlogInput(
                    circuit="%s_%02d" % (major_group, index + 1),
                    reg=modbus_feature['val_reg'] + index,
                    **modbus_feature,
                )

                devices.register(feature_type, _device)

    def _parse_feature_register(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]
        reg_type: str = modbus_feature.get("reg_type")

        if major_group == self.major_group:
            for index in range(0, max_count):
                if reg_type == "input":
                    name = "%s_%d_inp"
                else:
                    name = "%s_%d"

                _device = Register(
                    circuit=name % (major_group, index + 1),
                    reg=modbus_feature['start_reg'] + index,
                    **modbus_feature,
                )

                devices.register(feature_type, _device)

    def _parse_feature_led(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                _device = Led(
                    circuit="%s_%02d" % (major_group, index + 1),
                    coil=modbus_feature['val_coil'] + index,
                    **modbus_feature,
                )

                devices.register(feature_type, _device)

    def _parse_feature_wd(self, max_count: int, modbus_feature: list) -> None:
        major_group: int = modbus_feature["major_group"]
        feature_type: str = modbus_feature["type"]

        if major_group == self.major_group:
            for index in range(0, max_count):
                _device = Watchdog(
                    circuit="%s_%02d" % (major_group, index + 1),
                    reg=modbus_feature['val_reg'] + index,
                    **modbus_feature,
                )

                devices.register(feature_type, _device)

    def _parse_feature(self, modbus_feature: dict) -> None:
        max_count: int = modbus_feature["count"]
        feature_type: str = modbus_feature["type"].lower()
        func = getattr(self, f"_parse_feature_{feature_type}", None)

        if func:
            func(max_count, modbus_feature)

    def parse_definition(self) -> None:
        for modbus_feature in self._modbus_features:
            print(modbus_feature)
            self._parse_feature(modbus_feature)


class Neuron:
    def __init__(self, modbus_client):
        self._modbus_client = modbus_client
        self.boards: list = []

    async def read_boards(self) -> None:
        logger.info("Reading SPI boards")

        for index in (1, 2, 3):
            request_fw = await self._modbus_client.read_input_registers(1000, 1, unit=index)

            if request_fw.isError():
                logger.info(f"No board on SPI {index}")
            else:
                Board(major_group=index).parse_definition()
