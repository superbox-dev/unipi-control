from enum import Enum
from typing import Final


class FeatureState:
    ON: str = "ON"
    OFF: str = "OFF"


class FeatureType(Enum):
    DI: Final[tuple] = ("DI", "input", "Digital Input")
    DO: Final[tuple] = ("DO", "relay", "Digital Output")
    LED: Final[tuple] = ("LED", "led", "LED")
    RO: Final[tuple] = ("RO", "relay", "Relay")
    METER: Final[tuple] = ("METER", "meter", "Meter")

    def __init__(self, short_name: str, topic_name: str, long_name: str) -> None:
        self.short_name: str = short_name
        self.topic_name: str = topic_name
        self.long_name: str = long_name
