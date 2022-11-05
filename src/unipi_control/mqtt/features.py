import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Any
from typing import AsyncIterable
from typing import List
from typing import Set

from asyncio_mqtt import Client

from unipi_control.config import HardwareType
from unipi_control.config import logger
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.logging import LOG_MQTT_SUBSCRIBE
from unipi_control.logging import LOG_MQTT_SUBSCRIBE_TOPIC


class BaseFeaturesMqttPlugin:
    PUBLISH_RUNNING: bool = True
    subscribe_feature_types: List[str] = []
    publish_feature_types: List[str] = []

    def __init__(self, neuron, mqtt_client: Client):
        self.neuron = neuron
        self.mqtt_client: Client = mqtt_client

    async def _publish(self, scan_type: str, hardware_types: List[str], feature_types: List[str], sleep: float):
        while self.PUBLISH_RUNNING:
            await self.neuron.modbus_cache_data.scan(scan_type, hardware_types)

            for feature in self.neuron.features.by_feature_types(feature_types):
                if feature.changed:
                    topic: str = f"{feature.topic}/get"
                    await self.mqtt_client.publish(topic, feature.payload, qos=1, retain=True)
                    logger.info(LOG_MQTT_PUBLISH, topic, feature.payload)

            await asyncio.sleep(sleep)


class NeuronFeaturesMqttPlugin(BaseFeaturesMqttPlugin):
    """Provide features control as MQTT commands."""

    subscribe_feature_types: List[str] = ["DO", "RO"]
    publish_feature_types: List[str] = ["DI", "DO", "RO"]
    scan_interval: float = 25e-3

    async def init_tasks(self, stack: AsyncExitStack, tasks: Set[Task]):
        for feature in self.neuron.features.by_feature_types(self.subscribe_feature_types):
            topic: str = f"{feature.topic}/set"

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            subscribe_task: Task[Any] = asyncio.create_task(self._subscribe(feature, topic, messages))
            tasks.add(subscribe_task)

            await self.mqtt_client.subscribe(topic)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        task: Task[Any] = asyncio.create_task(
            self._publish(
                scan_type="tcp",
                hardware_types=[HardwareType.NEURON],
                feature_types=self.publish_feature_types,
                sleep=self.scan_interval,
            )
        )

        tasks.add(task)

    @staticmethod
    async def _subscribe(feature, topic: str, messages: AsyncIterable):
        async for message in messages:
            value: str = message.payload.decode()

            if value == "ON":
                await feature.set_state(True)
            elif value == "OFF":
                await feature.set_state(False)

            logger.info(LOG_MQTT_SUBSCRIBE, topic, value)


class MeterFeaturesMqttPlugin(BaseFeaturesMqttPlugin):
    """Provide features control as MQTT commands."""

    publish_feature_types: List[str] = ["METER"]
    scan_interval: float = 60

    async def init_tasks(self, tasks: Set[Task]):
        task: Task[Any] = asyncio.create_task(
            self._publish(
                scan_type="serial",
                hardware_types=[HardwareType.EXTENSION],
                feature_types=self.publish_feature_types,
                sleep=self.scan_interval,
            )
        )
        tasks.add(task)
