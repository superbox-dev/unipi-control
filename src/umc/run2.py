#!/usr/bin/env python3
import argparse
import asyncio

from api.settings import logger
from devices import devices
from neuron import Neuron
from pymodbus.client.asynchronous import schedulers
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusClient


class UnipiMqttClient:
    def __init__(self, modbus_client, debug: bool):
        self.debug: bool = debug
        self.neuron = Neuron(modbus_client)

    async def run(self) -> None:
        await self.neuron.initialise_cache()
        await self.neuron.read_boards()

        devs = devices.by_name(["RO", "DO", "LED"])

        while True:
            await self.neuron.start_scanning()
            results: list = await asyncio.gather(*(dev.get_state() for dev in devs))

            for device in results:
                if device.changed:
                    print(device)

            await asyncio.sleep(250e-3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, type=bool, help="Debug")
    args = parser.parse_args()

    try:
        loop, modbus_client = ModbusClient(schedulers.ASYNC_IO, port=502)

        loop.run_until_complete(
            UnipiMqttClient(
                modbus_client.protocol,
                debug=args.debug
            ).run()
        )
    except KeyboardInterrupt:
        logger.info("Process interrupted")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
