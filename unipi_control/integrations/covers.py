import asyncio
import functools
import itertools
import time
from asyncio import Future
from asyncio import Task
from collections.abc import Iterator
from dataclasses import asdict
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Final
from typing import List
from typing import Mapping
from typing import NamedTuple
from typing import Optional
from typing import Union

from pymodbus.pdu import ModbusResponse

from unipi_control.config import Config
from unipi_control.features.map import FeatureMap
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Relay
from unipi_control.helpers.text import slugify

ASYNCIO_SLEEP_DELAY_FIX: Final[float] = 0.04


def run_in_executor(_func: Callable[..., Any]) -> Callable[..., Any]:
    """Run blocking code async."""

    @functools.wraps(_func)
    def wrapped(*args, **kwargs) -> Future[Any]:  # type: ignore[no-untyped-def]
        loop = asyncio.get_running_loop()
        func = functools.partial(_func, *args, **kwargs)
        return loop.run_in_executor(executor=None, func=func)

    return wrapped


class CoverSettings(NamedTuple):
    object_id: str
    friendly_name: str
    suggested_area: str
    device_class: str
    cover_run_time: Union[float, int]
    tilt_change_time: Union[float, int]
    cover_up: str
    cover_down: str
    cover_up_feature: Union[DigitalOutput, Relay]
    cover_down_feature: Union[DigitalOutput, Relay]


class CoverProperty(NamedTuple):
    set_tilt: bool
    set_position: bool


class CoverProperties:
    blind: CoverProperty = CoverProperty(set_tilt=True, set_position=True)
    roller_shutter: CoverProperty = CoverProperty(set_tilt=False, set_position=False)
    garage_door: CoverProperty = CoverProperty(set_tilt=False, set_position=True)


class CoverState:
    """State constants."""

    OPEN: Final[str] = "open"
    OPENING: Final[str] = "opening"
    CLOSING: Final[str] = "closing"
    CLOSED: Final[str] = "closed"
    STOPPED: Final[str] = "stopped"
    OPEN_IN_PERCENT: Final[int] = 100
    CLOSED_IN_PERCENT: Final[int] = 0


class CoverDeviceState:
    """Device state constants."""

    OPEN: Final[str] = "OPEN"
    CLOSE: Final[str] = "CLOSE"
    STOP: Final[str] = "STOP"
    IDLE: Final[str] = "IDLE"


class CoverTimer:
    """Timer for state changes.

    If the state from the device changed (e.g. open, close, stop, ...)
    a timer is required for the cover runtime. The timer run in an asyncio.py
    task and run a callback function when it expired.
    """

    def __init__(self, timeout: float, callback: Callable[[], Awaitable[None]]) -> None:
        """Initialize timer.

        Parameters
        ----------
        timeout: float
            The timer timeout in seconds.
        callback: Callable
            The callback function that is executed at the end of the timer.
        """
        self._timeout: float = timeout
        self._callback: Callable[[], Awaitable[None]] = callback
        self._task: Optional[Task[Any]] = None

    async def _job(self) -> None:
        await asyncio.sleep(self._timeout - ASYNCIO_SLEEP_DELAY_FIX)
        await self._callback()

    def start(self) -> None:
        """Start cover run timer."""
        self._task = asyncio.create_task(self._job())

    def cancel(self) -> None:
        """Cancel cover run timer."""
        if self._task:
            self._task.cancel()


@dataclass
class CoverTimerStatus:
    timer: Optional[CoverTimer] = None
    start: Optional[float] = None


@dataclass
class CoverCalibration:
    mode: bool = False
    started: bool = False


@dataclass
class CoverCurrentStatus:
    device_state: str = CoverDeviceState.IDLE
    state: Optional[str] = None
    position: Optional[int] = None
    tilt: Optional[int] = None


@dataclass
class CoverStatus:
    state: Optional[str] = None
    position: Optional[int] = None
    tilt: Optional[int] = None


