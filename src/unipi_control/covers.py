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


class Cover:
    def __init__(self, devices, *args, **kwargs):
        self.__dict__.update(kwargs)

        self._current_command: Optional[str] = None
        self._command: str = CoverCommand.IDLE

        self._current_state: Optional[str] = None
        self._state: str = CoverState.OPEN

        self._position: Optional[int] = None
        self._start_position: Optional[int] = self.position
        self._set_position: Optional[int] = None

        self._circuit_up = devices.by_circuit(self.circuit_up)
        self._circuit_down = devices.by_circuit(self.circuit_down)

        self._event_start_time: Optional[float] = None

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

    async def elapsed_time(self) -> None:
        while True:
            self._current_time = time.monotonic()

            if self._event_start_time:
                self._event_time = self._current_time - self._event_start_time

                if self.is_closing:
                    self.position = int(100 * (self.full_close_time - self._event_time) / self.full_close_time) - (100 - self._start_position)
                elif self.is_opening:
                    self.position = self._start_position + int(100 * self._event_time / self.full_open_time)

                if self.position <= 0:
                    if self.is_closing:
                        await self.stop()

                    self.position = 0
                elif self.position >= 100:
                    if self.is_opening:
                        await self.stop()

                    self.position = 100
                elif self._set_position == self.position:
                    await self.stop()

                logger.debug(f"""[COVER][{self.friendly_name}] {self._state} {self.position}""")

            await asyncio.sleep(20e-3)

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
                self._event_start_time = time.monotonic()

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
                self._event_start_time = time.monotonic()

    async def stop(self) -> None:
        await self._circuit_down.set_state(0)
        await self._circuit_up.set_state(0)

        if self.position <= 0:
            self._state = CoverState.CLOSED
        elif self.position >= 100:
            self._state = CoverState.OPEN
        else:
            self._state = CoverState.STOPPED

        self._command = CoverCommand.IDLE
        self._set_position = None
        self._start_position = self.position
        self._event_start_time = None

    async def move(self, position: int) -> None:
        if position > self.position:
            await self.open(position)
        elif position < self.position:
            await self.close(position)

    def __repr__(self):
        return self.friendly_name
