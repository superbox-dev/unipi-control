from helpers import MutableMappingMixin


class DeviceMap(MutableMappingMixin):
    def register(self, dev_type, device):
        if not self.mapping.get(dev_type):
            self.mapping[dev_type] = []

        self.mapping[dev_type].append(device)


devices = DeviceMap()
