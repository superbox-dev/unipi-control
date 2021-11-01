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

        self._current_command: Optional[str] = None
        self._command: str = CoverCommand.IDLE

        self._current_state: Optional[str] = None
        self._state: str = CoverState.OPEN

        self._position: Optional[int] = None
        self._start_position: Optional[int] = self.position
        self._set_position: Optional[int] = None

        self._circuit_up = devices.by_circuit(self.circuit_up)
        self._circuit_down = devices.by_circuit(self.circuit_down)

    async def calibrate_position(self):
        if self._position is None:
            logger.info(f"""[COVER] Calibrate "{self.friendly_name}".""")
            self._position = 0
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
    def position(self) -> Optional[int]:
        return self._position

    @position.setter
    def position(self, position) -> Optional[int]:
        self._position = position

    @property
    def update_position(self) -> bool:
        changed: bool = False

        if self._command != self._current_command:
            self._current_command = self._command

            if self._current_command == CoverCommand.IDLE:
                changed = True

        return changed

    @property
    def position_message(self) -> Optional[int]:
        return self._position

    async def open(self, position: int = 100) -> None:
        if self.is_closing:
            await self.stop()
        else:
            response = await self._circuit_down.set_state(0)

            if not response.isError():
                await self._circuit_up.set_state(1)

                self._command = CoverCommand.OPEN
                self._state = CoverState.OPENING
                self._set_position = position
                self._start_position = self.position
                self._start_timer = time.monotonic()

                stop_timer: float = (position - self._start_position) * self.full_open_time / 100
                self._timer = CoverTimer(stop_timer, self.stop)

    async def close(self, position: int = 0) -> None:
        if self.is_opening:
            await self.stop()
        else:
            response = await self._circuit_up.set_state(0)

            if not response.isError():
                await self._circuit_down.set_state(1)

                self._command = CoverCommand.CLOSE
                self._state = CoverState.CLOSING
                self._set_position = position
                self._start_position = self.position
                self._start_timer = time.monotonic()

                stop_timer: float = (self._start_position - position) * self.full_open_time / 100
                self._timer = CoverTimer(stop_timer, self.stop)

    async def stop(self) -> None:
        await self._circuit_down.set_state(0)
        await self._circuit_up.set_state(0)

        if self._timer is not None:
            self._timer.cancel()

        if self._start_timer is not None:
            end_timer = time.monotonic() - self._start_timer

            if self.is_closing:
                self.position = int(100 * (self.full_close_time - end_timer) / self.full_close_time) - (100 - self._start_position)
            elif self.is_opening:
                self.position = self._start_position + int(100 * end_timer / self.full_open_time)

        if self.position <= 0:
            self._state = CoverState.CLOSED
        elif self.position >= 100:
            self._state = CoverState.OPEN
        else:
            self._state = CoverState.STOPPED

        self._command = CoverCommand.IDLE
        self._set_position = None
        self._start_position = self.position
        self._start_timer = None

    async def set_position(self, position: int) -> None:
        if position > self.position:
            await self.open(position)
        elif position < self.position:
            await self.close(position)

    # async def set_tilt(self, tilt: int) -> None:
    #    print(tilt, abs(tilt - self._current_tilt), self._current_tilt)

    #    if tilt > self._current_tilt:
    #        await self.open(tilt=abs(tilt - self._current_tilt))
    #        print("open")
    #    elif tilt < self._current_tilt:
    #        await self.close(tilt=abs(tilt - self._current_tilt))
    #        print("close")

    #    self._current_tilt = tilt

    def __repr__(self):
        return self.friendly_name
