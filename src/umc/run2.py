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
        self.modbus_client = modbus_client
        self.debug: bool = debug

    async def run(self) -> None:
        await Neuron(self.modbus_client).read_boards()

        print(devices)

        while True:
            print("test")
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
