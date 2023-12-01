from pathlib import Path
from typing import Any
from typing import Dict
from typing import Iterator
from typing import Mapping
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import TypedDict

from unipi_control.config import Config
from unipi_control.config import LogPrefix
from unipi_control.config import ModbusUnitConfig
from unipi_control.config import UNIPI_LOGGER
from unipi_control.hardware.constants import HardwareType
from unipi_control.hardware.info import HardwareInfo
from unipi_control.helpers.exceptions import ConfigError
from unipi_control.helpers.exceptions import YamlError
from unipi_control.helpers.yaml import yaml_loader_safe


class ModbusRegisterBlock(TypedDict):
    start_reg: int
    count: int
    unit: Optional[int]


class ModbusFeature(TypedDict):
    feature_type: str
    major_group: int
    count: int
    val_reg: int
    val_coil: Optional[int]


class EastronModbusFeature(ModbusFeature):
    friendly_name: str
    device_class: Optional[str]
    state_class: Optional[str]
    unit_of_measurement: Optional[str]


class HardwareDefinition(NamedTuple):
    unit: int
    hardware_type: str
    device_name: Optional[str]
    suggested_area: Optional[str]
    manufacturer: Optional[str]
    model: str
    modbus_register_blocks: List[ModbusRegisterBlock]
    modbus_features: List[ModbusFeature]


class HardwareMap(Mapping[str, HardwareDefinition]):
    def __init__(self, config: Config) -> None:
        self.config = config

        self.data: Dict[str, HardwareDefinition] = {}
        self.info: HardwareInfo = HardwareInfo(sys_bus_dir=config.sys_bus_dir)

        if self.info.model == "unknown":
            msg = "Hardware is not supported!"
            raise ConfigError(msg)

        self._read_plc_definition()
        self._read_extension_definitions()

    def __getitem__(self, key: str) -> HardwareDefinition:
        data: HardwareDefinition = self.data[key]
        return data

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def _read_plc_definition(self) -> None:
        definition_file: Path = Path(f"{self.config.hardware_dir}/neuron/{self.info.model}.yaml")

        if definition_file.is_file():
            try:
                yaml_content: Dict[str, Any] = yaml_loader_safe(definition_file)

                self.data[HardwareType.PLC] = HardwareDefinition(
                    unit=0,
                    hardware_type=HardwareType.PLC,
                    device_name=None,
                    suggested_area=None,
                    manufacturer=None,
                    model=f"{self.info.name} {self.info.model}",
                    modbus_register_blocks=yaml_content["modbus_register_blocks"],
                    modbus_features=yaml_content["modbus_features"],
                )
                UNIPI_LOGGER.debug("%s Definition loaded: %s", LogPrefix.CONFIG, definition_file)
            except KeyError as error:
                msg = f"{LogPrefix.CONFIG} Definition is invalid: {definition_file}\nKeyError: {error}"
                raise ConfigError(msg) from error
            except TypeError as error:
                msg = f"{LogPrefix.CONFIG} Definition is invalid: {definition_file}"
                raise ConfigError(msg) from error
            except YamlError as error:
                msg = f"{LogPrefix.CONFIG} Definition is invalid: {definition_file}\n{error}"
                raise ConfigError(msg) from error
        else:
            msg = "No valid YAML definition found for this device!"
            raise ConfigError(msg)

    def _read_extension_definitions(self) -> None:
        for definition_file in Path(f"{self.config.hardware_dir}/extensions").glob("*.yaml"):
            try:
                yaml_content: Dict[str, Any] = yaml_loader_safe(definition_file)

                units: Iterator[ModbusUnitConfig] = self.config.modbus_serial.get_units_by_identifier(
                    identifier=definition_file.stem
                )

                for unit in units:
                    self.data[f"{HardwareType.EXTENSION}_{unit.unit}"] = HardwareDefinition(
                        unit=unit.unit,
                        hardware_type=HardwareType.EXTENSION,
                        device_name=unit.device_name,
                        suggested_area=unit.suggested_area,
                        manufacturer=yaml_content["manufacturer"],
                        model=yaml_content["model"],
                        modbus_register_blocks=yaml_content["modbus_register_blocks"],
                        modbus_features=yaml_content["modbus_features"],
                    )

                UNIPI_LOGGER.debug("%s Definition loaded: %s", LogPrefix.CONFIG, definition_file)
            except KeyError as error:
                msg = f"{LogPrefix.CONFIG} Definition is invalid: {definition_file}\nKeyError: {error}"
                raise ConfigError(msg) from error
            except TypeError as error:
                msg = f"{LogPrefix.CONFIG} Definition is invalid: {definition_file}"
                raise ConfigError(msg) from error
            except YamlError as error:
                msg = f"{LogPrefix.CONFIG} Definition is invalid: {definition_file}\n{error}"
                raise ConfigError(msg) from error

    def get_definition_by_hardware_types(self, hardware_types: List[str]) -> Iterator[HardwareDefinition]:
        """Filter hardware definitions by hardware types.

        Parameters
        ----------
        hardware_types: list
            A list of hardware types to filter hardware definitions.

        Returns
        -------
        Iterator:
            Filtered hardware definitions.
        """
        return (definition for definition in self.data.values() if definition.hardware_type in hardware_types)
