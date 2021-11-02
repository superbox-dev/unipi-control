import asyncio

from config import logger


class DevicesMqttPlugin:
    def __init__(self, uc, mqtt_client):
        self.uc = uc
        self.mqtt_client = mqtt_client

    async def init_task(self, stack) -> set:
        tasks = set()

        for device in self.uc.neuron.devices.by_device_type(["AO", "DO", "RO"]):
            topic: str = f"""{device.topic}/set"""

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe(device, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic)
            logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    async def _subscribe(self, device, topic: str, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            value: str = message.payload.decode()
            logger.info(template.format(value))

            if value == "ON":
                await device.set_state(1)
            elif value == "OFF":
                await device.set_state(0)

    async def _publish(self) -> None:
        while True:
            await self.uc.neuron.start_scanning()

            for device in self.uc.neuron.devices.by_device_type(["AO", "DI", "DO", "RO"]):
                if device.changed:
                    topic: str = f"""{device.topic}/get"""
                    logger.info(f"""[MQTT][{topic}] Publishing message: {device.state_message}""")
                    await self.mqtt_client.publish(topic, device.state_message, qos=2)

            await asyncio.sleep(25e-3)
