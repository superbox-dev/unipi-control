#!/usr/bin/env python3
import argparse
import asyncio
import json
import signal
import sys
import uuid
from contextlib import AsyncExitStack
from dataclasses import asdict
from typing import Optional

from asyncio_mqtt import Client as MqttClient
from asyncio_mqtt import MqttError
from config import config
from config import logger
from devices import devices
from homeassistant import HomeAssistant
from modbus import Modbus
from modbus import ModbusException
from neuron import Neuron


class UnipiMqttClient:
    def __init__(self, loop, modbus):
        self.neuron = Neuron(modbus)
        self.ha = HomeAssistant(self.neuron)

        self._mqtt_client_id: str = f"""{config.device_name}-{uuid.uuid4()}"""
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

    async def _publish_devices(self, client: MqttClient) -> None:
        while True:
            await self.neuron.start_scanning()

            for device in devices.by_name(["RO", "DO"]):
                if device.changed:
                    message: dict = asdict(device.message)
                    logger.info(f"""[MQTT][{device.topic}] Publishing message: {message}""")
                    await client.publish(device.topic, json.dumps(message), qos=1)

            await asyncio.sleep(250e-3)

    async def _init_tasks(self) -> None:
        async with AsyncExitStack() as stack:
            self._tasks = set()

            stack.push_async_callback(self.cancel_tasks)

            mqtt_client = MqttClient(
                config.mqtt.host,
                config.mqtt.port,
                client_id=self._mqtt_client_id,
                keepalive=config.mqtt.keepalive,
            )

            await stack.enter_async_context(mqtt_client)
            self._retry_reconnect = 0

            logger.info(f"""[MQTT] Connected to broker at `{config.mqtt.host}:{config.mqtt.port}`""")

            for device in devices.by_name(["RO", "DO"]):
                topic: str = f"""{device.topic}/set"""

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

        tasks = [t for t in asyncio.all_tasks() if t is not (t.done() or asyncio.current_task())]
        [task.cancel() for task in tasks]

        logger.info(f"Cancelling {len(tasks)} outstanding tasks.")

        await asyncio.gather(*tasks)

    async def run(self) -> None:
        await self.neuron.initialise_cache()
        await self.neuron.read_boards()

        reconnect_interval: int = config.mqtt.reconnect_interval
        retry_limit: Optional[int] = config.mqtt.retry_limit

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

    loop = asyncio.new_event_loop()
    loop.set_debug(args.debug)

    modbus = Modbus(loop)
    umc = UnipiMqttClient(loop, modbus)

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)

    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(umc.shutdown(loop, s))
        )

    try:
        loop.run_until_complete(umc.run())
    except ModbusException as error:
        logger.error(f"[MODBUS] {error}")
    finally:
        loop.close()
        logger.info("Successfully shutdown the Unipi MQTT Client service.")


if __name__ == "__main__":
    main()
