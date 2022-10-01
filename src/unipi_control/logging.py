import logging
import sys
from collections import OrderedDict
from typing import Dict
from typing import Final

LOG_NAME: Final[str] = "unipi-control"
LOG_FMT: Final[str] = "{level} | {message}"
LOG_MQTT_PUBLISH: Final[str] = "[MQTT] [%s] Publishing message: %s"
LOG_MQTT_SUBSCRIBE: Final[str] = "[MQTT] [%s] Subscribe message: %s"
LOG_MQTT_SUBSCRIBE_TOPIC: Final[str] = "[MQTT] Subscribe topic %s"

LOG_LEVEL: Final[Dict[str, int]] = OrderedDict(
    {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
)

stream_handler = logging.StreamHandler(stream=sys.stderr)
stream_handler.setFormatter(logging.Formatter(fmt="%(levelname)s | %(message)s"))


def init_logger(name: str, level: str, handlers: list) -> logging.Logger:
    logger: logging.Logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL[level.lower()])

    for handler in handlers:
        logger.addHandler(handler)

    return logger
