import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Any
from typing import AsyncIterable
from typing import Set

from config import COVER_TYPES
from config import LOG_MQTT_PUBLISH
from config import LOG_MQTT_SUBSCRIBE
from config import LOG_MQTT_SUBSCRIBE_TOPIC
from config import logger
from covers import CoverDeviceState


class CoversMqttPlugin:
    """Provide cover control as MQTT commands."""

    def __init__(self, uc, mqtt_client):
        """Initialize covers MQTT plugin."""
        self._uc = uc
        self._mqtt_client = mqtt_client

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

        task: Task[Any] = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    async def _command_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> Set[Task]:
        for cover in self._uc.covers.by_cover_type(COVER_TYPES):
            topic: str = f"{cover.topic}/set"

            manager = self._mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe_command_topic(cover, topic, messages))
            tasks.add(task)

            await self._mqtt_client.subscribe(topic, qos=2)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        return tasks

    async def _set_position_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> Set[Task]:
        for cover in self._uc.covers.by_cover_type(COVER_TYPES):
            topic: str = f"{cover.topic}/position/set"

            manager = self._mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe_set_position_topic(cover, topic, messages))
            tasks.add(task)

            await self._mqtt_client.subscribe(topic, qos=2)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        return tasks

    async def _tilt_command_topic(self, stack: AsyncExitStack, tasks: Set[Task]) -> Set[Task]:
        for cover in self._uc.covers.by_cover_type(COVER_TYPES):
            if cover.tilt_change_time:
                topic: str = f"{cover.topic}/tilt/set"

                manager = self._mqtt_client.filtered_messages(topic)
                messages = await stack.enter_async_context(manager)

                task = asyncio.create_task(self._subscribe_tilt_command_topic(cover, topic, messages))
                tasks.add(task)

                await self._mqtt_client.subscribe(topic, qos=2)
                logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        return tasks

    @staticmethod
    async def _subscribe_command_topic(cover, topic: str, messages: AsyncIterable) -> None:
        async for message in messages:
            value: str = message.payload.decode()

            if value == CoverDeviceState.OPEN:
                await cover.open()
            elif value == CoverDeviceState.CLOSE:
                await cover.close()
            elif value == CoverDeviceState.STOP:
                await cover.stop()

            logger.info(LOG_MQTT_SUBSCRIBE, topic, value)

    @staticmethod
    async def _subscribe_set_position_topic(cover, topic: str, messages: AsyncIterable) -> None:
        async for message in messages:
            try:
                position: int = int(message.payload.decode())
                await cover.set_position(position)
                logger.info(LOG_MQTT_SUBSCRIBE, topic, position)
            except ValueError as error:
                logger.error(error)

    @staticmethod
    async def _subscribe_tilt_command_topic(cover, topic: str, messages: AsyncIterable) -> None:
        async for message in messages:
            try:
                tilt: int = int(message.payload.decode())
                await cover.set_tilt(tilt)
                logger.info(LOG_MQTT_SUBSCRIBE, topic, tilt)
            except ValueError as error:
                logger.error(error)

    async def _publish(self) -> None:
        while True:
            for cover in self._uc.covers.by_cover_type(COVER_TYPES):
                if cover.position_changed:
                    position_topic: str = f"{cover.topic}/position"
                    await self._mqtt_client.publish(position_topic, cover.position, qos=2, retain=True)
                    logger.info(LOG_MQTT_PUBLISH, position_topic, cover.position)

                if cover.tilt_changed:
                    tilt_topic: str = f"{cover.topic}/tilt"
                    await self._mqtt_client.publish(tilt_topic, cover.tilt, qos=2, retain=True)
                    logger.info(LOG_MQTT_PUBLISH, tilt_topic, cover.tilt)

                if cover.state_changed:
                    state_topic: str = f"{cover.topic}/state"
                    await self._mqtt_client.publish(state_topic, cover.state, qos=2, retain=True)
                    logger.info(LOG_MQTT_PUBLISH, state_topic, cover.state)

                await cover.calibrate()
            await asyncio.sleep(25e-3)
