import itertools
from typing import Union

from mapping import MutableMappingMixin


class DeviceMap(MutableMappingMixin):
    def register(self, dev_type, device):
        if not self.mapping.get(dev_type):
            self.mapping[dev_type] = []

        self.mapping[dev_type].append(device)

    def by_name(self, dev_type: Union[str, list]) -> list:
        if isinstance(dev_type, str):
            return self.mapping[dev_type]
        elif isinstance(dev_type, list):
            return list(
                itertools.chain.from_iterable(
                    map(self.mapping.get, dev_type)
                )
            )


devices = DeviceMap()
