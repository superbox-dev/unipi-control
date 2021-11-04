import asyncio

from config import LOG_MQTT_PUBLISH
from config import LOG_MQTT_SUBSCRIBE
from config import LOG_MQTT_SUBSCRIBE_TOPIC
from config import logger


class DevicesMqttPlugin:
    def __init__(self, uc, mqtt_client):
        self.uc = uc
        self.mqtt_client = mqtt_client

    async def init_task(self, stack) -> set:
        tasks = set()

        devices = self.uc.neuron.devices.by_device_type(["AO", "DO", "RO"])

        for device in devices:
            topic: str = f"{device.topic}/set"

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe(device, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic)
            logger.debug(LOG_MQTT_SUBSCRIBE_TOPIC, topic)

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    @staticmethod
    async def _subscribe(device, topic: str, messages) -> None:
        async for message in messages:
            value: str = message.payload.decode()
            logger.info(LOG_MQTT_SUBSCRIBE % (topic, value))

            if value == "ON":
                await device.set_state(1)
            elif value == "OFF":
                await device.set_state(0)

    async def _publish(self) -> None:
        while True:
            await self.uc.neuron.start_scanning()

            devices = self.uc.neuron.devices.by_device_type(["AO", "DI", "DO", "RO"])

            for device in devices:
                if device.changed:
                    topic: str = f"{device.topic}/get"
                    logger.info(LOG_MQTT_PUBLISH, (topic, device.state))
                    await self.mqtt_client.publish(topic, device.state, qos=2)

            await asyncio.sleep(25e-3)
