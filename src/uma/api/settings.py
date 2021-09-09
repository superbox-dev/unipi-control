import logging
import os

from systemd import journal
import yaml


def get_config() -> dict:
    default_config: dict = {
        "device_name": "unipi",
        "sysfs": {
            "devices": "/sys/bus/platform/devices",
        },
        "mqtt": {
            "host": "localhost",
            "port": 1883,
        },
        "logger": "systemd",
        "homeassistant": {
            "discovery_prefix": "homeassistant",
            "device": {
                "name": "Unipi",
                "manufacturer": "Unipi",
            }
        },
    }

    path: str = "/etc/default/uma"

    if os.path.exists(path):
        with open(path, "r") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            # TODO: add recusive merge!
            default_config.update(**config)

    return default_config


CONFIG = get_config()

with open(f"""{CONFIG["sysfs"]["devices"]}/unipi_plc/model_name""", "r") as f:
    CONFIG["homeassistant"]["device"]["model"] = f.read().rstrip()

logger_type: str = CONFIG["logger"]
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
