from pymodbus.client.asynchronous import schedulers
from pymodbus.client.asynchronous.tcp import AsyncModbusTCPClient as ModbusClient


class ModbusException(Exception):
    def __str__(self):
        return "Can't connect to Modbus TCP!"


class Modbus:
    def __init__(self, loop):
        self.loop, self.modbus = ModbusClient(schedulers.ASYNC_IO, port=502, loop=loop)
        self.modbus_client = self.modbus.protocol

    async def write_coil(self, address, value, unit):
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        response = await self.modbus_client.write_coil(address, value, unit=unit)

        return response

    async def read_holding_registers(self, address, count, unit):
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        response = await self.modbus_client.read_holding_registers(address, count, unit=unit)

        return response

    async def read_input_registers(self, address, count, unit):
        if not self.modbus_client or not self.modbus_client.connected:
            raise ModbusException()

        response = await self.modbus_client.read_input_registers(address, count, unit=unit)

        return response


class ModbusCacheMap:
    def __init__(self, modbus_reg_map, neuron):
        self.modbus_reg_map = modbus_reg_map
        self.neuron = neuron
        self.registered: dict = {}
        self.registered_input: dict = {}

        for modbus_reg_group in modbus_reg_map:
            for index in range(modbus_reg_group["count"]):
                reg: int = modbus_reg_group["start_reg"] + index

                if modbus_reg_group.get("type") == "input":
                    self.registered_input[reg] = None
                else:
                    self.registered[reg] = None

    def get_register(self, count: int, index: int, unit=0, is_input=False) -> list:
        ret: list = []

        for counter in range(index, count + index):
            if is_input:
                if counter not in self.registered_input:
                    raise Exception(f"Unknown register {counter}")
                elif self.registered_input[counter] is None:
                    raise Exception(f"No cached value of register {counter} on unit {unit} - read error")

                ret += [self.registered_input[counter]]
            else:
                if counter not in self.registered:
                    raise Exception(f"Unknown register {counter}")
                elif self.registered[counter] is None:
                    raise Exception(f"No cached value of register {counter} on unit {unit} - read error")

                ret += [self.registered[counter]]

        return ret

    async def scan(self):
        for modbus_reg_group in self.modbus_reg_map:
            data: dict = {
                "address": modbus_reg_group["start_reg"],
                "count": modbus_reg_group["count"],
                "unit": 0,
            }

            if modbus_reg_group.get("type") == "input":
                val = await self.neuron.modbus.read_input_registers(**data)

                for index in range(modbus_reg_group["count"]):
                    self.registered_input[modbus_reg_group["start_reg"] + index] = val.registers[index]
            else:
                val = await self.neuron.modbus.read_holding_registers(**data)

                for index in range(modbus_reg_group["count"]):
                    self.registered[modbus_reg_group["start_reg"] + index] = val.registers[index]
