import asyncio

from config import COVER_TYPES
from config import logger
from covers import CoverDeviceState


class CoversMqttPlugin:
    def __init__(self, uc, mqtt_client):
        self.uc = uc
        self.mqtt_client = mqtt_client

    async def init_task(self, stack) -> set:
        tasks = set()

        tasks = await self._command_topic(stack, tasks)
        tasks = await self._set_position_topic(stack, tasks)
        tasks = await self._tilt_command_topic(stack, tasks)

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    async def _command_topic(self, stack, tasks):
        for cover in self.uc.covers.by_cover_type(COVER_TYPES):
            topic: str = f"""{cover.topic}/set"""

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe_command_topic(cover, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic, qos=2)
            logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        return tasks

    async def _set_position_topic(self, stack, tasks):
        for cover in self.uc.covers.by_cover_type(COVER_TYPES):
            topic: str = f"""{cover.topic}/position/set"""

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe_set_position_topic(cover, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic, qos=2)
            logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        return tasks

    async def _tilt_command_topic(self, stack, tasks):
        for cover in self.uc.covers.by_cover_type(COVER_TYPES):
            if cover.tilt_change_time:
                topic: str = f"""{cover.topic}/tilt/set"""

                manager = self.mqtt_client.filtered_messages(topic)
                messages = await stack.enter_async_context(manager)

                task = asyncio.create_task(self._subscribe_tilt_command_topic(cover, topic, messages))
                tasks.add(task)

                await self.mqtt_client.subscribe(topic, qos=2)
                logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        return tasks

    @staticmethod
    async def _subscribe_command_topic(cover, topic: str, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            value: str = message.payload.decode()
            logger.info(template.format(value))

            if value == CoverDeviceState.OPEN:
                await cover.open()
            elif value == CoverDeviceState.CLOSE:
                await cover.close()
            elif value == CoverDeviceState.STOP:
                await cover.stop()

    @staticmethod
    async def _subscribe_set_position_topic(cover, topic: str, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            try:
                position: int = int(message.payload.decode())
                logger.info(template.format(position))

                await cover.set_position(position)
            except ValueError as error:
                logger.error(error)

    @staticmethod
    async def _subscribe_tilt_command_topic(cover, topic: str, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            try:
                tilt: int = int(message.payload.decode())
                logger.info(template.format(tilt))

                await cover.set_tilt(tilt)
            except ValueError as error:
                logger.error(error)

    async def _publish(self) -> None:
        while True:
            for cover in self.uc.covers.by_cover_type(COVER_TYPES):
                if cover.position_changed:
                    topic: str = f"{cover.topic}/position"
                    logger.info(f"[MQTT][{topic}] Publishing message: {cover.position_message}")
                    await self.mqtt_client.publish(topic, cover.position_message, qos=2)

                if cover.tilt_changed and cover.tilt_change_time:
                    topic: str = f"{cover.topic}/tilt"
                    logger.info(f"[MQTT][{topic}] Publishing message: {cover.tilt_message}")
                    await self.mqtt_client.publish(topic, cover.tilt_message, qos=2)

                if cover.state_changed:
                    topic: str = f"{cover.topic}/state"
                    logger.info(f"[MQTT][{topic}] Publishing message: {cover.state_message}")
                    await self.mqtt_client.publish(topic, cover.state_message, qos=2)

            await asyncio.sleep(25e-3)
