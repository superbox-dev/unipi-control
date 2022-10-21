import asyncio
from asyncio import Task
from typing import Set

from unipi_control.config import MODBUS_TYPES
from unipi_control.config import logger
from unipi_control.logging import LOG_MQTT_PUBLISH
from unipi_control.modbus.cache import ModbusCacheData


class ModbusDevicesMqttPlugin:
    PUBLISH_RUNNING: bool = True

    def __init__(self, mqtt_client, devices: ModbusCacheData):
        self._devices: ModbusCacheData = devices
        self._mqtt_client = mqtt_client

    async def init_tasks(self) -> Set[Task]:
        """Add tasks to the ``AsyncExitStack``."""
        tasks: Set[Task] = set()

        task = asyncio.create_task(self._publish())
        tasks.add(task)

        return tasks

    async def _publish(self):
        while self.PUBLISH_RUNNING:
            for device in self._devices.get_register(MODBUS_TYPES):
                topic: str = f"{device.topic}/get"
                await self._mqtt_client.publish(topic, device.json_attributes, qos=1, retain=True)
                logger.info(LOG_MQTT_PUBLISH, topic, device.json_attributes)

            await asyncio.sleep(15)
