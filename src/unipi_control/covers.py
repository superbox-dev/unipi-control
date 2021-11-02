import asyncio
import itertools
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional

from config import config
from config import logger
from helpers import MutableMappingMixin


class CoverMap(MutableMappingMixin):
    def __init__(self, devices):
        super().__init__()

        for index, cover in enumerate(config.covers):
            cover_type: str = cover["cover_type"]

            if not self.mapping.get(cover_type):
                self.mapping[cover_type] = []

            c = Cover(devices, **cover)

            if c.is_valid_config:
                self.mapping[cover_type].append(c)

    def by_cover_type(self, cover_type: list) -> Iterator:
        return itertools.chain.from_iterable(
            filter(None, map(self.mapping.get, cover_type))
        )


@dataclass(frozen=True)
class CoverState:
    OPEN: str = "open"
    OPENING: str = "opening"
    CLOSING: str = "closing"
    CLOSED: str = "closed"
    STOPPED: str = "stopped"


@dataclass(frozen=True)
class CoverCommand:
    OPEN: str = "OPEN"
    CLOSE: str = "CLOSE"
    STOP: str = "STOP"
    IDLE: str = "IDLE"


class CoverTimer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()


class Cover:
    def __init__(self, devices, *args, **kwargs):
        self.__dict__.update(kwargs)

        self._timer: Optional[CoverTimer] = None
        self._start_timer: Optional[float] = None

        self._command: str = CoverCommand.IDLE

        self._current_state: Optional[str] = None
        self._state: str = CoverState.OPEN

        self._current_position: Optional[int] = None
        self.position: Optional[int] = None

        self._current_tilt: Optional[int] = None
        self.tilt: Optional[int] = None

        self._circuit_up = devices.by_circuit(self.circuit_up)
        self._circuit_down = devices.by_circuit(self.circuit_down)

    async def calibrate_position(self):
        if self.position is None:
            logger.info(f"""[COVER] Calibrate "{self.friendly_name}".""")
            self.position = 0
            self.tilt = 0
            await self.open()

    @property
    def is_valid_config(self):
        if self._circuit_up and self._circuit_down:
            return True

        return False

    @property
    def topic(self) -> str:
        return f"{config.device_name.lower()}/{self.topic_name}/cover/{self.cover_type}"

    @property
    def is_opening(self) -> bool:
        return self._state == CoverState.OPENING

    @property
    def is_closing(self) -> bool:
        return self._state == CoverState.CLOSING

    @property
    def is_stopped(self) -> bool:
        return self._state == CoverState.STOPPED

    @property
    def state_changed(self) -> bool:
        changed: bool = self._state != self._current_state

        if changed:
            self._current_state = self._state

        return changed

    @property
    def state_message(self) -> str:
        return self._state

    @property
    def position_changed(self) -> bool:
        changed: bool = self.position != self._current_position

        if changed and self._command == CoverCommand.IDLE:
            self._current_position = self.position
            return True

        return False

    @property
    def position_message(self) -> Optional[int]:
        return self.position

    @property
    def tilt_message(self) -> Optional[int]:
        return self.tilt

    @property
    def tilt_changed(self) -> bool:
        changed: bool = self.tilt != self._current_tilt

        if changed and self._command == CoverCommand.IDLE:
            self._current_tilt = self.tilt
            return True

        return False

    def _stop_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _update_position(self) -> None:
        if self._start_timer is not None:
            end_timer = time.monotonic() - self._start_timer

            if self.is_closing:
                self.position = int(round(100 * (self.full_close_time - end_timer) / self.full_close_time)) - (100 - self.position)
            elif self.is_opening:
                self.position = self.position + int(round(100 * end_timer / self.full_open_time))

    async def open(self, position: int = 100, tilt: Optional[int] = None) -> None:
        self._stop_timer()
        self._update_position()

        response = await self._circuit_down.set_state(0)

        if not response.isError():
            await self._circuit_up.set_state(1)

            self._command = CoverCommand.OPEN
            self._state = CoverState.OPENING
            self._start_timer = time.monotonic()

            if tilt is not None:
                stop_timer = (tilt - self.tilt) * self.tilt_change_time / 100
            elif position is not None:
                if position == 100:
                    position = 105

                stop_timer: float = (position - self.position) * self.full_open_time / 100

            self._timer = CoverTimer(stop_timer, self.stop)

    async def close(self, position: int = 0, tilt: Optional[int] = None) -> None:
        self._stop_timer()
        self._update_position()

        response = await self._circuit_up.set_state(0)

        if not response.isError():
            await self._circuit_down.set_state(1)

            self._command = CoverCommand.CLOSE
            self._state = CoverState.CLOSING
            self._start_timer = time.monotonic()

            if tilt is not None:
                stop_timer = (self.tilt - tilt) * self.tilt_change_time / 100
            elif position is not None:
                if position == 0:
                    position = -5

                stop_timer: float = (self.position - position) * self.full_open_time / 100

            self._timer = CoverTimer(stop_timer, self.stop)

    async def stop(self) -> None:
        await self._circuit_down.set_state(0)
        await self._circuit_up.set_state(0)

        self._stop_timer()
        self._update_position()

        if self.position <= 0:
            self.position = 0
            self._state = CoverState.CLOSED
        elif self.position >= 100:
            self.position = 100
            self._state = CoverState.OPEN
        else:
            self._state = CoverState.STOPPED

        self._command = CoverCommand.IDLE
        self._start_timer = None

    async def set_position(self, position: int) -> None:
        if position > self.position:
            await self.open(position)
        elif position < self.position:
            await self.close(position)

    async def set_tilt(self, tilt: int) -> None:
        if tilt > self.tilt:
            await self.open(tilt=tilt)
        elif tilt < self.tilt:
            await self.close(tilt=tilt)

        self.tilt = tilt

    def __repr__(self):
        return self.friendly_name
