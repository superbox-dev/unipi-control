import asyncio
import itertools
import time
from asyncio import Task
from collections.abc import Iterator
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from tempfile import gettempdir
from typing import Callable
from typing import Final
from typing import List
from typing import Optional
from typing import Union

from unipi_control.config import Config
from unipi_control.config import LOG_COVER_DEVICE_LOCKED
from unipi_control.config import logger
from unipi_control.features import DigitalOutput
from unipi_control.features import FeatureMap
from unipi_control.features import Relay
from unipi_control.helpers import DataStorage
from unipi_control.helpers import run_in_executor

ASYNCIO_SLEEP_DELAY_FIX: Final[float] = 0.04


@dataclass(eq=False)
class CoverFeatures:
    set_tilt: bool = field(default=True)
    set_position: bool = field(default=True)


@dataclass(eq=False, frozen=True)
class CoverSettings:
    blind: CoverFeatures = CoverFeatures(set_tilt=True, set_position=True)
    roller_shutter: CoverFeatures = CoverFeatures(set_tilt=False, set_position=False)
    garage_door: CoverFeatures = CoverFeatures(set_tilt=False, set_position=True)


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
        self._timeout: float = timeout
        self._callback: Callable = callback
        self._task: Task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout - ASYNCIO_SLEEP_DELAY_FIX)
        await self._callback()

    def cancel(self):
        self._task.cancel()


