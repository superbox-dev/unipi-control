import asyncio

from config import LOG_MQTT_PUBLISH
from config import LOG_MQTT_SUBSCRIBE
from config import LOG_MQTT_SUBSCRIBE_TOPIC
from config import logger


class FeaturesMqttPlugin:
    def __init__(self, uc, mqtt_client):
        self.uc = uc
        self.mqtt_client = mqtt_client

    async def init_task(self, stack) -> set:
        tasks = set()

        features = self.uc.neuron.features.by_feature_type(["AO", "DO", "RO"])

        for feature in features:
            topic: str = f"{feature.topic}/set"

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(
                self._subscribe(feature,
                                topic,
                                messages)
            )
            tasks.add(task)

            await self.mqtt_client.subscribe(topic)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    @staticmethod
    async def _subscribe(feature, topic: str, messages) -> None:
        async for message in messages:
            value: str = message.payload.decode()
            logger.info(LOG_MQTT_SUBSCRIBE, topic, value)

            if value == "ON":
                await feature.set_state(1)
            elif value == "OFF":
                await feature.set_state(0)

    async def _publish(self) -> None:
        while True:
            await self.uc.neuron.scan()

            features = self.uc.neuron.features.by_feature_type(
                ["AO",
                 "DI",
                 "DO",
                 "RO"]
            )

            for feature in features:
                if feature.changed:
                    topic: str = f"{feature.topic}/get"
                    logger.info(LOG_MQTT_PUBLISH, topic, feature.state)
                    await self.mqtt_client.publish(topic, feature.state, qos=2)

            await asyncio.sleep(25e-3)
