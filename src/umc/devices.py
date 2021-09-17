from helpers import MutableMappingMixin


RELAY = 0
INPUT = 1


class DeviceMap(MutableMappingMixin):
    def register(self, dev_type, device):
        # topic: str = f"""{CLIENT["device_name"]}/{device.dev}/{device.dev_type}/{device.circuit}"""
        if not self.mapping.get(dev_type):
            self.mapping[dev_type] = []

        self.mapping[dev_type].append(device)


devices = DeviceMap()
