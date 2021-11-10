import asyncio
from contextlib import AsyncExitStack
from typing import AsyncIterable

from config import LOG_MQTT_PUBLISH
from config import LOG_MQTT_SUBSCRIBE
from config import LOG_MQTT_SUBSCRIBE_TOPIC
from config import logger


class FeaturesMqttPlugin:
    """Provide features control as MQTT commands."""

    def __init__(self, uc, mqtt_client):
        """Initialize features MQTT plugin."""
        self._uc = uc
        self._mqtt_client = mqtt_client

    async def init_tasks(self, stack: AsyncExitStack) -> set:
        """Add tasks to the ``AsyncExitStack``.

        Parameters
        ----------
        stack : AsyncExitStack
            The asynchronous context manager for the MQTT client.
        """
        tasks = set()

        features = self._uc.neuron.features.by_feature_type(["AO", "DO", "RO"])

        for feature in features:
            topic: str = f"{feature.topic}/set"

            manager = self._mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe(feature, topic, messages))
            tasks.add(task)

            await self._mqtt_client.subscribe(topic)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    @staticmethod
    async def _subscribe(feature, topic: str, messages: AsyncIterable) -> None:
        async for message in messages:
            value: str = message.payload.decode()
            logger.info(LOG_MQTT_SUBSCRIBE, topic, value)

            if value == "ON":
                await feature.set_state(1)
            elif value == "OFF":
                await feature.set_state(0)

    async def _publish(self) -> None:
        while True:
            await self._uc.neuron.scan()

            features = self._uc.neuron.features.by_feature_type(["AO", "DI", "DO", "RO"])

            for feature in features:
                if feature.changed:
                    topic: str = f"{feature.topic}/get"
                    logger.info(LOG_MQTT_PUBLISH, topic, feature.state)
                    await self._mqtt_client.publish(topic, feature.state, qos=2, retain=True)

            await asyncio.sleep(25e-3)
