#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
import uuid
from collections import namedtuple
from contextlib import AsyncExitStack
from typing import Optional

from asyncio_mqtt import Client
from asyncio_mqtt import MqttError
from config import config
from config import logger
from devices import devices
from neuron import Neuron
from pymodbus.client.asynchronous import schedulers
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusClient
# from api.homeassistant import HomeAssistant


class UnipiMqttClient:
    def __init__(self, modbus_client, debug: bool):
        self.debug: bool = debug
        self.neuron = Neuron(modbus_client)
        self.config = config

        self._mqtt_client_id: str = f"""{self.config["device_name"]}-{uuid.uuid4()}""",
        logger.info(f"[MQTT] Client ID: {self._mqtt_client_id}")

        self._retry_reconnect: int = 0

        # self._ha: Optional[HomeAssistant] = None

    def _get_topic(self, device) -> str:
        topic: str = f"""{self.config["device_name"]}/{device.dev_name}"""

        if device.dev_type:
            topic += f"/{device.dev_type}"

        topic += f"/{device.circuit}"

        return topic

    async def _subscribe_devices(self, device, topic, messages) -> None:
        template: str = f"""[MQTT][{topic}] Subscribe message: {{}}"""

        async for message in messages:
            logger.info(template.format(message.payload.decode()))

            try:
                value: int = int(message.payload.decode())
            except ValueError as e:
                logger.error(e)
            finally:
                await device.set_state(value)

    async def _publish_devices(self, mqtt_client) -> None:
        while True:
            await self.neuron.start_scanning()
            devices: namedtuple = await asyncio.gather(*(device.get_state() for device in self._publish_list))

            for device in devices:
                if device.changed:
                    topic: str = f"""{self._get_topic(device)}/get"""
                    message: dict = {k: v for k, v in dict(device._asdict()).items() if v is not None}
                    message.pop("changed")

                    logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
                    await mqtt_client.publish(topic, json.dumps(message), qos=1)
                    await asyncio.sleep(250e-3)

    def on_message_thread(self, message):
        async def on_message_cb(message):
            device = self._topics[message.topic]

            try:
                value: int = int(message.payload.decode())
            except ValueError as e:
                logger.error(e)
            finally:
                device.set_state(value)

    async def _cancel_tasks(self, tasks):
        for task in tasks:
            if task.done():
                continue

            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _init_tasks(self) -> None:
        async with AsyncExitStack() as stack:
            tasks = set()
            stack.push_async_callback(self._cancel_tasks, tasks)

            mqtt_client = Client(
                self.config["mqtt"]["host"],
                port=self.config["mqtt"]["port"],
                client_id=self._mqtt_client_id,
                keepalive=self.config["mqtt"]["connection"]["keepalive"],
            )

            await stack.enter_async_context(mqtt_client)
            self._retry_reconnect = 0

            logger.info(f"""[MQTT] Connected to broker at `{self.config["mqtt"]["host"]}:{self.config["mqtt"]["port"]}`""")

            for device in self._subscribe_list:
                topic: str = f"""{self._get_topic(device)}/set"""

                manager = mqtt_client.filtered_messages(topic)
                messages = await stack.enter_async_context(manager)

                task = asyncio.create_task(self._subscribe_devices(device, topic, messages))
                tasks.add(task)

                await mqtt_client.subscribe(topic)
                logger.debug(f"[MQTT] Subscribe topic `{topic}`")

            task = asyncio.create_task(self._publish_devices(mqtt_client))
            tasks.add(task)

            await asyncio.gather(*tasks)

    async def run(self) -> None:
        await self.neuron.initialise_cache()
        await self.neuron.read_boards()

        self._subscribe_list: list = devices.by_name(["RO", "DO"])
        self._publish_list: list = devices.by_name(["RO", "DO", "DI", "LED"])

        reconnect_interval: int = self.config["mqtt"]["connection"]["reconnect_interval"]
        retry_limit: Optional[int] = self.config["mqtt"]["connection"]["retry_limit"]

        while True:
            try:
                logger.info("[MQTT] Connecting to broker ...")
                await self._init_tasks()
            except MqttError as error:
                logger.error(f"""[MQTT] Error `{error}`. Connecting attempt #{self._retry_reconnect + 1}. Reconnecting in {reconnect_interval} seconds.""")
            finally:
                if retry_limit and self._retry_reconnect > retry_limit:
                    sys.exit(1)

                self._retry_reconnect += 1

                await asyncio.sleep(reconnect_interval)

    # if not self._ha:
    #    self._ha = HomeAssistant(client=self.mqtt_client, devices=self.devices)
    # self._ha.publish()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, type=bool, help="Debug")
    args = parser.parse_args()

    try:
        loop, modbus_client = ModbusClient(schedulers.ASYNC_IO, port=502)

        loop.run_until_complete(
            UnipiMqttClient(
                modbus_client.protocol,
                debug=args.debug,
            ).run()
        )
    except KeyboardInterrupt:
        logger.info("Process interrupted")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
