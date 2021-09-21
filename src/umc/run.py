#!/usr/bin/env python3
import argparse
import asyncio
import json
import signal
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
from homeassistant import HomeAssistant
from neuron import Neuron
from pymodbus.client.asynchronous import schedulers
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusClient
from utils import get_device_topic


class UnipiMqttClient:
    def __init__(self, loop, modbus_client):
        self.neuron = Neuron(modbus_client)
        self.ha = HomeAssistant(self.neuron)

        self._mqtt_client_id: str = f"""{config["device_name"]}-{uuid.uuid4()}"""
        logger.info(f"[MQTT] Client ID: {self._mqtt_client_id}")

        self._tasks = None
        self._retry_reconnect: int = 0

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

            results: namedtuple = await asyncio.gather(*(device.get_state() for device in self._publish_list))

            for device in results:
                if device.changed:
                    topic: str = f"""{get_device_topic(device)}/get"""
                    message: dict = {k: v for k, v in dict(device._asdict()).items() if v is not None}
                    message.pop("changed")

                    logger.info(f"""[MQTT][{topic}] Publishing message: {message}""")
                    await mqtt_client.publish(topic, json.dumps(message), qos=1)

            await asyncio.sleep(250e-3)

    async def _init_tasks(self) -> None:
        async with AsyncExitStack() as stack:
            self._tasks = set()

            stack.push_async_callback(self.cancel_tasks)

            mqtt_client = Client(
                config["mqtt"]["host"],
                port=config["mqtt"]["port"],
                client_id=self._mqtt_client_id,
                keepalive=config["mqtt"]["connection"]["keepalive"],
            )

            await stack.enter_async_context(mqtt_client)
            self._retry_reconnect = 0

            logger.info(f"""[MQTT] Connected to broker at `{config["mqtt"]["host"]}:{config["mqtt"]["port"]}`""")

            for device in self._subscribe_list:
                topic: str = f"""{get_device_topic(device)}/set"""

                manager = mqtt_client.filtered_messages(topic)
                messages = await stack.enter_async_context(manager)

                task = asyncio.create_task(self._subscribe_devices(device, topic, messages))
                self._tasks.add(task)

                await mqtt_client.subscribe(topic)
                logger.debug(f"[MQTT] Subscribe topic `{topic}`")

            task = asyncio.create_task(self._publish_devices(mqtt_client))
            self._tasks.add(task)

            task = asyncio.create_task(self.ha.publish(mqtt_client))
            self._tasks.add(task)

            await asyncio.gather(*self._tasks)

    async def cancel_tasks(self):
        tasks = [t for t in self._tasks if not t.done()]
        [task.cancel() for task in tasks]

        if tasks:
            logger.info(f"Cancelling {len(tasks)} outstanding tasks.")

        await asyncio.gather(*tasks)

    async def shutdown(self, loop, signal=None):
        if signal:
            logger.info(f"Received exit signal {signal.name}...")

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]

        logger.info(f"Cancelling {len(tasks)} outstanding tasks.")

        await asyncio.gather(*tasks)

        loop.stop()

    async def run(self) -> None:
        await self.neuron.initialise_cache()
        await self.neuron.read_boards()

        self._subscribe_list: list = devices.by_name(["RO", "DO"])
        self._publish_list: list = devices.by_name(["RO", "DO", "DI", "LED"])

        reconnect_interval: int = config["mqtt"]["connection"]["reconnect_interval"]
        retry_limit: Optional[int] = config["mqtt"]["connection"]["retry_limit"]

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, type=bool, help="Debug")
    args = parser.parse_args()

    loop, modbus_client = ModbusClient(schedulers.ASYNC_IO, port=502)
    umc = UnipiMqttClient(loop, modbus_client.protocol)
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)

    loop.set_debug(args.debug)

    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(umc.shutdown(loop, s))
        )

    try:
        loop.run_until_complete(umc.run())
    except asyncio.CancelledError as error:
        print(error)
    finally:
        loop.close()
        logger.info("Successfully shutdown the Unipi MQTT Client service.")


if __name__ == "__main__":
    main()
