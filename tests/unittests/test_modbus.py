import pytest

from conftest import ConfigLoader
from conftest_data import CONFIG_CONTENT
from conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.modbus import ModbusCacheMap
from unipi_control.modbus import ModbusRegisterException
from unipi_control.neuron import Neuron


class TestUnhappyPathModbus:
    @pytest.mark.parametrize(
        "config_loader",
        [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)],
        indirect=True,
    )
    def test_modbus_exceptions(self, config_loader: ConfigLoader, neuron: Neuron):
        assert isinstance(neuron.modbus_cache_map, ModbusCacheMap)

        with pytest.raises(ModbusRegisterException) as error:
            neuron.modbus_cache_map.get_register(address=22, index=0)

        assert "Modbus error on address 21 (unit: 0)" == str(error.value)
