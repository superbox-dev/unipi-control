"""Initialize MQTT subscribe and publish for features."""

import asyncio
from asyncio import Task
from contextlib import AsyncExitStack
from typing import Any, ClassVar
from typing import AsyncIterable
from typing import List
from typing import Set
from typing import Union

from asyncio_mqtt import Client

from unipi_control.config import HardwareType
from unipi_control.config import UNIPI_LOGGER
from unipi_control.features.neuron import DigitalOutput
from unipi_control.features.neuron import Relay
from unipi_control.helpers.log import LOG_MQTT_PUBLISH
from unipi_control.helpers.log import LOG_MQTT_SUBSCRIBE
from unipi_control.helpers.log import LOG_MQTT_SUBSCRIBE_TOPIC
from unipi_control.neuron import Neuron


class BaseFeaturesMqttPlugin:
    PUBLISH_RUNNING: bool = True
    subscribe_feature_types: ClassVar[List[str]] = []
    publish_feature_types: ClassVar[List[str]] = []

    def __init__(self, neuron: Neuron, mqtt_client: Client) -> None:
        self.neuron: Neuron = neuron
        self.mqtt_client: Client = mqtt_client

    async def _publish(self, scan_type: str, hardware_types: List[str], feature_types: List[str], sleep: float) -> None:
        while self.PUBLISH_RUNNING:
            await self.neuron.modbus_cache_data.scan(scan_type, hardware_types)

            for feature in self.neuron.features.by_feature_types(feature_types):
                if feature.changed:
                    topic: str = f"{feature.topic}/get"
                    await self.mqtt_client.publish(topic, feature.payload, qos=1, retain=True)
                    UNIPI_LOGGER.info(LOG_MQTT_PUBLISH, topic, feature.payload)

            await asyncio.sleep(sleep)


class NeuronFeaturesMqttPlugin(BaseFeaturesMqttPlugin):
    """Provide features control as MQTT commands."""

    subscribe_feature_types: ClassVar[List[str]] = ["DO", "RO"]
    publish_feature_types: ClassVar[List[str]] = ["DI", "DO", "RO"]
    scan_interval: float = 25e-3

    async def init_tasks(self, stack: AsyncExitStack, tasks: Set[Task]) -> None:
        """Initialize MQTT tasks for subscribe and publish MQTT topics.

        Parameters
        ----------
        stack: AsyncExitStack
            The async exit stack for mqtt.
        tasks: set
            A set of all MQTT tasks.
        """
        for feature in self.neuron.features.by_feature_types(self.subscribe_feature_types):
            if isinstance(feature, (DigitalOutput, Relay)):
                topic: str = f"{feature.topic}/set"

                manager = self.mqtt_client.filtered_messages(topic)
                messages = await stack.enter_async_context(manager)

                subscribe_task: Task = asyncio.create_task(self._subscribe(feature, topic, messages))
                tasks.add(subscribe_task)

                await self.mqtt_client.subscribe(topic)
                UNIPI_LOGGER.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        task: Task = asyncio.create_task(
            self._publish(
                scan_type="tcp",
                hardware_types=[HardwareType.NEURON],
                feature_types=self.publish_feature_types,
                sleep=self.scan_interval,
            )
        )

        tasks.add(task)

    @staticmethod
    async def _subscribe(feature: Union[DigitalOutput, Relay], topic: str, messages: AsyncIterable[Any]) -> None:
        async for message in messages:
            value: str = message.payload.decode()

            if value == "ON":
                await feature.set_state(True)
                UNIPI_LOGGER.info(LOG_MQTT_SUBSCRIBE, topic, value)
            elif value == "OFF":
                await feature.set_state(False)
                UNIPI_LOGGER.info(LOG_MQTT_SUBSCRIBE, topic, value)


class MeterFeaturesMqttPlugin(BaseFeaturesMqttPlugin):
    """Provide features control as MQTT commands."""

    publish_feature_types: ClassVar[List[str]] = ["METER"]
    scan_interval: float = 25e-3

    async def init_tasks(self, tasks: Set[Task]) -> None:
        """Initialize MQTT tasks for publish MQTT topics.

        Parameters
        ----------
        tasks: set
            A set of all MQTT tasks.
        """
        task: Task = asyncio.create_task(
            self._publish(
                scan_type="serial",
                hardware_types=[HardwareType.EXTENSION],
                feature_types=self.publish_feature_types,
                sleep=self.scan_interval,
            )
        )
        tasks.add(task)
