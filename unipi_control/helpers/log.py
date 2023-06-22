"""Collection of logging helpers."""

import logging
from collections import OrderedDict
from logging import StreamHandler
from typing import Dict, ClassVar
from typing import Final

LOG_NAME: Final[str] = "unipi-control"
LOG_MQTT_PUBLISH: Final[str] = "[MQTT] [%s] Publishing message: %s"
LOG_MQTT_SUBSCRIBE: Final[str] = "[MQTT] [%s] Subscribe message: %s"
LOG_MQTT_SUBSCRIBE_TOPIC: Final[str] = "[MQTT] Subscribe topic %s"

SIMPLE_LOG_FORMAT: Final[str] = "%(message)s"
LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)s | %(message)s"

LOG_LEVEL: Final[Dict[str, int]] = OrderedDict(
    {
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
    }
)


class SystemdHandler(StreamHandler):
    """Systemd handler with logging prefix for submit log level to journalcl."""

    # https://www.freedesktop.org/software/systemd/man/sd-daemon.html
    PREFIX: ClassVar[Dict[int, str]] = {
        logging.CRITICAL: "<2>",
        logging.ERROR: "<3>",
        logging.WARNING: "<4>",
        logging.INFO: "<6>",
        logging.DEBUG: "<7>",
    }

    def emit(self, record: logging.LogRecord) -> None:
        """Modify a record and add logging prefix."""
        msg: str = self.format(record)
        prefix: str = self.PREFIX.get(record.levelno, "<6>")
        self.stream.write(f"{prefix}{msg}{self.terminator}")
        self.flush()
