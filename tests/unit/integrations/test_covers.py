# pylint: disable=protected-access
from dataclasses import dataclass
from dataclasses import field
from typing import NoReturn
from typing import Optional
from unittest.mock import MagicMock

import pytest
from pymodbus.pdu import ModbusResponse
from pytest_mock import MockerFixture

from tests.unit.conftest import ConfigLoader
from tests.unit.conftest import MockModbusClient
from tests.unit.conftest_data import CONFIG_CONTENT
from tests.unit.conftest_data import EXTENSION_HARDWARE_DATA_CONTENT
from tests.unit.conftest_data import HARDWARE_DATA_CONTENT
from unipi_control.integrations.covers import Cover
from unipi_control.integrations.covers import CoverMap
from unipi_control.integrations.covers import CoverState


@dataclass
class CoverOptions:
    device_class: str
    calibration_mode: bool = field(default_factory=bool)
    position: Optional[int] = field(default=None)
    current_position: Optional[int] = field(default=None)
    tilt: Optional[int] = field(default=None)
    current_tilt: Optional[int] = field(default=None)
    cover_state: Optional[str] = field(default=None)
    current_cover_state: Optional[str] = field(default=None)


@dataclass
class CoverExpected:
    calibration_started: Optional[bool] = field(default=None)
    calibration_mode: Optional[bool] = field(default=None)
    position: Optional[int] = field(default=None)
    tilt: Optional[int] = field(default=None)
    current_cover_state: Optional[str] = field(default=None)
    position_cover_state: Optional[str] = field(default=None)
    tilt_cover_state: Optional[str] = field(default=None)
    open_cover_state: Optional[str] = field(default=None)
    close_cover_state: Optional[str] = field(default=None)
    stop_cover_state: Optional[str] = field(default=None)
    position_changed: Optional[bool] = field(default=None)
    tilt_changed: Optional[bool] = field(default=None)


class TestCovers:
    @pytest.fixture(autouse=True)
    def pre(self, _modbus_client: MockModbusClient, mocker: MockerFixture) -> NoReturn:
        mock_response_is_error = MagicMock(spec=ModbusResponse)
        mock_response_is_error.isError.return_value = False

        _modbus_client.tcp.write_coil.return_value = mock_response_is_error

        mocker.patch("unipi_control.integrations.covers.CoverTimer", new_callable=MagicMock)


