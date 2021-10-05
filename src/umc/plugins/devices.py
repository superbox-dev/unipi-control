import asyncio
import json
from dataclasses import asdict

from umc.config import logger
from umc.devices import devices


class DevicesMqttPlugin:
    def __init__(self, umc, mqtt_client):
        logger.info("[MQTT] Initialize devices MQTT plugin")
        self.umc = umc
        self.mqtt_client = mqtt_client

    async def init(self, stack) -> set:
        tasks = set()

        for device in devices.by_name(["AO", "DO", "RO"]):
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
            logger.info(template.format(message.payload.decode()))

            try:
                value: int = int(message.payload.decode())
            except ValueError as e:
                logger.error(e)
            finally:
                await device.set_state(value)

    async def _publish(self) -> None:
        while True:
            await self.umc.neuron.start_scanning()

            for device in devices.by_name(["AO", "DI", "DO", "RO"]):
                if device.changed:
                    topic: str = f"""{device.topic}/get"""
                    message: dict = asdict(device.message)
                    logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
                    await self.mqtt_client.publish(f"{topic}", json.dumps(message), qos=1)

            await asyncio.sleep(250e-3)
