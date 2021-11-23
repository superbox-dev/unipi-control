import asyncio
import itertools
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from typing import Callable
from typing import Optional
from typing import Union

import aiofiles
from config import config
from features import DigitalOutput
from features import FeatureMap
from features import Relay
from helpers import DataStorage


@dataclass(init=False, eq=False, frozen=True)
class CoverState:
    """State constants."""

    OPEN: str = "open"
    OPENING: str = "opening"
    CLOSING: str = "closing"
    CLOSED: str = "closed"
    STOPPED: str = "stopped"


@dataclass(init=False, eq=False, frozen=True)
class CoverDeviceState:
    """Device state constants."""

    OPEN: str = "OPEN"
    CLOSE: str = "CLOSE"
    STOP: str = "STOP"
    IDLE: str = "IDLE"


class CoverTimer:
    """Timer for state changes.

    If the state from the device changed (e.g. open, close, stop, ...)
    a timer is required for the cover runtime. The timer run in an asyncio
    task and run a callback function when it expired.
    """

    def __init__(self, timeout: float, callback: Callable):
        """Initialize timer.

        Parameters
        ----------
        timeout : float
            The timer timeout in seconds.
        callback: Callable
            The callback function that is executed at the end of the timer.
        """
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        """Cancel a running timer before it ends."""
        self._task.cancel()