class TestHappyPathCovers(TestCovers):
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (
                CoverOptions(device_class="blind", calibration_mode=True),
                CoverExpected(calibration_started=True, calibration_mode=False),
            ),
            (
                CoverOptions(device_class="roller_shutter", calibration_mode=False),
                CoverExpected(calibration_started=False, calibration_mode=False),
            ),
        ],
    )
    async def test_calibrate(
        self,
        _config_loader: ConfigLoader,
        _covers: CoverMap,
        mocker: MockerFixture,
        options: CoverOptions,
        expected: CoverExpected,
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = options.calibration_mode

        mock_monotonic = mocker.patch("unipi_control.integrations.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.calibrate()

        assert cover._calibration.started is expected.calibration_started

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        await cover.stop_cover()

        assert cover._calibration.mode == expected.calibration_mode

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (
                CoverOptions(device_class="blind", position=0),
                CoverExpected(
                    position=100,
                    tilt=100,
                    current_cover_state="closed",
                    open_cover_state="opening",
                    stop_cover_state="open",
                    position_changed=True,
                ),
            ),
            (
                CoverOptions(device_class="blind", position=50),
                CoverExpected(
                    position=100,
                    tilt=100,
                    current_cover_state="stopped",
                    open_cover_state="opening",
                    stop_cover_state="open",
                    position_changed=True,
                ),
            ),
            (
                CoverOptions(device_class="roller_shutter", position=None),
                CoverExpected(
                    position=None,
                    tilt=None,
                    current_cover_state="stopped",
                    open_cover_state="opening",
                    stop_cover_state="stopped",
                    position_changed=False,
                ),
            ),
        ],
    )
    async def test_open_cover(
        self,
        _config_loader: ConfigLoader,
        _covers: CoverMap,
        mocker: MockerFixture,
        options: CoverOptions,
        expected: CoverExpected,
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = False
        cover._current.position = options.position
        cover.status.position = options.position
        cover._update_state()

        assert cover.status.state == expected.current_cover_state

        mock_monotonic = mocker.patch("unipi_control.integrations.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0

        if (cover_run_time := await cover.open_cover()) is not None:
            mock_monotonic.return_value = cover_run_time

        assert cover.status.state == expected.open_cover_state

        await cover.stop_cover()
        cover.read_position()

        assert cover.status.position == expected.position
        assert cover.status.tilt == expected.tilt
        assert cover.status.state == expected.stop_cover_state
        assert cover.state_changed is True
        assert cover.position_changed == expected.position_changed

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (
                CoverOptions(device_class="blind", position=100),
                CoverExpected(
                    position=0,
                    tilt=0,
                    current_cover_state="open",
                    close_cover_state="closing",
                    stop_cover_state="closed",
                    position_changed=True,
                ),
            ),
            (
                CoverOptions(device_class="blind", position=50),
                CoverExpected(
                    position=0,
                    tilt=0,
                    current_cover_state="stopped",
                    close_cover_state="closing",
                    stop_cover_state="closed",
                    position_changed=True,
                ),
            ),
            (
                CoverOptions(device_class="roller_shutter", position=None),
                CoverExpected(
                    position=None,
                    tilt=None,
                    current_cover_state="stopped",
                    close_cover_state="closing",
                    stop_cover_state="stopped",
                    position_changed=False,
                ),
            ),
        ],
    )
    async def test_close_cover(
        self,
        _config_loader: ConfigLoader,
        _covers: CoverMap,
        mocker: MockerFixture,
        options: CoverOptions,
        expected: CoverExpected,
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = False
        cover._current.position = options.position
        cover.status.position = options.position
        cover._update_state()

        assert cover.status.state == expected.current_cover_state

        mock_monotonic = mocker.patch("unipi_control.integrations.covers.time.monotonic", new_callable=MagicMock)

        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.close_cover()

        assert cover.status.state == expected.close_cover_state

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        await cover.stop_cover()
        cover.read_position()

        assert cover.status.position == expected.position
        assert cover.status.tilt == expected.tilt
        assert cover.status.state == expected.stop_cover_state
        assert cover.state_changed is True
        assert cover.position_changed == expected.position_changed

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (CoverOptions(device_class="blind", position=0, cover_state=CoverState.CLOSING), "closed"),
            (CoverOptions(device_class="blind", position=50, cover_state=CoverState.OPENING), "stopped"),
            (CoverOptions(device_class="blind", position=100, cover_state=CoverState.OPENING), "open"),
        ],
    )
    async def test_stop_cover(
        self,
        _config_loader: ConfigLoader,
        _covers: CoverMap,
        mocker: MockerFixture,
        options: CoverOptions,
        expected: str,
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = False
        cover.status.position = options.position
        cover.status.state = options.cover_state

        mock_monotonic = mocker.patch("unipi_control.integrations.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0

        await cover.stop_cover()
        assert cover.status.state == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (
                CoverOptions(device_class="blind", position=50, current_tilt=50, tilt=25),
                CoverExpected(
                    tilt=25,
                    current_cover_state="stopped",
                    tilt_cover_state="closing",
                    stop_cover_state="stopped",
                    tilt_changed=True,
                ),
            ),
            (
                CoverOptions(device_class="blind", position=50, current_tilt=50, tilt=75),
                CoverExpected(
                    tilt=75,
                    current_cover_state="stopped",
                    tilt_cover_state="opening",
                    stop_cover_state="stopped",
                    tilt_changed=True,
                ),
            ),
            (
                CoverOptions(device_class="roller_shutter", position=None, current_tilt=None, tilt=25),
                CoverExpected(
                    tilt=None,
                    current_cover_state="stopped",
                    tilt_cover_state="stopped",
                    stop_cover_state="stopped",
                    tilt_changed=False,
                ),
            ),
        ],
    )
    async def test_set_tilt(
        self,
        _config_loader: ConfigLoader,
        _covers: CoverMap,
        mocker: MockerFixture,
        options: CoverOptions,
        expected: CoverExpected,
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = False
        cover._current.tilt = options.current_tilt
        cover.status.tilt = options.current_tilt
        cover._current.position = options.position
        cover.status.position = options.position
        cover._update_state()

        assert cover.status.state == expected.current_cover_state

        mock_monotonic = mocker.patch("unipi_control.integrations.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0

        assert isinstance(options.tilt, int)

        cover_run_time: Optional[float] = await cover.set_tilt(options.tilt)

        assert cover.status.state == expected.tilt_cover_state

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        await cover.stop_cover()
        cover.read_position()

        assert cover.status.tilt == expected.tilt
        assert cover.status.state == expected.stop_cover_state
        assert cover.state_changed is True
        assert cover.tilt_changed == expected.tilt_changed

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (
                CoverOptions(device_class="blind", current_position=50, tilt=50, position=25),
                CoverExpected(
                    position=25,
                    current_cover_state="stopped",
                    position_cover_state="closing",
                    stop_cover_state="stopped",
                    position_changed=True,
                ),
            ),
            (
                CoverOptions(device_class="blind", current_position=50, tilt=50, position=75),
                CoverExpected(
                    position=75,
                    current_cover_state="stopped",
                    position_cover_state="opening",
                    stop_cover_state="stopped",
                    position_changed=True,
                ),
            ),
            (
                CoverOptions(device_class="roller_shutter", current_position=None, tilt=None, position=25),
                CoverExpected(
                    position=None,
                    current_cover_state="stopped",
                    position_cover_state="stopped",
                    stop_cover_state="stopped",
                    position_changed=False,
                ),
            ),
        ],
    )
    async def test_set_position(
        self,
        _config_loader: ConfigLoader,
        _covers: CoverMap,
        mocker: MockerFixture,
        options: CoverOptions,
        expected: CoverExpected,
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = False
        cover._current.tilt = options.tilt
        cover.tilt = options.tilt
        cover._current.position = options.current_position
        cover.status.position = options.current_position
        cover._update_state()

        assert cover.status.state == expected.current_cover_state

        mock_monotonic = mocker.patch("unipi_control.integrations.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0

        assert isinstance(options.position, int)

        cover_run_time: Optional[float] = await cover.set_position(options.position)

        assert cover.status.state == expected.position_cover_state

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time

        await cover.stop_cover()
        cover.read_position()

        assert cover.status.position == expected.position
        assert cover.status.state == expected.stop_cover_state
        assert cover.state_changed is True
        assert cover.position_changed == expected.position_changed

    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (CoverOptions(device_class="blind"), "MOCKED_FRIENDLY_NAME - BLIND"),
            (CoverOptions(device_class="roller_shutter"), "MOCKED_FRIENDLY_NAME - ROLLER SHUTTER"),
        ],
    )
    def test_friendly_name(
        self, _config_loader: ConfigLoader, _covers: CoverMap, options: CoverOptions, expected: str
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))

        assert str(cover) == expected

    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (CoverOptions(device_class="blind", current_cover_state="stopped", cover_state="close"), True),
            (CoverOptions(device_class="blind", current_cover_state="closed", cover_state="closed"), False),
        ],
    )
    def test_state_changed(
        self, _config_loader: ConfigLoader, _covers: CoverMap, options: CoverOptions, expected: bool
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._current.state = options.current_cover_state
        cover.status.state = options.cover_state

        assert cover.state_changed == expected

    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (CoverOptions(device_class="blind", current_position=0, position=50), True),
            (CoverOptions(device_class="blind", current_position=50, position=50), False),
            (CoverOptions(device_class="roller_shutter", current_position=None, position=None), False),
        ],
    )
    def test_position_changed(
        self, _config_loader: ConfigLoader, _covers: CoverMap, options: CoverOptions, expected: bool
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._current.position = options.current_position
        cover.status.position = options.position

        assert cover.position_changed == expected


class TestUnhappyPathCovers(TestCovers):
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize("options, expected", [(CoverOptions(device_class="blind"), 105)])
    async def test_open_with_invalid_position(
        self,
        _config_loader: ConfigLoader,
        _covers: CoverMap,
        options: CoverOptions,
        expected: int,
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = False
        cover._current.position = expected
        cover.status.position = expected

        cover_run_time: Optional[float] = await cover.open_cover()

        assert cover_run_time is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize("options, expected", [(CoverOptions(device_class="blind"), 50)])
    async def test_open_with_calibration_mode(
        self, _config_loader: ConfigLoader, _covers: CoverMap, options: CoverOptions, expected: int
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = True
        cover._current.position = expected
        cover.status.position = expected

        cover_run_time: Optional[float] = await cover.open_cover()

        assert cover_run_time is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize("options, expected", [(CoverOptions(device_class="blind"), 50)])
    async def test_close_with_calibration_mode(
        self, _config_loader: ConfigLoader, _covers: CoverMap, options: CoverOptions, expected: int
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = True
        cover._current.position = expected
        cover.status.position = expected

        cover_run_time: Optional[float] = await cover.close_cover()

        assert cover_run_time is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "_config_loader", [(CONFIG_CONTENT, HARDWARE_DATA_CONTENT, EXTENSION_HARDWARE_DATA_CONTENT)], indirect=True
    )
    @pytest.mark.parametrize(
        "options, expected",
        [
            (
                CoverOptions(device_class="blind", calibration_mode=True),
                CoverExpected(calibration_started=True, calibration_mode=True),
            ),
            (
                CoverOptions(device_class="roller_shutter", calibration_mode=False),
                CoverExpected(calibration_started=False, calibration_mode=False),
            ),
        ],
    )
    async def test_calibrate_stopped(
        self,
        _config_loader: ConfigLoader,
        _covers: CoverMap,
        mocker: MockerFixture,
        options: CoverOptions,
        expected: CoverExpected,
    ) -> NoReturn:
        cover: Cover = next(_covers.by_device_classes([options.device_class]))
        cover._calibration.mode = options.calibration_mode

        mock_monotonic = mocker.patch("unipi_control.integrations.covers.time.monotonic", new_callable=MagicMock)
        mock_monotonic.return_value = 0
        cover_run_time: Optional[float] = await cover.calibrate()

        assert cover._calibration.started is expected.calibration_started

        if cover_run_time is not None:
            mock_monotonic.return_value = cover_run_time / 2

        await cover.stop_cover()

        assert cover._calibration.mode == expected.calibration_mode
