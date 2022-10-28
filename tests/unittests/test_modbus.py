import pytest

from superbox_utils.core.exception import UnexpectedException
from unipi_control.modbus.cache import ModbusCacheData
from unipi_control.neuron import Neuron
from unittests.conftest import ConfigLoader
from unittests.conftest_data import CONFIG_CONTENT
from unittests.conftest_data import HARDWARE_DATA_CONTENT
from unittests.conftest_data import THIRD_PARTY_HARDWARE_DATA_CONTENT


class TestUnhappyPathModbus:
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, THIRD_PARTY_HARDWARE_DATA_CONTENT)], indirect=True
    )
    def test_modbus_exceptions(self, _config_loader: ConfigLoader, _neuron: Neuron):
        assert isinstance(_neuron.modbus_cache_data, ModbusCacheData)

        with pytest.raises(UnexpectedException) as error:
            _neuron.modbus_cache_data.get_register(index=3, address=0, unit=1)

        assert str(error.value) == "Modbus error on address 2 (unit: 1)"
