"""Collection of feature classes."""

from enum import Enum
from typing import Final
from typing import Tuple


class FeatureState:
    ON: str = "ON"
    OFF: str = "OFF"


class FeatureType(Enum):
    DI: Final[Tuple[str, str, str]] = ("DI", "input", "Digital Input")
    DO: Final[Tuple[str, str, str]] = ("DO", "relay", "Digital Output")
    LED: Final[Tuple[str, str, str]] = ("LED", "led", "LED")
    RO: Final[Tuple[str, str, str]] = ("RO", "relay", "Relay")
    METER: Final[Tuple[str, str, str]] = ("METER", "meter", "Meter")

    def __init__(self, short_name: str, topic_name: str, long_name: str) -> None:
        self.short_name: str = short_name
        self.topic_name: str = topic_name
        self.long_name: str = long_name