class Cover:
    """Class to control a cover and get the state of it.

    Attributes
    ----------
    calibrate_mode: bool
        Set the cover in calibration mode.
    object_id: str, optional
        ID. Used for ``Entity ID`` in Home Assistant.
    friendly_name: str
        Friendly name of the cover. Used for ``Name`` in Home Assistant.
    suggested_area: str, optional
        Suggest an area. Used for ``Area`` in Home Assistant.
    device_class: str
        Device class can be ``blind``, ``roller_shutter``, or ``garage_door``.
    cover_run_time: float or int, optional
        Define the time (in seconds) it takes for the cover to fully open or close.
    tilt_change_time: float or int, optional
        Define the time (in seconds) that the tilt changes from fully open to fully closed state.
    cover_up: str
        Output circuit name from a relay or digital output.
    cover_down: str
        Output circuit name from a relay or digital output.
    state: str, optional
        Current cover state defined in the ``CoverState()`` class.
    position: int, optional
        Current cover position.
    tilt: int, optional
        Current tilt position.
    cover_up_feature: Feature
        The feature for opening the cover.
    cover_down_feature: Feature
        The feature for closing the cover.
    """

    def __init__(
        self,
        config: Config,
        settings: CoverSettings,
    ) -> None:
        """Initialize cover.

        Parameters
        ----------
        features: FeatureMap
            All registered features (e.g. Relay, Digital Input, ...) from the
            Unipi Neuron.
        """
        self.config: Config = config
        self.settings: CoverSettings = settings

        self.status: CoverStatus = CoverStatus()
        self.properties: CoverProperty = getattr(CoverProperties, settings.device_class)

        self._timer: CoverTimerStatus = CoverTimerStatus()
        self._calibration: CoverCalibration = CoverCalibration()
        self._current: CoverCurrentStatus = CoverCurrentStatus()

    def __repr__(self) -> str:
        return self.settings.friendly_name

    @cached_property
    def unique_id(self) -> str:
        """Get unique id for Home Assistant discovery.

        Returns
        -------
        str:
            Unique ID for Home Assistant discovery.
        """
        return f"{slugify(self.config.device_info.name)}_{self.settings.object_id}"

    @cached_property
    def topic(self) -> str:
        """Get unique name for the MQTT topic.

        Returns
        -------
        str:
            Path for MQTT topic.
        """
        return f"{slugify(self.config.device_info.name)}/{self.settings.object_id}/cover/{self.settings.device_class}"

    @cached_property
    def position_file(self) -> Path:
        """Path to temporary cover file.

        Returns
        -------
        Path:
            Path to temporary cover file.
        """
        return self.config.temp_path / self.topic.replace("/", "__")

    @property
    def is_opening(self) -> bool:
        """Check if cover is opening.

        Returns
        -------
        bool:
            ``True`` if cover is opening else ``False``.
        """
        return self.status.state == CoverState.OPENING

    @property
    def is_closing(self) -> bool:
        """Check if cover is closing.

        Returns
        -------
        bool:
            ``True`` if cover is closing else ``False``.
        """
        return self.status.state == CoverState.CLOSING

    @property
    def state_changed(self) -> bool:
        """Check whether the state has changed.

        When the state changed then this return ``True``. The state is changed
        when the cover open, close or stopped.

        Returns
        -------
        bool
            ``True`` if position changed else ``False``.

        See Also
        --------
            covers.Cover.open(): open the cover.
            covers.Cover.close(): close the cover.
            covers.Cover.stop(): stop the cover.
            covers.Cover.set_position(): set the cover position.
        """
        if changed := self.status.state != self._current.state:
            self._current.state = self.status.state

        return changed

    @property
    def position_changed(self) -> bool:
        """Check whether the position has changed.

        When the position changed and the device state is **IDLE** then this
        return ``True``. The device state is **IDLE** when a command
        (OPENING or CLOSE) is stopped.

        Returns
        -------
        bool
            ``True`` if position changed else ``False``.

        See Also
        --------
            covers.Cover.open(): open the cover.
            covers.Cover.close(): close the cover.
            covers.Cover.set_position(): set the cover position.
        """
        if self.properties.set_position is True:
            changed: bool = self.status.position != self._current.position

            if changed and self._current.device_state == CoverDeviceState.IDLE:
                self._current.position = self.status.position
                return True

        return False

    @property
    def tilt_changed(self) -> bool:
        """Check whether the tilt has changed.

        When the tilt changed and the device state is **IDLE** then this
        return ``True``. The device state is **IDLE** when a command
        (OPENING or CLOSE) is stopped.

        Returns
        -------
        bool
            ``True`` if tilt changed else ``False``.

        See Also
        --------
            covers.Cover.set_tilt(): set the cover tilt position.
        """
        if self.properties.set_tilt is True:
            changed: bool = self.status.tilt != self._current.tilt

            if changed and self._current.device_state == CoverDeviceState.IDLE:
                self._current.tilt = self.status.tilt
                return True

        return False

    def _stop_timer(self) -> None:
        if self._timer.timer is not None:
            self._timer.timer.cancel()
            self._timer.timer = None

        self._timer.start = None

    def _update_state(self) -> None:
        if self.properties.set_position is True:
            if self.status.position is not None:
                if self.status.position <= CoverState.CLOSED_IN_PERCENT:
                    self.status.state = CoverState.CLOSED
                elif self.status.position >= CoverState.OPEN_IN_PERCENT:
                    self.status.state = CoverState.OPEN
                else:
                    self.status.state = CoverState.STOPPED
        else:
            self.status.state = CoverState.STOPPED

    def _update_position(self) -> None:
        if not self.properties.set_position:
            return

        if self._timer.start is None:
            return

        if self.status.position is not None:
            end_timer = time.monotonic() - self._timer.start

            if self.is_closing:
                self.status.position = int(
                    round(100 * (self.settings.cover_run_time - end_timer) / self.settings.cover_run_time)
                ) - (100 - self.status.position)
            elif self.is_opening:
                self.status.position = self.status.position + int(round(100 * end_timer / self.settings.cover_run_time))

            if self.status.position <= CoverState.CLOSED_IN_PERCENT:
                self.status.position = CoverState.CLOSED_IN_PERCENT
            elif self.status.position >= CoverState.OPEN_IN_PERCENT:
                self.status.position = CoverState.OPEN_IN_PERCENT

    def _delete_position(self) -> None:
        if self.properties.set_position is True:
            self.position_file.unlink(missing_ok=True)

    @run_in_executor
    def _write_position(self) -> None:
        if self.properties.set_position is True:
            self.position_file.write_text(f"{self.status.position}/{self.status.tilt}")

    def read_position(self) -> None:
        """Read the cover position and tilt from the temporary cover file."""
        if self.properties.set_position is True:
            try:
                data: List[str] = self.position_file.read_text().split("/")
                self.status.position = int(data[0])
                self.status.tilt = int(data[1])
            except (FileNotFoundError, IndexError, ValueError):
                self.status.position = CoverState.CLOSED_IN_PERCENT
                self.status.tilt = CoverState.CLOSED_IN_PERCENT

                self._calibration.mode = True

    async def calibrate(self) -> Optional[float]:
        """Calibrate cover if it is not calibrated.

        Returns
        -------
        float, optional
            Cover run time for fully opened cover.
        """
        if self._calibration.mode is True and not self._calibration.started:
            self._calibration.started = True
            return await self.open_cover(calibrate=True)

        return None

    async def open_cover(self, position: int = CoverState.OPEN_IN_PERCENT, calibrate: bool = False) -> Optional[float]:
        """Close the cover.

        If the cover is in calibration mode then the cover will be fully open.

        For safety reasons, the relay for close the cover will be deactivated.
        If this is successful, the relay to open the cover is activated.

        The device state is changed to **OPEN**, the cover state is changed
        to **OPENING** and the timer will be started.

        Parameters
        ----------
        position: int
            The cover position. ``100`` is fully open and ``0`` is fully closed.
        calibrate: bool
            Set position to ``0`` if ``True``.

        Returns
        -------
        float, optional
            Cover run time in seconds.
        """
        if (
            self.properties.set_position is True
            and self.status.position is not None
            and self.status.position >= CoverState.OPEN_IN_PERCENT
        ):
            return None

        if self._calibration.mode is True and not calibrate:
            return None

        self._update_position()
        response: Optional[ModbusResponse] = await self.settings.cover_down_feature.set_state(False)
        self._stop_timer()

        if response:
            await self.settings.cover_up_feature.set_state(True)

            self._current.device_state = CoverDeviceState.OPEN
            self.status.state = CoverState.OPENING
            self._timer.start = time.monotonic()

            if self.properties.set_position is True:
                if self.settings.tilt_change_time:
                    self.status.tilt = CoverState.OPEN_IN_PERCENT

                if self.status.position is not None and self.settings.cover_run_time:
                    position = 105 if position == CoverState.OPEN_IN_PERCENT else position
                    cover_run_time: float = (position - self.status.position) * self.settings.cover_run_time / 100

                    if self.settings.tilt_change_time and cover_run_time < self.settings.tilt_change_time:
                        cover_run_time = self.settings.tilt_change_time

                    self._timer.timer = CoverTimer(cover_run_time, self.stop_cover)
                    self._timer.timer.start()

                    self._delete_position()

                    return cover_run_time

        return None

    async def close_cover(self, position: int = CoverState.CLOSED_IN_PERCENT) -> Optional[float]:
        """Close the cover.

        If the cover is in calibration mode then the cover will be fully closed.

        If the cover is already opening or closing then the position is
        updated. If a running timer exists, it will be stopped.

        For safety reasons, the relay for open the cover will be deactivated.
        If this is successful, the relay to close the cover is activated.

        The device state is changed to **CLOSE**, the cover state is changed
        to **CLOSING** and the timer will be started.

        Parameters
        ----------
        position: int
            The cover position. ``100`` is fully open and ``0`` is fully closed.

        Returns
        -------
        float, optional
            Cover run time in seconds.
        """
        if self.properties.set_position is True:
            if self.status.position is None:
                return None

            if self.status.position <= CoverState.CLOSED_IN_PERCENT:
                return None

        if self._calibration.mode is True:
            return None

        self._update_position()
        response: Optional[ModbusResponse] = await self.settings.cover_up_feature.set_state(False)
        self._stop_timer()

        if response:
            await self.settings.cover_down_feature.set_state(True)

            self._current.device_state = CoverDeviceState.CLOSE
            self.status.state = CoverState.CLOSING
            self._timer.start = time.monotonic()

            if self.properties.set_position is True:
                if self.settings.tilt_change_time:
                    self.status.tilt = CoverState.CLOSED_IN_PERCENT

                if self.status.position is not None and self.settings.cover_run_time:
                    position = position if position else -5
                    cover_run_time: float = (self.status.position - position) * self.settings.cover_run_time / 100

                    if self.settings.tilt_change_time and cover_run_time < self.settings.tilt_change_time:
                        cover_run_time = self.settings.tilt_change_time

                    self._timer.timer = CoverTimer(cover_run_time, self.stop_cover)
                    self._timer.timer.start()

                    self._delete_position()

                    return cover_run_time

        return None

    async def stop_cover(self) -> None:
        """Stop moving the cover.

        If the cover is already opening or closing then the position is
        updated. If a running timer exists, it will be stopped.

        If position is lower than equal 0 then the cover state is set to
        closed. If position is greater than equal 100 then the cover state is
        set to open. On all other positions the cover state is set to stopped.

        The device state is changed to **IDLE** and the timer will be
        reset.
        """
        self._update_position()

        if self._calibration.mode is True:
            if self.status.position == CoverState.OPEN_IN_PERCENT:
                self._calibration.mode = False
            else:
                self.status.position = CoverState.CLOSED_IN_PERCENT
                return

        await self.settings.cover_down_feature.set_state(False)
        await self.settings.cover_up_feature.set_state(False)

        await self._write_position()
        self._stop_timer()
        self._update_state()

        self._current.device_state = CoverDeviceState.IDLE

    async def _open_tilt(self, tilt: int = CoverState.OPEN_IN_PERCENT) -> Optional[float]:
        cover_run_time: Optional[float] = None

        if self.status.tilt is None:
            return None

        if self.status.tilt == CoverState.OPEN_IN_PERCENT:
            return None

        if self.settings.tilt_change_time:
            self._update_position()
            response: Optional[ModbusResponse] = await self.settings.cover_down_feature.set_state(False)
            self._stop_timer()

            if response:
                await self.settings.cover_up_feature.set_state(True)

                self._current.device_state = CoverDeviceState.OPEN
                self.status.state = CoverState.OPENING
                self._timer.start = time.monotonic()

                cover_run_time = (tilt - self.status.tilt) * self.settings.tilt_change_time / 100

                self._timer.timer = CoverTimer(cover_run_time, self.stop_cover)
                self._timer.timer.start()

                self._delete_position()

        return cover_run_time

    async def _close_tilt(self, tilt: int = CoverState.CLOSED_IN_PERCENT) -> Optional[float]:
        cover_run_time: Optional[float] = None

        if not self.status.tilt:
            return None

        if self.settings.tilt_change_time:
            self._update_position()
            response: Optional[ModbusResponse] = await self.settings.cover_up_feature.set_state(False)
            self._stop_timer()

            if response:
                await self.settings.cover_down_feature.set_state(True)

                self._current.device_state = CoverDeviceState.CLOSE
                self.status.state = CoverState.CLOSING
                self._timer.start = time.monotonic()

                cover_run_time = (self.status.tilt - tilt) * self.settings.tilt_change_time / 100

                self._timer.timer = CoverTimer(cover_run_time, self.stop_cover)
                self._timer.timer.start()

                self._delete_position()

        return cover_run_time

    async def set_position(self, position: int) -> Optional[float]:
        """Set the cover position.

        Parameters
        ----------
        position: int
            The cover position. ``100`` is fully open and ``0`` is fully closed.

        Returns
        -------
        float, optional
            Cover run time in seconds.
        """
        if not self.properties.set_position:
            return None

        cover_run_time: Optional[float] = None

        if not self._calibration.mode and self.status.position is not None:
            if position > self.status.position:
                cover_run_time = await self.open_cover(position)
            elif position < self.status.position:
                cover_run_time = await self.close_cover(position)

        return cover_run_time

    async def set_tilt(self, tilt: int) -> Optional[float]:
        """Set the tilt position.

        Parameters
        ----------
        tilt: int
            The tilt position. ``100`` is fully open and ``0`` is fully closed.

        Returns
        -------
        float, optional
            Cover run time in seconds.
        """
        if not self.properties.set_tilt:
            return None

        if not self.settings.tilt_change_time:
            return None

        cover_run_time: Optional[float] = None

        if not self._calibration.mode and self.status.tilt is not None:
            if tilt > self.status.tilt:
                cover_run_time = await self._open_tilt(tilt)
            elif tilt < self.status.tilt:
                cover_run_time = await self._close_tilt(tilt)

            self.status.tilt = tilt

        return cover_run_time


