import pytest

from conftest import ConfigLoader
from conftest_data import CONFIG_CONTENT


class TestHappyPathConfig:
    @pytest.mark.parametrize("config_loader", [CONFIG_CONTENT], indirect=True)
    def test_open(self, config_loader: ConfigLoader):
        pass
