import asyncio
import itertools
import json
import time
from dataclasses import asdict
from dataclasses import dataclass
from typing import Optional

from config import config
from config import logger
from devices import devices
from helpers import MutableMappingMixin


class CoverMap(MutableMappingMixin):
    def __init__(self):
        super().__init__()
        covers = config.plugins.covers
        blinds = covers.get("blinds", [])

        self.mapping["blind"] = []

        for blind in blinds:
            self.mapping["blind"].append(Blind(**blind))

    def by_cover_type(self, cover_type: list) -> list:
        return list(
            itertools.chain.from_iterable(
                map(self.mapping.get, cover_type)
            )
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
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

        self._current_command: Optional[str] = None
        self._command: str = CoverCommand.IDLE

        self._current_state: Optional[str] = None
        self._state: str = CoverState.OPEN

        self._position: int = 100
        self._set_position: Optional[int] = None
        self._port_up = devices.by_circuit(self.port_up)
        self._port_down = devices.by_circuit(self.port_down)

        self._start_position: int = self.position
        self._event_start_time: Optional[float] = None

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
    def position(self) -> int:
        return self._position

    @position.setter
    def position(self, position: int):
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
    def position_message(self) -> int:
        return self._position

    async def elapsed_time(self) -> None:
        while True:
            self._current_time = time.monotonic()

            if self._event_start_time:
                self._event_time = self._current_time - self._event_start_time
                # print("event_time:", self._event_time, "current:", self._current_time, "event start:", self._event_start_time)

                if self.is_closing:
                    self.position = int(100 * (self.runtime - self._event_time) / self.runtime) - (100 - self._start_position)
                elif self.is_opening:
                    self.position = self._start_position + int(100 * self._event_time / self.runtime)

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

                print(self._state, self.position, self._set_position)

            await asyncio.sleep(20e-3)

    async def open(self, position: int = 100) -> None:
        if self.is_closing:
            await self.stop()
        else:
            response = await self._port_down.set_state(0)

            if not response.isError():
                await self._port_up.set_state(1)

                self._command = CoverCommand.OPEN
                self._state = CoverState.OPENING
                self._set_position = position
                self._start_position = self.position
                self._event_start_time = time.monotonic()

    async def close(self, position: int = 0) -> None:
        if self.is_opening:
            await self.stop()
        else:
            response = await self._port_up.set_state(0)

            if not response.isError():
                await self._port_down.set_state(1)

                self._command = CoverCommand.CLOSE
                self._state = CoverState.CLOSING
                self._set_position = position
                self._start_position = self.position
                self._event_start_time = time.monotonic()

    async def stop(self) -> None:
        await self._port_down.set_state(0)
        await self._port_up.set_state(0)

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


class Blind(Cover):
    cover_type = "blind"


class HomeAssistantCoverDiscovery:
    def __init__(self, umc, mqtt_client, covers):
        self.umc = umc
        self.mqtt_client = mqtt_client
        self.covers = covers

        self._hw = umc.neuron.hw

    def _get_discovery(self, cover) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/cover/{cover.topic_name}/config"""
        message: dict = {
            "name": cover.friendly_name,
            "unique_id": f"{cover.cover_type}_{cover.topic_name}",
            "command_topic": f"{cover.topic}/set",
            "position_topic": f"{cover.topic}/position",
            "set_position_topic": f"{cover.topic}/position/set",
            "state_topic": f"{cover.topic}/state",
            "retain": False,
            "qos": 2,
            "optimistic": False,
            "device": {
                "name": config.device_name,
                "identifiers": config.device_name.lower(),
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    async def publish(self) -> None:
        for cover in self.covers.by_cover_type(["blind"]):
            topic, message = self._get_discovery(cover)
            json_data: str = json.dumps(message)
            logger.info(f"""[MQTT][{topic}] Publishing message: {json_data}""")
            await self.mqtt_client.publish(topic, json_data, qos=2)


class CoversMqttPlugin:
    def __init__(self, umc, mqtt_client):
        logger.info("[MQTT] Initialize covers MQTT plugin")
        self.umc = umc
        self.mqtt_client = mqtt_client

        self.covers = CoverMap()
        self._ha = HomeAssistantCoverDiscovery(umc, mqtt_client, self.covers)

    async def init_task(self, stack) -> set:
        tasks = set()

        tasks = await self._command_topic(stack, tasks)
        tasks = await self._set_position_topic(stack, tasks)

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        task = asyncio.create_task(self._ha.publish())
        tasks.add(task)

        return tasks

    async def _command_topic(self, stack, tasks):
        for cover in self.covers.by_cover_type(["blind"]):
            task = asyncio.create_task(cover.elapsed_time())
            tasks.add(task)

            topic: str = f"""{cover.topic}/set"""

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe_command_topic(cover, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic, qos=2)
            logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        return tasks

    async def _set_position_topic(self, stack, tasks):
        for cover in self.covers.by_cover_type(["blind"]):
            topic: str = f"""{cover.topic}/position/set"""

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe_set_position_topic(cover, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic, qos=2)
            logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        return tasks

    async def _subscribe_command_topic(self, cover, topic: str, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            value: str = message.payload.decode()
            logger.info(template.format(value))

            if value == CoverCommand.OPEN:
                await cover.open()
            elif value == CoverCommand.CLOSE:
                await cover.close()
            elif value == CoverCommand.STOP:
                await cover.stop()

    async def _subscribe_set_position_topic(self, cover, topic: str, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            try:
                position: int = int(message.payload.decode())
                logger.info(template.format(position))

                await cover.move(position)
            except ValueError as error:
                logger.error(error)

    async def _publish(self) -> None:
        while True:
            for cover in self.covers.by_cover_type(["blind"]):
                if cover.update_position:
                    topic: str = f"{cover.topic}/position"
                    logger.info(f"[MQTT][{topic}] Publishing message: {cover.position_message}")
                    await self.mqtt_client.publish(topic, cover.position_message, qos=2)

                if cover.state_changed:
                    # if not cover.is_stopped:
                    topic: str = f"{cover.topic}/state"
                    logger.info(f"[MQTT][{topic}] Publishing message: {cover.state_message}")
                    await self.mqtt_client.publish(topic, cover.state_message, qos=2)

            await asyncio.sleep(250e-3)
