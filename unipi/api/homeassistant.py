from api.settings import (
    HA,
    logger,
)


class HomeAssistant:
    """HomeAssistant class for discovery topics."""

    def __init__(self, client):
        self.client = client

    def on_message(self, message):
        logger.info(message)
    
    def subscribe(self) -> None:
        """Subscribe topics for discovery."""
        logger.info("Disovery")
        topic: str = f"""{HA["discovery_prefix"]}/switch/unipi/ro_1_01/config"""
        self.client.subscribe(topic, qos=1)
