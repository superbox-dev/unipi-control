import fcntl
import socket
import struct

from config import config


def get_hw_addr(ifname: str) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack("256s", bytes(ifname, "utf-8")[:15]))
    return ":".join("%02x" % b for b in info[18:24])


def get_device_connections() -> list:
    connections: list = []

    for key, interface in socket.if_nameindex():
        hw_addr: str = get_hw_addr(interface)

        if hw_addr != "00:00:00:00:00:00":
            connections.append(["mac", hw_addr])
            break

    return connections


def get_device_topic(device) -> str:
    topic: str = f"""{config["device_name"]}/{device.dev_name}"""

    if device.dev_type:
        topic += f"/{device.dev_type}"

    topic += f"/{device.circuit}"

    return topic
