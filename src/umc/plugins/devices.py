import asyncio
import json
from dataclasses import asdict
from typing import Optional

from config import config
from config import logger
from devices import devices


class HomeAssistantDevicesDiscovery:
    def __init__(self, umc, mqtt_client):
        self.umc = umc
        self.mqtt_client = mqtt_client
        self._hw = umc.neuron.hw

    def _get_mapping(self, circuit) -> dict:
        return config.plugins.devices["mapping"].get(circuit, {})

    def _get_friendly_name(self, device) -> str:
        friendly_name: Optional[str] = self._get_mapping(device.circuit).get("friendly_name")

        if friendly_name:
            return friendly_name

        return f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]} - {device.circuit_name}"""

    def _get_switch_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/switch/{config.device_name.lower()}/{device.circuit}/config"""

        message: dict = {
            "name": self._get_friendly_name(device),
            "unique_id": f"""{config.device_name.lower()}_{device.circuit}""",
            "availability_topic": f"{device.topic}/available",
            "command_topic": f"{device.topic}/set",
            "state_topic": f"{device.topic}/get",
            "retain": True,
            "qos": 2,
            "device": {
                "name": config.device_name,
                "identifiers": config.device_name.lower(),
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                "sw_version": self.umc.neuron.boards[device.major_group - 1].firmware,
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    def _get_binary_sensor_discovery(self, device) -> tuple:
        topic: str = f"""{config.homeassistant.discovery_prefix}/binary_sensor/{config.device_name.lower()}/{device.circuit}/config"""

        message: dict = {
            "name": self._get_friendly_name(device),
            "unique_id": f"""{config.device_name.lower()}_{device.circuit}""",
            "availability_topic": f"{device.topic}/available",
            "state_topic": f"{device.topic}/get",
            "qos": 2,
            "device": {
                "name": config.device_name,
                "identifiers": config.device_name.lower(),
                "model": f"""{self._hw["neuron"]["name"]} {self._hw["neuron"]["model"]}""",
                "sw_version": self.umc.neuron.boards[device.major_group - 1].firmware,
                **asdict(config.homeassistant.device),
            }
        }

        return topic, message

    async def publish(self) -> None:
        for device in devices.by_device_type(["RO", "DO"]):
            topic, message = self._get_switch_discovery(device)
            json_data: str = json.dumps(message)
            logger.info(f"""[MQTT][{topic}] Publishing message: {json_data}""")
            await self.mqtt_client.publish(topic, json_data, qos=1)

        for device in devices.by_device_type(["DI"]):
            topic, message = self._get_binary_sensor_discovery(device)
            json_data: str = json.dumps(message)
            logger.info(f"""[MQTT][{topic}] Publishing message: {json_data}""")
            await self.mqtt_client.publish(topic, json_data, qos=1)


class DevicesMqttPlugin:
    def __init__(self, umc, mqtt_client):
        logger.info("[MQTT] Initialize devices MQTT plugin")
        self.umc = umc
        self.mqtt_client = mqtt_client
        self._ha = HomeAssistantDevicesDiscovery(umc, mqtt_client)

    async def init_task(self, stack) -> set:
        tasks = set()

        for device in devices.by_device_type(["AO", "DO", "RO"]):
            topic: str = f"""{device.topic}/set"""

            manager = self.mqtt_client.filtered_messages(topic)
            messages = await stack.enter_async_context(manager)

            task = asyncio.create_task(self._subscribe(device, topic, messages))
            tasks.add(task)

            await self.mqtt_client.subscribe(topic)
            logger.debug(f"[MQTT] Subscribe topic `{topic}`")

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        task = asyncio.create_task(self._ha.publish())
        tasks.add(task)

        return tasks

    async def _subscribe(self, device, topic: str, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            value: str = message.payload.decode()
            logger.info(template.format(value))
            print(device, value)
            if value == "ON":
                await device.set_state(1)
            elif value == "OFF":
                await device.set_state(0)

    async def _publish(self) -> None:
        while True:
            await self.umc.neuron.start_scanning()

            for device in devices.by_device_type(["AO", "DI", "DO", "RO"]):
                if device.available_changed:
                    topic: str = f"""{device.topic}/available"""
                    logger.info(f"""[MQTT][{topic}] Publishing message: {device.available_message}""")
                    await self.mqtt_client.publish(topic, device.available_message, qos=2)

                if device.changed:
                    topic: str = f"""{device.topic}/get"""
                    logger.info(f"""[MQTT][{topic}] Publishing message: {device.state_message}""")
                    await self.mqtt_client.publish(topic, device.state_message, qos=2)

            await asyncio.sleep(250e-3)
