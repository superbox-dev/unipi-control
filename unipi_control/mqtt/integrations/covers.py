"""Initialize MQTT subscribe and publish for covers."""
import asyncio
import re
from asyncio import Queue
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Any
from typing import AsyncIterable
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Set
from typing import Union

from aiomqtt import Client

from unipi_control.config import DEVICE_CLASSES
from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.helpers.log import LOG_MQTT_PUBLISH
from unipi_control.helpers.log import LOG_MQTT_SUBSCRIBE
from unipi_control.helpers.log import LOG_MQTT_SUBSCRIBE_TOPIC
from unipi_control.integrations.covers import Cover
from unipi_control.integrations.covers import CoverDeviceState
from unipi_control.integrations.covers import CoverMap


class SubscribeCommand(NamedTuple):
    command: str
    value: int
    log: List[Union[str, int]]


class CoversMqttPlugin:
    """Provide cover control as MQTT commands."""

    PUBLISH_RUNNING: bool = True
    SUBSCRIBE_RUNNING: bool = True

    def __init__(self, mqtt_client: Client, covers: CoverMap) -> None:
        self.mqtt_client: Client = mqtt_client
        self.covers: CoverMap = covers

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

    async def init_tasks(self, stack: AsyncExitStack, tasks: Set[Task]) -> None:
        """Initialize MQTT tasks for subscribe and publish MQTT topics.

        Parameters
        ----------
        stack: AsyncExitStack
            The async exit stack for MQTT.
        tasks: set
            A set of all MQTT tasks.
        """
        await self._set_position_topic(stack, tasks)
        await self._tilt_command_topic(stack, tasks)
        await self._command_topic(stack, tasks)

        task: Task = asyncio.create_task(self._publish())
        tasks.add(task)

        for cover in self.covers.by_device_classes(DEVICE_CLASSES):
            task = asyncio.create_task(self._subscribe_command_worker(cover))
            tasks.add(task)

    async def _subscribe_command_worker(self, cover: Cover) -> None:
        while self.SUBSCRIBE_RUNNING:
            queue: Queue = self._queues[cover.topic]

            if queue.qsize() > 0:
                UNIPI_LOGGER.info("%s [%s] [Worker] %s task(s) in queue.", LogPrefix.COVER, cover.topic, queue.qsize())

            subscribe_queue: SubscribeCommand = await queue.get()
            command: Callable[[int], Awaitable[Optional[float]]] = getattr(cover, subscribe_queue.command)
            cover_run_time: Optional[float] = await command(subscribe_queue.value)

            UNIPI_LOGGER.info(*subscribe_queue.log)

            if cover_run_time:
                UNIPI_LOGGER.debug(
                    "%s [%s] [Worker] Cover runtime: %s seconds.",
                    LogPrefix.COVER,
                    cover.topic,
                    cover_run_time,
                )

                while cover.is_closing or cover.is_opening:
                    await asyncio.sleep(25e-3)

            queue.task_done()

    async def _command_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> None:
        for cover in self.covers.by_device_classes(DEVICE_CLASSES):
            topic: str = f"{cover.topic}/set"

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task: Task = asyncio.create_task(self._subscribe_command_topic(cover, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic, qos=0)
            UNIPI_LOGGER.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

    async def _set_position_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> None:
        for cover in self.covers.by_device_classes(DEVICE_CLASSES):
            topic: str = f"{cover.topic}/position/set"

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task: Task = asyncio.create_task(self._subscribe_set_position_topic(cover, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic, qos=0)
            UNIPI_LOGGER.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

    async def _tilt_command_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> None:
        for cover in self.covers.by_device_classes(DEVICE_CLASSES):
            if cover.settings.tilt_change_time:
                topic: str = f"{cover.topic}/tilt/set"

                manager = self.mqtt_client.filtered_messages(topic)
                messages = await stack.enter_async_context(manager)

                task: Task = asyncio.create_task(self._subscribe_tilt_command_topic(cover, topic, messages))
                tasks.add(task)

                await self.mqtt_client.subscribe(topic, qos=0)
                UNIPI_LOGGER.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

    async def _subscribe_command_topic(self, cover: Cover, topic: str, messages: AsyncIterable[Any]) -> None:
        async for message in messages:
            value: str = message.payload.decode()

            await self._clear_queue(cover)

            if value == CoverDeviceState.OPEN:
                await cover.open_cover()
            elif value == CoverDeviceState.CLOSE:
                await cover.close_cover()
            elif value == CoverDeviceState.STOP:
                await cover.stop_cover()

            UNIPI_LOGGER.info(LOG_MQTT_SUBSCRIBE, topic, value)

    async def _subscribe_set_position_topic(self, cover: Cover, topic: str, messages: AsyncIterable[Any]) -> None:
        async for message in messages:
            value: str = message.payload.decode()

            if re.match(r"[+-]?\d+$", value):
                position: int = int(value)
                queue: Queue = self._queues[cover.topic]

                await queue.put(
                    SubscribeCommand(
                        command="set_position",
                        value=position,
                        log=[LOG_MQTT_SUBSCRIBE, topic, position],
                    ),
                )

    async def _subscribe_tilt_command_topic(self, cover: Cover, topic: str, messages: AsyncIterable[Any]) -> None:
        async for message in messages:
            value: str = message.payload.decode()

            if re.match(r"[+-]?\d+$", value):
                tilt: int = int(value)
                queue: Queue = self._queues[cover.topic]

                await queue.put(
                    SubscribeCommand(
                        command="set_tilt",
                        value=tilt,
                        log=[LOG_MQTT_SUBSCRIBE, topic, tilt],
                    ),
                )

    async def _publish(self) -> None:
        while self.PUBLISH_RUNNING:
            for cover in self.covers.by_device_classes(DEVICE_CLASSES):
                if cover.position_changed:
                    position_topic: str = f"{cover.topic}/position"
                    await self.mqtt_client.publish(position_topic, cover.status.position, qos=1, retain=True)
                    UNIPI_LOGGER.info(LOG_MQTT_PUBLISH, position_topic, cover.status.position)

                if cover.tilt_changed:
                    tilt_topic: str = f"{cover.topic}/tilt"
                    await self.mqtt_client.publish(tilt_topic, cover.status.tilt, qos=1, retain=True)
                    UNIPI_LOGGER.info(LOG_MQTT_PUBLISH, tilt_topic, cover.status.tilt)

                if cover.state_changed:
                    state_topic: str = f"{cover.topic}/state"
                    await self.mqtt_client.publish(state_topic, cover.state, qos=1, retain=True)
                    UNIPI_LOGGER.info(LOG_MQTT_PUBLISH, state_topic, cover.state)
                await cover.calibrate()
            await asyncio.sleep(25e-3)
