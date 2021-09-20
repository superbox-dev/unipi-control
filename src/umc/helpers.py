import fcntl
import socket
import struct
from collections.abc import Mapping
from collections.abc import MutableMapping


class MappingMixin(Mapping):
    def __init__(self):
        self.mapping: dict = {}

    def __getitem__(self, key):
        return self.mapping[key]

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self._mapping)

    def __repr__(self):
        return f"{type(self).__name__}({self.mapping})"


class MutableMappingMixin(MutableMapping):
    def __init__(self):
        self.mapping: dict = {}

    def __getitem__(self, key):
        return self.mapping[key]

    def __delitem__(self, key):
        value = self[key]
        del self.mapping[key]
        self.pop(value, None)

    def __setitem__(self, key, value):
        if key in self:
            del self[self[key]]

        if value in self:
            del self[value]

        self.mapping[key] = value
        self.mapping[value] = key

    def __iter__(self):
        return iter(self.mapping)

    def __len__(self):
        return len(self._mapping)

    def __repr__(self):
        return f"{type(self).__name__}({self.mapping})"


def get_hw_addr(ifname: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack("256s", bytes(ifname, "utf-8")[:15]))
    return ":".join("%02x" % b for b in info[18:24])


def _get_device_connections() -> list:
    connections: list = []

    for key, interface in socket.if_nameindex():
        hw_addr: str = get_hw_addr(interface)

        if hw_addr != "00:00:00:00:00:00":
            connections.append(["mac", hw_addr])
            break

    return connections