class Cover:
    """Class to control a cover and get the state of it.

    Attributes
    ----------
    calibrate_mode : bool
        Set the cover in calibration mode.
    friendly_name : str
        Friendly name of the cover. It is used e.g. for Home Assistant.
    cover_type : str
        Cover types can be ``blind``, ``roller_shutter``, or ``garage_door``.
    topic_name : str
        Unique name for the MQTT topic.
    full_open_time : float or int
        Define the time (in seconds) it takes for the cover to fully open.
    full_close_time : float or int
        Define the time (in seconds) it takes for the cover to fully close.
    tilt_change_time : float or int
        Define the time (in seconds) that the tilt changes from fully open to
        fully closed state.
    circuit_up : str
        Output circuit name from a relay or digital output.
    circuit_down : str
        Output circuit name from a relay or digital output.
    state : str, optional
        Current cover state defined in the ``CoverState()`` class.
    position : int, optional
        Current cover position.
    tilt : int, optional
        Current tilt position.
    cover_up_feature : Feature
        The feature for opening the cover.
    cover_down_feature : Feature
        The feature for closing the cover.
    """

    def __init__(self, features, **kwargs):
        """Initialize cover.

        Parameters
        ----------
        features : FeatureMap
            All registered features (e.g. Relay, Digital Input, ...) from the
            Unipi Neuron.
        """
        self.calibrate_mode: bool = False
        self.friendly_name: str = kwargs.get("friendly_name")
        self.cover_type: str = kwargs.get("cover_type")
        self.topic_name: str = kwargs.get("topic_name")
        self.full_open_time: Union[float, int] = kwargs.get("full_open_time")
        self.full_close_time: Union[float, int] = kwargs.get("full_close_time")
        self.tilt_change_time: Union[float, int] = kwargs.get("tilt_change_time")
        self.circuit_up: str = kwargs.get("circuit_up")
        self.circuit_down: str = kwargs.get("circuit_down")
        self.state: Optional[str] = None
        self.position: Optional[int] = None
        self.tilt: Optional[int] = None
        self.cover_up_feature: Union[DigitalOutput, Relay] = features.by_circuit(self.circuit_up, feature_type=["DO", "RO", ])
        self.cover_down_feature: Union[DigitalOutput, Relay] = features.by_circuit(self.circuit_down, feature_type=["DO", "RO", ])

        self._timer: Optional[CoverTimer] = None
        self._start_timer: Optional[float] = None
        self._device_state: str = CoverDeviceState.IDLE
        self._current_state: Optional[str] = None
        self._current_position: Optional[int] = None
        self._current_tilt: Optional[int] = None
        self._calibration_started: bool = False

        temp_dir = Path(gettempdir(), "unipi")
        temp_dir.mkdir(exist_ok=True)
        self._temp_filename = Path(temp_dir, self.topic.replace("/", "__"))
        self._read_position()

    def __repr__(self) -> str:
        return self.friendly_name

    @property
    def topic(self) -> str:
        """MQTT topic prefix.

        All available MQTT topics start with this prefix path.

        Returns
        -------
        str
            Return MQTT topic prefix.
        """
        return f"{config.device_name.lower()}/{self.topic_name}/" \
               f"cover/{self.cover_type}"

    @property
    def is_opening(self) -> bool:
        """Check whether the status is set to opening.

        Returns
        -------
        bool
            ``True`` if the cover state is **OPENING** else ``False``.
        """
        return self.state == CoverState.OPENING

    @property
    def is_closing(self) -> bool:
        """Check whether the status is set to closing.

        Returns
        -------
        bool
            ``True`` if the cover state is **CLOSING** else ``False``.
        """
        return self.state == CoverState.CLOSING

    @property
    def is_stopped(self) -> bool:
        """Check whether the status is set to stopped.

        Returns
        -------
        bool
            ``True`` if the cover state is **STOPPED** else ``False``.
        """
        return self.state == CoverState.STOPPED

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
        changed: bool = self.state != self._current_state

        if changed:
            self._current_state = self.state

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
        changed: bool = self.position != self._current_position

        if changed and self._device_state == CoverDeviceState.IDLE:
            self._current_position = self.position
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
        changed: bool = self.tilt != self._current_tilt

        if changed and self._device_state == CoverDeviceState.IDLE:
            self._current_tilt = self.tilt
            return True

        return False

    def _stop_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        self._start_timer = None

    def _update_position(self) -> None:
        if self._start_timer is None:
            return

        end_timer = time.monotonic() - self._start_timer

        if self.is_closing:
            self.position = int(round(100 * (self.full_close_time - end_timer) / self.full_close_time)) - (100 - self.position)
        elif self.is_opening:
            self.position = self.position + int(
                round(100 * end_timer / self.full_open_time))

        if self.position <= 0:
            self.position = 0
        elif self.position >= 100:
            self.position = 100

    def _delete_position(self):
        self._temp_filename.unlink(missing_ok=True)

    def _read_position(self) -> None:
        try:
            with open(self._temp_filename) as f:
                data = f.read().split("/")
                self.position = int(data[0])
                self.tilt = int(data[1])
        except (FileNotFoundError, IndexError, ValueError):
            self.state = CoverState.CLOSED
            self.position = 0
            self.tilt = 0

            self.calibrate_mode = True

    async def _write_position(self) -> None:
        async with aiofiles.open(self._temp_filename, "w") as f:
            await f.write(f"{self.position}/{self.tilt}")

    async def calibrate(self) -> None:
        """Calibrate the cover if calibration mode is enabled."""
        if self.calibrate_mode and not self._calibration_started:
            self._calibration_started = True
            await self.open(calibrate=True)

    async def open(self, position: int = 100, calibrate: bool = False) -> None:
        """Close the cover.

        If the cover is in calibration mode then the cover will be fully open.

        For safety reasons, the relay for close the cover will be deactivated.
        If this is successful, the relay to open the cover is activated.

        The device state is changed to **OPEN**, the cover state is changed
        to **OPENING** and the timer will be started.

        Parameters
        ----------
        position : int
            The cover position. ``100`` is fully open and ``0`` is fully closed.
        calibrate : bool
            Set position to ``0`` if ``True``.
        """
        if self.position >= 100:
            return

        if self.calibrate_mode and not calibrate:
            return

        self._update_position()
        response = await self.cover_down_feature.set_state(0)
        self._stop_timer()

        if not response.isError():
            await self.cover_up_feature.set_state(1)

            self._device_state = CoverDeviceState.OPEN
            self.state = CoverState.OPENING
            self._start_timer = time.monotonic()
            self.tilt = 100

            if position == 100:
                position = 105

            stop_timer = (position - self.position) * self.full_open_time / 100

            if stop_timer < self.tilt_change_time:
                stop_timer = self.tilt_change_time

            if calibrate:
                self.position = 0

            self._timer = CoverTimer(stop_timer, self.stop)
            self._delete_position()

    async def close(self, position: int = 0, calibrate: bool = False) -> None:
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
        position : int
            The cover position. ``100`` is fully open and ``0`` is fully closed.
        calibrate : bool
            Set position to ``100`` if ``True``.
        """
        if self.position <= 0:
            return

        if self.calibrate_mode and not calibrate:
            return

        self._update_position()
        response = await self.cover_up_feature.set_state(0)
        self._stop_timer()

        if not response.isError():
            await self.cover_down_feature.set_state(1)

            self._device_state = CoverDeviceState.CLOSE
            self.state = CoverState.CLOSING
            self._start_timer = time.monotonic()
            self.tilt = 0

            if position == 0:
                position = -5

            stop_timer = (self.position - position) * self.full_open_time / 100

            if stop_timer < self.tilt_change_time:
                stop_timer = self.tilt_change_time

            if calibrate:
                self.position = 100

            self._timer = CoverTimer(stop_timer, self.stop)
            self._delete_position()

    async def stop(self) -> None:
        """Stop moving the cover.

        If the cover is already opening or closing then the position is
        updated. If a running timer exists, it will be stopped.

        If position is lower then equal 0 then the cover state is set to
        closed. If position is greater then equal 100 then the cover state is
        set to open. On all other positions the cover state is set to stopped.

        The device state is changed to **IDLE** and the timer will be
        reset.
        """
        self._update_position()

        if self.calibrate_mode:
            if self.position == 100:
                self.calibrate_mode = False
            else:
                self.position = 0
                return

        await self.cover_down_feature.set_state(0)
        await self.cover_up_feature.set_state(0)

        await self._write_position()
        self._stop_timer()

        if self.position <= 0:
            self.state = CoverState.CLOSED
        elif self.position >= 100:
            self.state = CoverState.OPEN
        else:
            self.state = CoverState.STOPPED

        self._device_state = CoverDeviceState.IDLE

    async def _open_tilt(self, tilt: int = 100) -> None:
        if self.tilt == 100:
            return

        self._update_position()
        response = await self.cover_down_feature.set_state(0)
        self._stop_timer()

        if not response.isError():
            await self.cover_up_feature.set_state(1)

            self._device_state = CoverDeviceState.OPEN
            self.state = CoverState.OPENING
            self._start_timer = time.monotonic()

            stop_timer = (tilt - self.tilt) * self.tilt_change_time / 100
            self._timer = CoverTimer(stop_timer, self.stop)
            self._delete_position()

    async def _close_tilt(self, tilt: int = 0) -> None:
        if self.tilt == 0:
            return

        self._update_position()
        response = await self.cover_up_feature.set_state(0)
        self._stop_timer()

        if not response.isError():
            await self.cover_down_feature.set_state(1)

            self._device_state = CoverDeviceState.CLOSE
            self.state = CoverState.CLOSING
            self._start_timer = time.monotonic()

            stop_timer = (self.tilt - tilt) * self.tilt_change_time / 100
            self._timer = CoverTimer(stop_timer, self.stop)
            self._delete_position()

    async def set_position(self, position: int) -> None:
        """Set the cover position.

        Parameters
        ----------
        position : int
            The cover position. ``100`` is fully open and ``0`` is fully closed.
        """
        if not self.calibrate_mode:
            if position > self.position:
                await self.open(position)
            elif position < self.position:
                await self.close(position)

    async def set_tilt(self, tilt: int) -> None:
        """Set the tilt position.

        Parameters
        ----------
        tilt : int
            The tilt position. ``100`` is fully open and ``0`` is fully closed.
        """
        if not self.calibrate_mode:
            if tilt > self.tilt:
                await self._open_tilt(tilt)
            elif tilt < self.tilt:
                await self._close_tilt(tilt)

            self.tilt = tilt


class CoverMap(DataStorage):
    """A read-only container object that has saved cover classes.

    See Also
    --------
    helpers.DataStorage
    """

    def __init__(self, features: FeatureMap):
        """Initialize cover map.

        Parameters
        ----------
        features : FeatureMap
            All registered features (e.g. Relay, Digital Input, ...) from the
            Unipi Neuron.
        """
        super().__init__()

        for cover in config.covers:
            cover_type: str = cover["cover_type"]

            if not self.data.get(cover_type):
                self.data[cover_type] = []

            c = Cover(features, **cover)
            self.data[cover_type].append(c)

    def by_cover_type(self, cover_type: list) -> Iterator:
        """Filter covers by cover type.

        Parameters
        ----------
        cover_type : list

        Returns
        ----------
        Iterator
            A list of covers filtered by cover type.
        """
        return itertools.chain.from_iterable(
            filter(None, map(self.data.get, cover_type)))
