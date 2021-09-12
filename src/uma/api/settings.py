import fcntl
import logging
import os
import socket
import struct

from deepmerge import always_merger
from systemd import journal
import yaml


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


def _get_config(config: dict, path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r") as f:
            custom_config = yaml.load(f, Loader=yaml.FullLoader)
            result = always_merger.merge(config, custom_config)

    return result


api_config: dict = {
    "device_name": "unipi",
    "sysfs": {
        "devices": "/sys/bus/platform/devices",
    },
    "mqtt": {
        "host": "localhost",
        "port": 1883,
        "connection": {
            "keepalive": 15,
            "retry_limit": 30,
            "retry_interval": 10,
        },
    },
    "logging": {
        "logger": "systemd",
        "level": "info",
    },
}

homeassistant_config: dict = {
    "discovery_prefix": "homeassistant",
    "device": {
        "connections": _get_device_connections(),
        "name": "Unipi",
        "manufacturer": "Unipi technology",
    },
}

API = _get_config(api_config, "/etc/uma/api.yaml")
HA = _get_config(homeassistant_config, "/etc/uma/homeassistant.yaml")

with open(f"""{API["sysfs"]["devices"]}/unipi_plc/model_name""", "r") as f:
    HA["device"]["model"] = f.read().rstrip()

logger_type: str = API["logging"]["logger"]
logger = logging.getLogger(__name__)

LEVEL: dict = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

if logger_type == "systemd":
    logger.addHandler(journal.JournalHandler())
    logger.setLevel(level=LEVEL[API["logging"]["level"]])
elif logger_type == "file":
    logging.basicConfig(
        level=LEVEL[API["logging"]["level"]],
        filename="/var/log/unipi.log",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
