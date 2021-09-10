import logging
import os

from deepmerge import always_merger
from systemd import journal
import yaml

api_config: dict = {
    "device_name": "unipi",
    "sysfs": {
        "devices": "/sys/bus/platform/devices",
    },
    "mqtt": {
        "host": "localhost",
        "port": 1883,
    },
    "logger": "systemd",
}

ha_config: dict = {
    "discovery_prefix": "homeassistant",
    "device": {
        "name": "Unipi",
        "manufacturer": "Unipi technology",
    },
}


def get_config(config: dict, path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r") as f:
            custom_config = yaml.load(f, Loader=yaml.FullLoader)
            result = always_merger.merge(config, custom_config)

    return result


API = get_config(api_config, "/etc/uma/api.yaml")
HA = get_config(ha_config, "/etc/uma/ha.yaml")

with open(f"""{API["sysfs"]["devices"]}/unipi_plc/model_name""", "r") as f:
    HA["device"]["model"] = f.read().rstrip()

logger_type: str = API["logger"]
logger = logging.getLogger(__name__)

if logger_type == "systemd":
    logger.addHandler(journal.JournalHandler())
    logger.setLevel(level=logging.DEBUG)
elif logger_type == "file":
    logging.basicConfig(
        level=logging.DEBUG,
        filename="/var/log/unipi.log",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