class Cover:
    """Class to control a cover and get the state of it.

    Attributes
    ----------
    calibrate_mode : bool
        Set the cover in calibration mode.
    friendly_name : str
        Friendly name of the cover. It is used e.g. for Home Assistant.
    suggested_area : str
        Suggest an area. It is used e.g. for Home Assistant.
    cover_type : str
        Cover types can be ``blind``, ``roller_shutter``, or ``garage_door``.
    topic_name : str
        Unique name for the MQTT topic.
    cover_run_time : float or int, optional
        Define the time (in seconds) it takes for the cover to fully open or close.
    tilt_change_time : float or int, optional
        Define the time (in seconds) that the tilt changes from fully open to fully closed state.
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

    def __init__(self, config, features, **kwargs):
        """Initialize cover.

        Parameters
        ----------
        features : FeatureMap
            All registered features (e.g. Relay, Digital Input, ...) from the
            Unipi Neuron.
        """
        self.config: Config = config

        self.calibrate_mode: bool = False
        self.friendly_name: str = kwargs.get("friendly_name", "")
        self.suggested_area: str = kwargs.get("suggested_area", "")
        self.cover_type: str = kwargs.get("cover_type", "roller_shutter")
        self.topic_name: str = kwargs.get("topic_name")
        self.cover_run_time: Optional[Union[float, int]] = kwargs.get("cover_run_time")
        self.tilt_change_time: Optional[Union[float, int]] = kwargs.get("tilt_change_time")
        self.circuit_up: Optional[str] = kwargs.get("circuit_up")
        self.circuit_down: Optional[str] = kwargs.get("circuit_down")
        self.state: Optional[str] = None
        self.position: Optional[int] = None
        self.tilt: Optional[int] = None

        self.cover_up_feature: Union[DigitalOutput, Relay] = features.by_circuit(
            self.circuit_up, feature_type=["DO", "RO"]
        )

        self.cover_down_feature: Union[DigitalOutput, Relay] = features.by_circuit(
            self.circuit_down, feature_type=["DO", "RO"]
        )

        self.settings: CoverFeatures = getattr(CoverSettings, self.cover_type)

        self._timer: Optional[CoverTimer] = None
        self._start_timer: Optional[float] = None
        self._device_locked: bool = False
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
        return f"{self.config.device_name.lower()}/{self.topic_name}/cover/{self.cover_type}"

    @property
    def is_opening(self) -> bool:
        return self.state == CoverState.OPENING

    @property
    def is_closing(self) -> bool:
        return self.state == CoverState.CLOSING

    @property
    def is_stopped(self) -> bool:
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
        if self.settings.set_position is True:
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
        if self.settings.set_tilt is True:
            changed: bool = self.tilt != self._current_tilt

            if changed and self._device_state == CoverDeviceState.IDLE:
                self._current_tilt = self.tilt
                return True

        return False

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        self._start_timer = None

    def _update_position(self):
        if self.settings.set_position is False:
            return

        if self.position is None:
            return

        if self._start_timer is None:
            return

        end_timer = time.monotonic() - self._start_timer

        if self.is_closing:
            self.position = int(round(100 * (self.cover_run_time - end_timer) / self.cover_run_time)) - (
                100 - self.position
            )
        elif self.is_opening:
            self.position = self.position + int(round(100 * end_timer / self.cover_run_time))

        if self.position <= 0:
            self.position = 0
        elif self.position >= 100:
            self.position = 100

    def _delete_position(self):
        if self.settings.set_position is True:
            self._temp_filename.unlink(missing_ok=True)

    def _read_position(self):
        if self.settings.set_position is True:
            try:
                data: list = self._temp_filename.read_text().split("/")
                self.position = int(data[0])
                self.tilt = int(data[1])
            except (FileNotFoundError, IndexError, ValueError):
                self.state = CoverState.CLOSED
                self.position = 0
                self.tilt = 0

                self.calibrate_mode = True

    @run_in_executor
    def _write_position(self):
        if self.settings.set_position is True:
            self._temp_filename.write_text(f"{self.position}/{self.tilt}")

    async def calibrate(self):
        if self.calibrate_mode is True and self._calibration_started is False:
            self._calibration_started = True
            await self.open(calibrate=True)

    async def open(self, position: int = 100, calibrate: bool = False) -> Optional[float]:
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

        Returns
        -------
        float, optional
            Cover run time in seconds.
        """
        if self._device_locked is True:
            logger.warning(LOG_COVER_DEVICE_LOCKED, self.topic)
            return None

        if self.settings.set_position is True:
            if self.position is None:
                return None

            if self.position >= 100:
                return None

        if self.calibrate_mode is True and calibrate is False:
            return None

        self._update_position()
        response = await self.cover_down_feature.set_state(0)
        self._stop_timer()

        if not response.isError():
            await self.cover_up_feature.set_state(1)

            self._device_state = CoverDeviceState.OPEN
            self.state = CoverState.OPENING
            self._start_timer = time.monotonic()

            if self.settings.set_position is True:
                if self.tilt_change_time:
                    self.tilt = 100

                if self.position is not None and self.cover_run_time is not None:
                    position = 105 if position == 100 else position
                    cover_run_time: float = (position - self.position) * self.cover_run_time / 100

                    if self.tilt_change_time and cover_run_time < self.tilt_change_time:
                        cover_run_time = self.tilt_change_time

                    if calibrate:
                        self.position = 0

                    self._timer = CoverTimer(cover_run_time, self.stop)
                    self._delete_position()

                    return cover_run_time

        return None

    async def close(self, position: int = 0, calibrate: bool = False) -> Optional[float]:
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

        Returns
        -------
        float, optional
            Cover run time in seconds.
        """
        if self._device_locked is True:
            logger.warning(LOG_COVER_DEVICE_LOCKED, self.topic)
            return None

        if self.settings.set_position is True:
            if self.position is None:
                return None

            if self.position <= 0:
                return None

        if self.calibrate_mode is True and calibrate is False:
            return None

        self._update_position()
        response = await self.cover_up_feature.set_state(0)
        self._stop_timer()

        if not response.isError():
            await self.cover_down_feature.set_state(1)

            self._device_state = CoverDeviceState.CLOSE
            self.state = CoverState.CLOSING
            self._start_timer = time.monotonic()

            if self.settings.set_position is True:
                if self.tilt_change_time:
                    self.tilt = 0

                if self.position is not None and self.cover_run_time is not None:
                    position = -5 if position == 0 else position
                    cover_run_time = (self.position - position) * self.cover_run_time / 100

                    if self.tilt_change_time and cover_run_time < self.tilt_change_time:
                        cover_run_time = self.tilt_change_time

                    if calibrate:
                        self.position = 100

                    self._timer = CoverTimer(cover_run_time, self.stop)
                    self._delete_position()

                    return cover_run_time

        return None

    async def stop(self):
        """Stop moving the cover.

        If the cover is already opening or closing then the position is
        updated. If a running timer exists, it will be stopped.

        If position is lower then equal 0 then the cover state is set to
        closed. If position is greater then equal 100 then the cover state is
        set to open. On all other positions the cover state is set to stopped.

        The device state is changed to **IDLE** and the timer will be
        reset.
        """
        if self.settings.set_position is True:
            if self.position is None:
                return

        self._update_position()

        if self.calibrate_mode is True:
            if self.position == 100:
                self.calibrate_mode = False
            else:
                self.position = 0
                return

        await self.cover_down_feature.set_state(0)
        await self.cover_up_feature.set_state(0)

        await self._write_position()
        self._stop_timer()

        if self.settings.set_position is True:
            if self.position <= 0:
                self.state = CoverState.CLOSED
            elif self.position >= 100:
                self.state = CoverState.OPEN
            else:
                self.state = CoverState.STOPPED
        else:
            self.state = CoverState.STOPPED

        self._device_state = CoverDeviceState.IDLE
        self._device_locked = False

    async def _open_tilt(self, tilt: int = 100) -> Optional[float]:
        if self._device_locked is True:
            logger.warning(LOG_COVER_DEVICE_LOCKED, self.topic)
            return None

        if self.tilt is None:
            return None

        if self.tilt == 100:
            return None

        if self.tilt_change_time is None:
            return None

        self._update_position()
        response = await self.cover_down_feature.set_state(0)
        self._stop_timer()

        if not response.isError():
            await self.cover_up_feature.set_state(1)

            self._device_state = CoverDeviceState.OPEN
            self.state = CoverState.OPENING
            self._start_timer = time.monotonic()

            cover_run_time: float = (tilt - self.tilt) * self.tilt_change_time / 100

            self._timer = CoverTimer(cover_run_time, self.stop)
            self._delete_position()

            return cover_run_time

        return None

    async def _close_tilt(self, tilt: int = 0) -> Optional[float]:
        if self._device_locked is True:
            logger.warning(LOG_COVER_DEVICE_LOCKED, self.topic)
            return None

        if self.tilt is None:
            return None

        if self.tilt == 0:
            return None

        if self.tilt_change_time is None:
            return None

        self._update_position()
        response = await self.cover_up_feature.set_state(0)
        self._stop_timer()

        if not response.isError():
            await self.cover_down_feature.set_state(1)

            self._device_state = CoverDeviceState.CLOSE
            self.state = CoverState.CLOSING
            self._start_timer = time.monotonic()

            cover_run_time: float = (self.tilt - tilt) * self.tilt_change_time / 100

            self._timer = CoverTimer(cover_run_time, self.stop)
            self._delete_position()

            return cover_run_time

        return None

    async def set_position(self, position: int) -> Optional[float]:
        """Set the cover position.

        Parameters
        ----------
        position : int
            The cover position. ``100`` is fully open and ``0`` is fully closed.

        Returns
        -------
        float, optional
            Cover run time in seconds.
        """
        if self.settings.set_position is False:
            return None

        cover_run_time: Optional[float] = None

        if not self.calibrate_mode:
            if self.position is not None:
                if position > self.position:
                    cover_run_time = await self.open(position)
                elif position < self.position:
                    cover_run_time = await self.close(position)

        return cover_run_time

    async def set_tilt(self, tilt: int) -> Optional[float]:
        """Set the tilt position.

        Parameters
        ----------
        tilt : int
            The tilt position. ``100`` is fully open and ``0`` is fully closed.

        Returns
        -------
        float, optional
            Cover run time in seconds.
        """
        if self.settings.set_tilt is False:
            return None

        if self.tilt_change_time is None:
            return None

        cover_run_time: Optional[float] = None

        if not self.calibrate_mode:
            if self.tilt is not None:
                if tilt > self.tilt:
                    cover_run_time = await self._open_tilt(tilt)
                elif tilt < self.tilt:
                    cover_run_time = await self._close_tilt(tilt)

                self.tilt = tilt

        return cover_run_time


class CoverMap(DataStorage):
    """A read-only container object that has saved cover classes.

    See Also
    --------
    helpers.DataStorage
    """

    def __init__(self, config: Config, features: FeatureMap):
        """Initialize cover map.

        Parameters
        ----------
        features : FeatureMap
            All registered features (e.g. Relay, Digital Input, ...) from the
            Unipi Neuron.
        """
        super().__init__()

        for cover in config.covers:
            cover_type: str = cover.cover_type

            if not self.data.get(cover_type):
                self.data[cover_type] = []

            c = Cover(config, features, **asdict(cover))
            self.data[cover_type].append(c)

    def by_cover_type(self, cover_type: List[str]) -> Iterator:
        return itertools.chain.from_iterable(filter(None, map(self.data.get, cover_type)))
