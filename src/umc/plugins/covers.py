import asyncio
import itertools
import json
from dataclasses import asdict

from config import config
from config import logger
from devices import devices
from helpers import MutableMappingMixin


class CoverMap(MutableMappingMixin):
    def __init__(self):
        super().__init__()
        covers = config.plugins.covers
        blinds = covers.get("blinds", [])

        self.mapping["blind"] = []

        for blind in blinds:
            self.mapping["blind"].append(Blind(**blind))

    def by_cover_type(self, cover_type: list) -> list:
        return list(
            itertools.chain.from_iterable(
                map(self.mapping.get, cover_type)
            )
        )


class Cover:
    def __init__(self, *args, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def topic(self) -> str:
        return f"""{config.device_name.lower()}/{self.topic_name}/cover/{self.cover_type}"""

    @property
    def open(self) -> bool:
        return False

    @property
    def opening(self) -> bool:
        return False

    @property
    def closed(self) -> bool:
        return False

    @property
    def closing(self) -> bool:
        return False

    @property
    def stopped(self) -> bool:
        return False

    @property
    def state_message(self) -> str:
        return "open"


class Blind(Cover):
    cover_type = "blind"


class HomeAssistantCoverDiscovery:
    def __init__(self, umc, mqtt_client, covers):
        self.umc = umc
        self.mqtt_client = mqtt_client
        self.covers = covers

        self._hw = umc.neuron.hw

    def _get_discovery(self, cover) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/cover/{cover.topic_name}/config"""

        message: dict = {
            "name": cover.name,
            "unique_id": f"{cover.cover_type}_{cover.topic_name}",
            "command_topic": f"{cover.topic}/set",
            "state_topic": f"{cover.topic}/get",
            "device": {
                "name": config.device_name,
                "identifiers": config.device_name.lower(),
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    async def publish(self) -> None:
        for cover in self.covers.by_cover_type(["blind"]):
            topic, message = self._get_discovery(cover)
            logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
            await self.mqtt_client.publish(topic, json.dumps(message), qos=1)


class CoversMqttPlugin:
    def __init__(self, umc, mqtt_client):
        logger.info("[MQTT] Initialize covers MQTT plugin")
        self.umc = umc
        self.mqtt_client = mqtt_client

        self.covers = CoverMap()
        self._ha = HomeAssistantCoverDiscovery(umc, mqtt_client, self.covers)

    async def init_task(self, stack) -> set:
        tasks = set()

        for cover in self.covers.by_cover_type(["blind"]):
            topic: str = f"""{cover.topic}/set"""

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)
            # TODO: error log plugin config errors

            task = asyncio.create_task(self._subscribe(cover, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic)
            logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        # task = asyncio.create_task(self._publish())
        # tasks.add(task)

        task = asyncio.create_task(self._ha.publish())
        tasks.add(task)

        return tasks

    async def _subscribe(self, cover, topic: str, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            logger.info(template.format(message.payload.decode()))
            value: str = message.payload.decode()

            closing_device = devices.by_circuit(cover.circuit["closing"])
            opening_device = devices.by_circuit(cover.circuit["opening"])

            if all([closing_device, opening_device]):
                if value == "OPEN":
                    response = await closing_device.set_state(0)
                    if not response.isError():
                        await opening_device.set_state(1)
                elif value == "CLOSE":
                    response = await opening_device.set_state(0)
                    if not response.isError():
                        await closing_device.set_state(1)
                elif value == "STOP":
                    await closing_device.set_state(0)
                    await opening_device.set_state(0)

    async def _publish(self) -> None:
        while True:
            for cover in self.covers.by_cover_type(["blind"]):
                # if device.changed:
                topic: str = f"""{cover.topic}/state"""
                logger.info(f"""[MQTT][{topic}] Publishing message: {cover.state_message}""")
                await self.mqtt_client.publish(f"{topic}", cover.state_message, qos=0)

            await asyncio.sleep(250e-3)
