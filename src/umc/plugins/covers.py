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


class Cover:
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

        self._current_position: Optional[int] = None
        self._current_state: Optional[str] = None
        self._state: str = CoverState.OPEN
        self._position: int = 100
        self._opening = devices.by_circuit(self.circuit["opening"])
        self._closing = devices.by_circuit(self.circuit["closing"])

        self._start_position: int = self.position
        self._event_start_time: Optional[float] = None

    @property
    def topic(self) -> str:
        return f"{config.device_name.lower()}/{self.topic_name}/cover/{self.cover_type}"

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

    @property
    def state_changed(self) -> bool:
        changed: bool = self.state != self._current_state

        if changed:
            self._current_state = self.state

        return changed

    @property
    def state_message(self) -> str:
        return self.state

    @property
    def position(self) -> str:
        return self._position

    @position.setter
    def position(self, position: int):
        if position <= 0:
            if self.state == CoverState.CLOSING:
                self.state = CoverState.CLOSED

            position = 0
        elif position >= 100:
            if self.state == CoverState.OPENING:
                self.state = CoverState.OPEN

            position = 100

        self._position = int(position)

    @property
    def position_changed(self) -> bool:
        changed: bool = self.position != self._current_position

        if changed:
            self._current_position = self.position

        return changed

    @property
    def position_message(self) -> int:
        return self._position

    async def elapsed_time(self) -> None:
        while True:
            self._current_time = time.monotonic()

            if self._event_start_time:
                self._event_time = self._current_time - self._event_start_time
                print("event_time:", self._event_time, "current:", self._current_time, "event start:", self._event_start_time)

                if self.state == CoverState.CLOSING:
                    self.position = int(100 * (self.runtime - self._event_time) / self.runtime) - (100 - self._start_position)
                elif self.state == CoverState.OPENING:
                    self.position = self._start_position + int(100 * self._event_time / self.runtime)

                print(self.state, self.position)

            await asyncio.sleep(20e-3)

    async def open(self) -> None:
        if all([self._closing, self._opening]):
            response = await self._closing.set_state(0)

            if not response.isError():
                await self._opening.set_state(1)

            self.state = CoverState.OPENING
            self._start_position = self.position
            self._event_start_time = time.monotonic()

    async def close(self) -> None:
        if all([self._closing, self._opening]):
            response = await self._opening.set_state(0)

            if not response.isError():
                await self._closing.set_state(1)

            self.state = CoverState.CLOSING
            self._start_position = self.position
            self._event_start_time = time.monotonic()

    async def stop(self) -> None:
        if all([self._closing, self._opening]):
            await self._closing.set_state(0)
            await self._opening.set_state(0)

            self.state = CoverState.STOPPED
            self._start_position = self.position
            self._event_start_time = None

    def __repr__(self):
        return self.name


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
            "name": cover.name,
            "unique_id": f"{cover.cover_type}_{cover.topic_name}",
            "command_topic": f"{cover.topic}/set",
            "position_topic": f"{cover.topic}/position",
            "state_topic": f"{cover.topic}/state",
            # "position_template:": """{% if not state_attr(entity_id, "current_position") %}{{ value }}{% elif state_attr(entity_id, "current_position") < (value | int) %}{{ (value | int + 1) }}{% elif state_attr(entity_id, "current_position") > (value | int) %}{{ (value | int - 1) }}{% else %}{{ value }}{% endif %}""",
            "retain": "true",
            "qos": 2,
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
            logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
            await self.mqtt_client.publish(topic, json.dumps(message), qos=1)


class CoversMqttPlugin:
    def __init__(self, umc, mqtt_client):
        logger.info("[MQTT] Initialize covers MQTT plugin")
        self.umc = umc
        self.mqtt_client = mqtt_client

        self.covers = CoverMap()
        self._ha = HomeAssistantCoverDiscovery(umc, mqtt_client, self.covers)

    async def init_task(self, stack) -> set:
        tasks = set()

        for cover in self.covers.by_cover_type(["blind"]):
            task = asyncio.create_task(cover.elapsed_time())
            tasks.add(task)

            topic: str = f"""{cover.topic}/set"""

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)
            # TODO: error log plugin config errors

            task = asyncio.create_task(self._subscribe(cover, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic)
            logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        task = asyncio.create_task(self._ha.publish())
        tasks.add(task)

        return tasks

    async def _subscribe(self, cover, topic: str, messages) -> None:
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

    async def _publish(self) -> None:
        while True:
            for cover in self.covers.by_cover_type(["blind"]):
                if cover.position_changed:
                    topic: str = f"{cover.topic}/position"
                    logger.info(f"[MQTT][{topic}] Publishing message: {cover.position_message}")
                    await self.mqtt_client.publish(topic, cover.position_message, qos=2)

                if cover.state_changed:
                    print(cover.state_message)
                    topic: str = f"{cover.topic}/state"
                    logger.info(f"[MQTT][{topic}] Publishing message: {cover.state_message}")
                    await self.mqtt_client.publish(topic, cover.state_message, qos=2)

            await asyncio.sleep(250e-3)
