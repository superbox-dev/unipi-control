import asyncio
from asyncio import Queue
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Any
from typing import AsyncIterable
from typing import Callable
from typing import Dict
from typing import NamedTuple
from typing import Optional
from typing import Set

from unipi_control.config import COVER_TYPES
from unipi_control.config import LogPrefix
from unipi_control.config import logger
from unipi_control.covers import Cover
from unipi_control.covers import CoverDeviceState
from unipi_control.covers import CoverMap
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.logging import LOG_MQTT_SUBSCRIBE
from unipi_control.logging import LOG_MQTT_SUBSCRIBE_TOPIC


class SubscribeCommand(NamedTuple):
    command: str
    value: float
    log: list


class CoversMqttPlugin:
    """Provide cover control as MQTT commands."""

    PUBLISH_RUNNING: bool = True
    SUBSCRIBE_COMMAND_WORKER_RUNNING: bool = True

    def __init__(self, mqtt_client, covers: CoverMap):
        self._covers: CoverMap = covers
        self._mqtt_client = mqtt_client
        self._queues: Dict[str, Queue] = {}

        self._init_queues()

    def _init_queues(self):
        for cover in self._covers.by_cover_type(COVER_TYPES):
            self._queues[cover.topic] = Queue()

    async def _clear_queue(self, cover):
        queue: Queue = self._queues[cover.topic]
        size: int = queue.qsize()

        if size > 0:
            for _ in range(size):
                await queue.get()
                queue.task_done()

            logger.info("%s [%s] [Worker] %s task(s) canceled.", LogPrefix.COVER, cover.topic, size)

    async def init_tasks(self, stack: AsyncExitStack) -> Set[Task]:
        """Add tasks to the ``AsyncExitStack``.

        Parameters
        ----------
        stack : AsyncExitStack
            The asynchronous context manager for the MQTT client.
        """
        tasks: Set[Task] = set()

        tasks = await self._command_topic(stack, tasks)
        tasks = await self._set_position_topic(stack, tasks)
        tasks = await self._tilt_command_topic(stack, tasks)

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        for cover in self._covers.by_cover_type(COVER_TYPES):
            task = asyncio.create_task(self._subscribe_command_worker(cover))
            tasks.add(task)

        return tasks

    async def _subscribe_command_worker(self, cover):
        while self.SUBSCRIBE_COMMAND_WORKER_RUNNING:
            queue: Queue = self._queues[cover.topic]

            if queue.qsize() > 0:
                logger.info("%s [%s] [Worker] %s task(s) in queue.", LogPrefix.COVER, cover.topic, queue.qsize())

            subscribe_queue: SubscribeCommand = await queue.get()
            command: Callable = getattr(cover, subscribe_queue.command)
            cover_run_time: Optional[float] = await command(subscribe_queue.value)

            logger.info(*subscribe_queue.log)

            if cover_run_time:
                logger.debug(
                    "%s [%s] [Worker] Cover runtime: %s seconds.", LogPrefix.COVER, cover.topic, cover_run_time
                )

                while cover.is_closing or cover.is_opening:
                    await asyncio.sleep(25e-3)

                queue.task_done()
            else:
                queue.task_done()

    async def _command_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> Set[Task]:
        for cover in self._covers.by_cover_type(COVER_TYPES):
            topic: str = f"{cover.topic}/set"

            manager = self._mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task: Task[Any] = asyncio.create_task(self._subscribe_command_topic(cover, topic, messages))
            tasks.add(task)

            await self._mqtt_client.subscribe(topic, qos=0)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        return tasks

    async def _set_position_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> Set[Task]:
        for cover in self._covers.by_cover_type(COVER_TYPES):
            topic: str = f"{cover.topic}/position/set"

            manager = self._mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task: Task[Any] = asyncio.create_task(self._subscribe_set_position_topic(cover, topic, messages))
            tasks.add(task)

            await self._mqtt_client.subscribe(topic, qos=0)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        return tasks

    async def _tilt_command_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> Set[Task]:
        for cover in self._covers.by_cover_type(COVER_TYPES):
            if cover.tilt_change_time:
                topic: str = f"{cover.topic}/tilt/set"

                manager = self._mqtt_client.filtered_messages(topic)
                messages = await stack.enter_async_context(manager)

                task: Task[Any] = asyncio.create_task(self._subscribe_tilt_command_topic(cover, topic, messages))
                tasks.add(task)

                await self._mqtt_client.subscribe(topic, qos=0)
                logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        return tasks

    async def _subscribe_command_topic(self, cover: Cover, topic: str, messages: AsyncIterable):
        async for message in messages:
            value: str = message.payload.decode()

            await self._clear_queue(cover)

            if value == CoverDeviceState.OPEN:
                await cover.open()
            elif value == CoverDeviceState.CLOSE:
                await cover.close()
            elif value == CoverDeviceState.STOP:
                await cover.stop()

            logger.info(LOG_MQTT_SUBSCRIBE, topic, value)

    async def _subscribe_set_position_topic(self, cover: Cover, topic: str, messages: AsyncIterable):
        async for message in messages:
            try:
                position: int = int(message.payload.decode())
                queue: Queue = self._queues[cover.topic]

                await queue.put(
                    SubscribeCommand(
                        command="set_position",
                        value=position,
                        log=[LOG_MQTT_SUBSCRIBE, topic, position],
                    )
                )
            except ValueError as error:
                logger.error(error)

    async def _subscribe_tilt_command_topic(self, cover: Cover, topic: str, messages: AsyncIterable):
        async for message in messages:
            try:
                tilt: int = int(message.payload.decode())
                queue: Queue = self._queues[cover.topic]

                await queue.put(
                    SubscribeCommand(
                        command="set_tilt",
                        value=tilt,
                        log=[LOG_MQTT_SUBSCRIBE, topic, tilt],
                    )
                )
            except ValueError as error:
                logger.error(error)

    async def _publish(self):
        while self.PUBLISH_RUNNING:
            for cover in self._covers.by_cover_type(COVER_TYPES):
                if cover.position_changed:
                    position_topic: str = f"{cover.topic}/position"
                    await self._mqtt_client.publish(position_topic, cover.position, qos=1, retain=True)
                    logger.info(LOG_MQTT_PUBLISH, position_topic, cover.position)

                if cover.tilt_changed:
                    tilt_topic: str = f"{cover.topic}/tilt"
                    await self._mqtt_client.publish(tilt_topic, cover.tilt, qos=1, retain=True)
                    logger.info(LOG_MQTT_PUBLISH, tilt_topic, cover.tilt)

                if cover.state_changed:
                    state_topic: str = f"{cover.topic}/state"
                    await self._mqtt_client.publish(state_topic, cover.state, qos=1, retain=True)
                    logger.info(LOG_MQTT_PUBLISH, state_topic, cover.state)

                await cover.calibrate()
            await asyncio.sleep(25e-3)
