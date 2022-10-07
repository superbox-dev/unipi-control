import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Any
from typing import AsyncIterable
from typing import List
from typing import Set

from unipi_control.config import logger
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.logging import LOG_MQTT_SUBSCRIBE
from unipi_control.logging import LOG_MQTT_SUBSCRIBE_TOPIC


class FeaturesMqttPlugin:
    """Provide features control as MQTT commands."""

    PUBLISH_RUNNING: bool = True
    subscribe_feature_types: List[str] = ["DO", "RO"]
    publish_feature_types: List[str] = ["DI", "DO", "RO"]

    def __init__(self, neuron, mqtt_client):
        self._neuron = neuron
        self._mqtt_client = mqtt_client

    async def init_tasks(self, stack: AsyncExitStack) -> Set[Task]:
        tasks: Set[Task] = set()

        for feature in self._neuron.features.by_feature_type(self.subscribe_feature_types):
            topic: str = f"{feature.topic}/set"

            manager = self._mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            subscribe_task: Task[Any] = asyncio.create_task(self._subscribe(feature, topic, messages))
            tasks.add(subscribe_task)

            await self._mqtt_client.subscribe(topic)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    @staticmethod
    async def _subscribe(feature, topic: str, messages: AsyncIterable):
        async for message in messages:
            value: str = message.payload.decode()

            if value == "ON":
                await feature.set_state(1)
            elif value == "OFF":
                await feature.set_state(0)

            logger.info(LOG_MQTT_SUBSCRIBE, topic, value)

    async def _publish(self):
        while self.PUBLISH_RUNNING:
            await self._neuron.scan()

            for feature in self._neuron.features.by_feature_type(self.publish_feature_types):
                if feature.changed:
                    topic: str = f"{feature.topic}/get"
                    await self._mqtt_client.publish(topic, feature.state, qos=1, retain=True)
                    logger.info(LOG_MQTT_PUBLISH, topic, feature.state)

            await asyncio.sleep(25e-3)
