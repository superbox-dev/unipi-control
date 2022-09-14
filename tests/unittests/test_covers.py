from typing import Optional
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from conftest import ConfigLoader
from conftest_data import CONFIG_CONTENT
from conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.config import COVER_TYPES
from unipi_control.config import Config
from unipi_control.covers import Cover
from unipi_control.covers import CoverMap
from unipi_control.covers import CoverState
from unipi_control.neuron import Neuron


class TestHappyPathCovers:
    @pytest.fixture(autouse=True)
    def pre(self, modbus_client, mocker: MockerFixture):
        mock_response_is_error = MagicMock()
        mock_response_is_error.isError.return_value = False

        modbus_client.write_coil.return_value = mock_response_is_error

        mocker.patch("unipi_control.covers.CoverTimer", new_callable=MagicMock)

    @pytest.fixture(autouse=True)
    def post(self, config_loader: ConfigLoader):
        yield
        config_loader.cleanup()

    @pytest_asyncio.fixture
    async def neuron(self, config_loader: ConfigLoader, modbus_client):
        config: Config = config_loader.get_config()

        neuron: Neuron = Neuron(config=config, modbus_client=modbus_client)
        await neuron.read_boards()

        yield neuron

    @pytest_asyncio.fixture
    async def cover(self, config_loader: ConfigLoader, neuron):
        config: Config = config_loader.get_config()

        covers: CoverMap = CoverMap(config=config, features=neuron.features)
        cover: Cover = next(covers.by_cover_type(COVER_TYPES))  # TODO: test multiple covers

        yield cover

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_position,expected_cover_run_time, expected_state",
        [(0, 37.275, "opening"), (50, 19.525, "opening"), (100, None, "open")],
    )
    async def test_open(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        cover,
        cover_position: int,
        expected_cover_run_time: Optional[float],
        expected_state: str,
    ):
        cover.calibrate_mode = False
        cover.position = cover_position
        cover.state = CoverState.OPEN  # Workaround: fix with a mocked temp file in _read_position()

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0

        cover_run_time: Optional[float] = await cover.open()

        assert expected_cover_run_time == cover_run_time
        assert expected_state == cover.state

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_position,expected_cover_run_time, expected_state",
        [(0, None, "closed"), (50, 19.525, "closing"), (100, 37.275, "closing")],
    )
    async def test_close(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        cover,
        cover_position: int,
        expected_cover_run_time: Optional[float],
        expected_state: str,
    ):
        cover.calibrate_mode = False
        cover.position = cover_position

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0

        cover_run_time: Optional[float] = await cover.close()

        assert expected_cover_run_time == cover_run_time
        assert expected_state == cover.state

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_position,cover_state,expected_state",
        [(0, CoverState.CLOSING, "closed"), (50, CoverState.OPENING, "stopped"), (100, CoverState.OPENING, "open")],
    )
    async def test_stop(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        cover,
        cover_position: int,
        cover_state: str,
        expected_state: str,
    ):
        cover.calibrate_mode = False
        cover.position = cover_position
        cover.state = cover_state

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0

        await cover.stop()
        assert expected_state == cover.state