class CoverMap(Mapping[str, List[Cover]]):
    def __init__(self, config: Config, features: FeatureMap) -> None:
        self.data: Dict[str, List[Cover]] = {}

        self.config: Config = config
        self.features: FeatureMap = features

    def __getitem__(self, key: str) -> List[Cover]:
        data: List[Cover] = self.data[key]
        return data

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def init(self) -> None:
        """Initialize covers from covers config."""
        for cover in self.config.covers:
            device_class: str = cover.device_class

            if not self.data.get(device_class):
                self.data[device_class] = []

            _cover = Cover(
                config=self.config,
                settings=CoverSettings(
                    **asdict(cover),
                    cover_up_feature=self.features.by_feature_id(cover.cover_up),
                    cover_down_feature=self.features.by_feature_id(cover.cover_down),
                ),
            )

            _cover.read_position()

            self.data[device_class].append(_cover)

    def by_device_classes(self, device_classes: List[str]) -> Iterator[Cover]:
        """Filter covers by device classes.

        Parameters
        ----------
        device_classes: list
            A list of device classes to filter covers.

        Returns
        -------
        Iterator:
            Filtered covers list.
        """
        return itertools.chain.from_iterable(
            [item for item in (self.data.get(device_class) for device_class in device_classes) if item is not None]
        )
