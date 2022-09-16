from typing import Optional
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from conftest import ConfigLoader
from conftest_data import CONFIG_CONTENT
from conftest_data import HARDWARE_DATA_CONTENT
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
    async def covers(self, config_loader: ConfigLoader, neuron):
        config: Config = config_loader.get_config()
        yield CoverMap(config=config, features=neuron.features)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position, stop_time, expected_position, expected_cover_run_time, expected_cover_tilt, "
        "expected_current_cover_state, expected_open_cover_state, expected_stop_cover_state, expected_position_changed",
        [
            ("blind", 0, 37.275, 100, 37.275, 100, "closed", "opening", "open", True),
            ("blind", 50, 19.525, 100, 19.525, 100, "stopped", "opening", "open", True),
            ("blind", 0, 17.75, 50, 37.275, 100, "closed", "opening", "stopped", True),
            ("roller_shutter", None, None, None, None, None, "stopped", "opening", "stopped", False),
        ],
    )
    async def test_open(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        cover_position: Optional[int],
        stop_time: Optional[float],
        expected_position: Optional[int],
        expected_cover_run_time: Optional[float],
        expected_cover_tilt: Optional[int],
        expected_current_cover_state: str,
        expected_open_cover_state: str,
        expected_stop_cover_state: str,
        expected_position_changed: bool,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = False
        cover._current_position = cover_position
        cover.position = cover_position
        cover._update_state()

        assert expected_current_cover_state == cover.state

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.open()

        if stop_time is not None:
            mock_monotonic.return_value = stop_time

        assert expected_open_cover_state == cover.state

        await cover.stop()
        cover.read_position()

        assert expected_position == cover.position
        assert expected_cover_tilt == cover.tilt
        assert expected_cover_run_time == cover_run_time
        assert expected_stop_cover_state == cover.state
        assert True is cover.state_changed
        assert expected_position_changed == cover.position_changed

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position, stop_time, expected_position, expected_cover_run_time, expected_cover_tilt, "
        "expected_current_cover_state, expected_close_cover_state, expected_stop_cover_state, "
        "expected_position_changed",
        [
            ("blind", 100, 37.275, 0, 37.275, 0, "open", "closing", "closed", True),
            ("blind", 50, 19.525, 0, 19.525, 0, "stopped", "closing", "closed", True),
            ("blind", 100, 17.75, 50, 37.275, 0, "open", "closing", "stopped", True),
            ("roller_shutter", None, None, None, None, None, "stopped", "closing", "stopped", False),
        ],
    )
    async def test_close(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        cover_position: Optional[int],
        stop_time: Optional[float],
        expected_position: Optional[int],
        expected_cover_run_time: Optional[float],
        expected_cover_tilt: Optional[int],
        expected_current_cover_state: str,
        expected_close_cover_state: str,
        expected_stop_cover_state: str,
        expected_position_changed: bool,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = False
        cover._current_position = cover_position
        cover.position = cover_position
        cover._update_state()

        assert expected_current_cover_state == cover.state

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)

        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.close()

        assert expected_close_cover_state == cover.state

        if stop_time is not None:
            mock_monotonic.return_value = stop_time

        await cover.stop()
        cover.read_position()

        assert expected_position == cover.position
        assert expected_cover_tilt == cover.tilt
        assert expected_cover_run_time == cover_run_time
        assert expected_stop_cover_state == cover.state
        assert True is cover.state_changed
        assert expected_position_changed == cover.position_changed

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position, cover_state, expected_state",
        [
            ("blind", 0, CoverState.CLOSING, "closed"),
            ("blind", 50, CoverState.OPENING, "stopped"),
            ("blind", 100, CoverState.OPENING, "open"),
        ],
    )
    async def test_stop(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        cover_position: int,
        cover_state: str,
        expected_state: str,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = False
        cover.position = cover_position
        cover.state = cover_state

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0

        await cover.stop()
        assert expected_state == cover.state

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position, current_cover_tilt, cover_tilt, stop_time, expected_cover_tilt, "
        "expected_cover_run_time, expected_current_cover_state, expected_tilt_cover_state, expected_stop_cover_state, "
        "expected_tilt_changed",
        [
            ("blind", 50, 50, 25, 0.375, 25, 0.375, "stopped", "closing", "stopped", True),
            ("blind", 50, 50, 75, 0.375, 75, 0.375, "stopped", "opening", "stopped", True),
            ("roller_shutter", None, None, 25, None, None, None, "stopped", "stopped", "stopped", False),
        ],
    )
    async def test_set_tilt(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        current_cover_tilt: Optional[int],
        cover_position: Optional[int],
        cover_tilt: int,
        stop_time: Optional[float],
        expected_cover_tilt: Optional[int],
        expected_cover_run_time: Optional[float],
        expected_current_cover_state: str,
        expected_tilt_cover_state: str,
        expected_stop_cover_state: str,
        expected_tilt_changed: bool,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = False
        cover._current_tilt = current_cover_tilt
        cover.tilt = current_cover_tilt
        cover._current_position = cover_position
        cover.position = cover_position
        cover._update_state()

        assert expected_current_cover_state == cover.state

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.set_tilt(cover_tilt)

        assert expected_tilt_cover_state == cover.state

        if stop_time is not None:
            mock_monotonic.return_value = stop_time

        await cover.stop()
        cover.read_position()

        assert expected_cover_tilt == cover.tilt
        assert expected_cover_run_time == cover_run_time
        assert expected_stop_cover_state == cover.state
        assert True is cover.state_changed
        assert expected_tilt_changed == cover.tilt_changed

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, current_cover_position, cover_tilt, cover_position, stop_time, expected_cover_position, "
        "expected_cover_run_time, expected_current_cover_state, expected_position_cover_state, expected_stop_cover_state, "
        "expected_position_changed",
        [
            ("blind", 50, 50, 25, 8.875, 25, 8.875, "stopped", "closing", "stopped", True),
            ("blind", 50, 50, 75, 8.875, 75, 8.875, "stopped", "opening", "stopped", True),
            ("roller_shutter", None, None, 25, None, None, None, "stopped", "stopped", "stopped", False),
        ],
    )
    async def test_set_position(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        current_cover_position: Optional[int],
        cover_tilt: Optional[int],
        cover_position: int,
        stop_time: Optional[float],
        expected_cover_position: Optional[int],
        expected_cover_run_time: Optional[float],
        expected_current_cover_state: str,
        expected_position_cover_state: str,
        expected_stop_cover_state: str,
        expected_position_changed: bool,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = False
        cover._current_tilt = cover_tilt
        cover.tilt = cover_tilt
        cover._current_position = current_cover_position
        cover.position = current_cover_position
        cover._update_state()

        assert expected_current_cover_state == cover.state

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.set_position(cover_position)

        assert expected_position_cover_state == cover.state

        if stop_time is not None:
            mock_monotonic.return_value = stop_time

        await cover.stop()
        cover.read_position()

        assert expected_cover_position == cover.position
        assert expected_cover_run_time == cover_run_time
        assert expected_stop_cover_state == cover.state
        assert True is cover.state_changed
        assert expected_position_changed == cover.position_changed

    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, expected_friendly_name",
        [
            ("blind", "MOCKED_FRIENDLY_NAME - BLIND"),
            ("roller_shutter", "MOCKED_FRIENDLY_NAME - ROLLER SHUTTER"),
        ],
    )
    def test_friendly_name(
        self, config_loader: ConfigLoader, covers: CoverMap, cover_type: str, expected_friendly_name: str
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))

        assert expected_friendly_name == str(cover)

    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, current_cover_state, cover_state, expected_state_changed",
        [
            ("blind", "stopped", "close", True),
            ("blind", "closed", "closed", False),
        ],
    )
    def test_state_changed(
        self,
        config_loader: ConfigLoader,
        covers: CoverMap,
        cover_type: str,
        current_cover_state: str,
        cover_state: str,
        expected_state_changed: bool,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover._current_state = current_cover_state
        cover.state = cover_state

        assert expected_state_changed == cover.state_changed

    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, current_position, position, expected_position_changed",
        [
            ("blind", 0, 50, True),
            ("blind", 50, 50, False),
            ("roller_shutter", None, None, False),
        ],
    )
    def test_position_changed(
        self,
        config_loader: ConfigLoader,
        covers: CoverMap,
        cover_type: str,
        current_position: Optional[int],
        position: Optional[int],
        expected_position_changed: bool,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover._current_position = current_position
        cover.position = position

        assert expected_position_changed == cover.position_changed
