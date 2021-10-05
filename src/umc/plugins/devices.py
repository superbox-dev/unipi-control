import asyncio
import json
from dataclasses import asdict
from typing import Optional

from config import config
from config import logger
from devices import devices


class DevicesMqttPlugin:
    def __init__(self, umc, mqtt_client):
        logger.info("[MQTT] Initialize devices MQTT plugin")
        self.umc = umc
        self.mqtt_client = mqtt_client
        self._hw = umc.neuron.hw

    async def init_task(self, stack) -> set:
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

    def _get_mapping(self, circuit) -> dict:
        return config.homeassistant.mapping.get(circuit, {})

    def _get_name(self, device) -> str:
        custom_name: Optional[str] = self._get_mapping(device.circuit).get("name")

        if custom_name:
            return custom_name

        return f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}"""

    def _get_switch_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/switch/{config.device_name.lower()}/{device.circuit}/config"""

        message: dict = {
            "name": f"{self._get_name(device)} - {device.circuit_name}",
            "unique_id": f"""{config.device_name.lower()}_{device.circuit}""",
            "state_topic": f"{device.topic}/get",
            "command_topic": f"{device.topic}/set",
            "payload_on": 1,
            "payload_off": 0,
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "retain": "true",
            "device": {
                "name": f"{config.device_name} {device.major_group}/{len(self.umc.neuron.boards)}",
                # "connections": get_device_connections(),
                "identifiers": f"{config.device_name.lower()} {device.major_group}",
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                "sw_version": self.umc.neuron.boards[device.major_group - 1].firmware,
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    def _get_binary_sensor_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/binary_sensor/{config.device_name.lower()}/{device.circuit}/config"""

        message: dict = {
            "name": f"{self._get_name(device)} - {device.circuit_name}",
            "unique_id": f"""{config.device_name.lower()}_{device.circuit}""",
            "state_topic": f"{device.topic}/get",
            "payload_on": 1,
            "payload_off": 0,
            "value_template": "{{ value_json.value }}",
            "qos": 1,
            "device": {
                "name": f"{config.device_name} {device.major_group}/{len(self.umc.neuron.boards)}",
                # "connections": get_device_connections(),
                "identifiers": f"{config.device_name.lower()} {device.major_group}",
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                "sw_version": self.umc.neuron.boards[device.major_group - 1].firmware,
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

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
        for device in devices.by_name(["RO", "DO"]):
            topic, message = self._get_switch_discovery(device)
            logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
            await self.mqtt_client.publish(topic, json.dumps(message), qos=1)

        for device in devices.by_name(["DI"]):
            topic, message = self._get_binary_sensor_discovery(device)
            logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
            await self.mqtt_client.publish(topic, json.dumps(message), qos=1)

        while True:
            await self.umc.neuron.start_scanning()

            for device in devices.by_name(["AO", "DI", "DO", "RO"]):
                if device.changed:
                    topic: str = f"""{device.topic}/get"""
                    message: dict = asdict(device.message)
                    logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
                    await self.mqtt_client.publish(f"{topic}", json.dumps(message), qos=1)

            await asyncio.sleep(250e-3)
