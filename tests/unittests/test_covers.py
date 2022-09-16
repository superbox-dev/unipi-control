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


class TestCovers:
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


class TestHappyPathCovers(TestCovers):
    @pytest.fixture(autouse=True)
    def pre(self, modbus_client, mocker: MockerFixture):
        mock_response_is_error = MagicMock()
        mock_response_is_error.isError.return_value = False

        modbus_client.write_coil.return_value = mock_response_is_error

        mocker.patch("unipi_control.covers.CoverTimer", new_callable=MagicMock)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, calibrate_mode, expected_calibration_started, expected_calibration_mode",
        [
            ("blind", True, True, False),
            ("roller_shutter", False, False, False),
        ],
    )
    async def test_calibrate(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        calibrate_mode: bool,
        expected_calibration_started: bool,
        expected_calibration_mode: bool,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = calibrate_mode

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.calibrate()

        assert expected_calibration_started is cover._calibration_started

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        await cover.stop()

        assert expected_calibration_mode == cover.calibrate_mode

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position, expected_position, expected_cover_tilt, "
        "expected_current_cover_state, expected_open_cover_state, expected_stop_cover_state, expected_position_changed",
        [
            ("blind", 0, 100, 100, "closed", "opening", "open", True),
            ("blind", 50, 100, 100, "stopped", "opening", "open", True),
            ("roller_shutter", None, None, None, "stopped", "opening", "stopped", False),
        ],
    )
    async def test_open(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        cover_position: Optional[int],
        expected_position: Optional[int],
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

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        assert expected_open_cover_state == cover.state

        await cover.stop()
        cover.read_position()

        assert expected_position == cover.position
        assert expected_cover_tilt == cover.tilt
        assert expected_stop_cover_state == cover.state
        assert True is cover.state_changed
        assert expected_position_changed == cover.position_changed

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position, expected_position, expected_cover_tilt, "
        "expected_current_cover_state, expected_close_cover_state, expected_stop_cover_state, "
        "expected_position_changed",
        [
            ("blind", 100, 0, 0, "open", "closing", "closed", True),
            ("blind", 50, 0, 0, "stopped", "closing", "closed", True),
            ("roller_shutter", None, None, None, "stopped", "closing", "stopped", False),
        ],
    )
    async def test_close(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        cover_position: Optional[int],
        expected_position: Optional[int],
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

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        await cover.stop()
        cover.read_position()

        assert expected_position == cover.position
        assert expected_cover_tilt == cover.tilt
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
        "cover_type, cover_position, current_cover_tilt, cover_tilt, expected_cover_tilt, "
        "expected_current_cover_state, expected_tilt_cover_state, expected_stop_cover_state, "
        "expected_tilt_changed",
        [
            ("blind", 50, 50, 25, 25, "stopped", "closing", "stopped", True),
            ("blind", 50, 50, 75, 75, "stopped", "opening", "stopped", True),
            ("roller_shutter", None, None, 25, None, "stopped", "stopped", "stopped", False),
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
        expected_cover_tilt: Optional[int],
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

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        await cover.stop()
        cover.read_position()

        assert expected_cover_tilt == cover.tilt
        assert expected_stop_cover_state == cover.state
        assert True is cover.state_changed
        assert expected_tilt_changed == cover.tilt_changed

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, current_cover_position, cover_tilt, cover_position, expected_cover_position, "
        "expected_current_cover_state, expected_position_cover_state, expected_stop_cover_state, "
        "expected_position_changed",
        [
            ("blind", 50, 50, 25, 25, "stopped", "closing", "stopped", True),
            ("blind", 50, 50, 75, 75, "stopped", "opening", "stopped", True),
            ("roller_shutter", None, None, 25, None, "stopped", "stopped", "stopped", False),
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
        expected_cover_position: Optional[int],
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

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        await cover.stop()
        cover.read_position()

        assert expected_cover_position == cover.position
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


class TestUnhappyPathCovers(TestCovers):
    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position",
        [
            ("blind", 105),
        ],
    )
    async def test_open_with_invalid_position(
        self,
        config_loader: ConfigLoader,
        covers: CoverMap,
        cover_type: str,
        cover_position: int,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = False
        cover._current_position = cover_position
        cover.position = cover_position

        cover_run_time: Optional[float] = await cover.open()

        assert None is cover_run_time

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position",
        [
            ("blind", 50),
        ],
    )
    async def test_open_with_calibrate_mode(
        self,
        config_loader: ConfigLoader,
        covers: CoverMap,
        cover_type: str,
        cover_position: Optional[int],
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = True
        cover._current_position = cover_position
        cover.position = cover_position

        cover_run_time: Optional[float] = await cover.open()

        assert None is cover_run_time

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, cover_position",
        [
            ("blind", 50),
        ],
    )
    async def test_close_with_calibrate_mode(
        self,
        config_loader: ConfigLoader,
        covers: CoverMap,
        cover_type: str,
        cover_position: Optional[int],
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = True
        cover._current_position = cover_position
        cover.position = cover_position

        cover_run_time: Optional[float] = await cover.close()

        assert None is cover_run_time

    @pytest.mark.asyncio
    @pytest.mark.parametrize("config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT)], indirect=True)
    @pytest.mark.parametrize(
        "cover_type, calibrate_mode, expected_calibration_started, expected_calibration_mode",
        [
            ("blind", True, True, True),
            ("roller_shutter", False, False, False),
        ],
    )
    async def test_calibrate_stopped(
        self,
        config_loader: ConfigLoader,
        mocker: MockerFixture,
        covers: CoverMap,
        cover_type: str,
        calibrate_mode: bool,
        expected_calibration_started: bool,
        expected_calibration_mode: bool,
    ):
        cover: Cover = next(covers.by_cover_type([cover_type]))
        cover.calibrate_mode = calibrate_mode

        mock_monotonic = mocker.patch("unipi_control.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.calibrate()

        assert expected_calibration_started is cover._calibration_started

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time / 2

        await cover.stop()

        assert expected_calibration_mode == cover.calibrate_mode
