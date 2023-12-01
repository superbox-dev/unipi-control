"""Initialize MQTT subscribe and publish for covers."""
import asyncio
import re
from asyncio import Queue
from asyncio import Task
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import NamedTuple
from typing import Optional
from typing import Set

from aiomqtt import Client

from unipi_control.config import Config
from unipi_control.config import DEVICE_CLASSES
from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.log import LOG_LEVEL
from unipi_control.helpers.log import LOG_MQTT_PUBLISH
from unipi_control.helpers.log import LOG_MQTT_SUBSCRIBE
from unipi_control.helpers.text import slugify
from unipi_control.integrations.covers import Cover
from unipi_control.integrations.covers import CoverDeviceState
from unipi_control.integrations.covers import CoverMap


class SubscribeCommand(NamedTuple):
    command: str
    value: int
    log: str


class CoversMqttHelper:
    """Provide cover control as MQTT commands."""

    PUBLISH_RUNNING: bool = True
    SUBSCRIBE_RUNNING: bool = True

    def __init__(self, client: Client, covers: CoverMap, scan_interval: float) -> None:
        self.config: Config = covers.config
        self.client: Client = client
        self.covers: CoverMap = covers
        self.scan_interval: float = scan_interval

        self._queues: Dict[str, Queue] = {}

        self._init_queues()

    def _init_queues(self) -> None:
        for cover in self.covers.by_device_classes(DEVICE_CLASSES):
            self._queues[cover.topic] = Queue()

    async def _clear_queue(self, cover: Cover) -> None:
        queue: Queue = self._queues[cover.topic]

        if (size := queue.qsize()) > 0:
            for _ in range(size):
                await queue.get()
                queue.task_done()

            UNIPI_LOGGER.info("%s [%s] [Worker] %s task(s) canceled.", LogPrefix.COVER, cover.topic, size)

    async def _subscribe(self) -> None:
        async with self.client.messages() as messages:
            await self.client.subscribe(f"{slugify(self.config.device_info.name)}/+/cover/#", qos=0)

            async for message in messages:
                for cover in self.covers.by_device_classes(DEVICE_CLASSES):
                    set_position_topic: str = f"{cover.topic}/position/set"
                    set_tilt_topic: str = f"{cover.topic}/tilt/set"
                    command_topic: str = f"{cover.topic}/set"

                    if (payload := message.payload) and isinstance(payload, bytes):
                        if message.topic.matches(set_position_topic):
                            await self._subscribe_set_position_topic(cover, set_position_topic, payload)
                        elif message.topic.matches(set_tilt_topic) and cover.settings.tilt_change_time:
                            await self._subscribe_tilt_command_topic(cover, set_tilt_topic, payload)
                        elif message.topic.matches(command_topic):
                            await self._subscribe_command_topic(cover, command_topic, payload)

    async def _publish(self) -> None:
        while self.PUBLISH_RUNNING:
            for cover in self.covers.by_device_classes(DEVICE_CLASSES):
                if cover.position_changed:
                    position_topic: str = f"{cover.topic}/position"
                    await self.client.publish(topic=position_topic, payload=cover.status.position, qos=1, retain=True)

                    if LOG_LEVEL[self.config.logging.mqtt.covers_level] <= LOG_LEVEL["info"]:
                        UNIPI_LOGGER.log(
                            level=LOG_LEVEL["info"],
                            msg=LOG_MQTT_PUBLISH % (position_topic, cover.status.position),
                        )

                if cover.tilt_changed:
                    tilt_topic: str = f"{cover.topic}/tilt"
                    await self.client.publish(topic=tilt_topic, payload=cover.status.tilt, qos=1, retain=True)

                    if LOG_LEVEL[self.config.logging.mqtt.covers_level] <= LOG_LEVEL["info"]:
                        UNIPI_LOGGER.log(
                            level=LOG_LEVEL["info"],
                            msg=LOG_MQTT_PUBLISH % (tilt_topic, cover.status.tilt),
                        )

                if cover.state_changed:
                    state_topic: str = f"{cover.topic}/state"
                    await self.client.publish(topic=state_topic, payload=cover.state, qos=1, retain=True)

                    if LOG_LEVEL[self.config.logging.mqtt.covers_level] <= LOG_LEVEL["info"]:
                        UNIPI_LOGGER.log(
                            level=LOG_LEVEL["info"],
                            msg=LOG_MQTT_PUBLISH % (state_topic, cover.state),
                        )

                await cover.calibrate()
            await asyncio.sleep(self.scan_interval)

    def init(self, tasks: Set[Task]) -> None:
        """Initialize covers MQTT subscribe and publish."""
        tasks.add(asyncio.create_task(self._subscribe()))
        tasks.add(asyncio.create_task(self._publish()))

        for cover in self.covers.by_device_classes(DEVICE_CLASSES):
            tasks.add(asyncio.create_task(self._subscribe_command_worker(cover)))

    async def _subscribe_command_worker(self, cover: Cover) -> None:
        while self.SUBSCRIBE_RUNNING:
            queue: Queue = self._queues[cover.topic]

            if queue.qsize() > 0:
                UNIPI_LOGGER.info("%s [%s] [Worker] %s task(s) in queue.", LogPrefix.COVER, cover.topic, queue.qsize())

            subscribe_queue: SubscribeCommand = await queue.get()
            command: Callable[[int], Awaitable[Optional[float]]] = getattr(cover, subscribe_queue.command)
            cover_run_time: Optional[float] = await command(subscribe_queue.value)

            if LOG_LEVEL[self.config.logging.mqtt.covers_level] <= LOG_LEVEL["info"]:
                UNIPI_LOGGER.log(
                    level=LOG_LEVEL["info"],
                    msg=subscribe_queue.log,
                )

            if cover_run_time:
                UNIPI_LOGGER.debug(
                    "%s [%s] [Worker] Cover runtime: %s seconds.",
                    LogPrefix.COVER,
                    cover.topic,
                    cover_run_time,
                )

                while cover.is_closing or cover.is_opening:
                    await asyncio.sleep(self.scan_interval)

            queue.task_done()

    async def _subscribe_command_topic(self, cover: Cover, topic: str, payload: bytes) -> None:
        value = payload.decode()

        await self._clear_queue(cover)

        if value == CoverDeviceState.OPEN:
            await cover.open_cover()
        elif value == CoverDeviceState.CLOSE:
            await cover.close_cover()
        elif value == CoverDeviceState.STOP:
            await cover.stop_cover()

        if LOG_LEVEL[self.config.logging.mqtt.covers_level] <= LOG_LEVEL["info"]:
            UNIPI_LOGGER.log(
                level=LOG_LEVEL["info"],
                msg=LOG_MQTT_SUBSCRIBE % (topic, value),
            )

    async def _subscribe_set_position_topic(self, cover: Cover, topic: str, payload: bytes) -> None:
        value: str = payload.decode()

        if re.match(r"[+-]?\d+$", value):
            position: int = int(value)
            queue: Queue = self._queues[cover.topic]

            await queue.put(
                SubscribeCommand(
                    command="set_position",
                    value=position,
                    log=LOG_MQTT_SUBSCRIBE % (topic, position),
                ),
            )

    async def _subscribe_tilt_command_topic(self, cover: Cover, topic: str, payload: bytes) -> None:
        value: str = payload.decode()

        if re.match(r"[+-]?\d+$", value):
            tilt: int = int(value)
            queue: Queue = self._queues[cover.topic]

            await queue.put(
                SubscribeCommand(
                    command="set_tilt",
                    value=tilt,
                    log=LOG_MQTT_SUBSCRIBE % (topic, tilt),
                ),
            )
