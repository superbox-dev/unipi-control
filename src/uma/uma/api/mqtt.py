import _thread

import paho.mqtt.client as mqtt

from api.settings import (
    API,
    logger,
)


class MqttMixin:
    """Mqtt mixin for connecting to Mqtt broker."""

    def connect(self, client_id: str):
        """Connect to mqtt broker.

        Args:
            client_id (str): unique client id
        """
        client = mqtt.Client(client_id)
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message

        client.connect(API["mqtt"]["host"], API["mqtt"]["port"])
        client.loop_start()

        return client

    def on_connect(self, client, userdata, flags, rc: int) -> None:
        """Subscribe topics on connect to mqtt broker."""
        if rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Connected to MQTT Broker at `{client._host}:{client._port}`")
        else:
            logger.error(f"Failed to connect, return code `{rc}`")

    def on_disconnect(self, client, userdata, rc: int) -> None:
        """Stop loop on disconnect from mqtt broker."""
        logger.info(f"Disconnected result code `{rc}`")
        client.loop_stop()

    def on_message(self, client, userdata, message) -> None:
        """Execude subscribe callback in a new thread."""
        logger.debug(f"Received `{message.payload.decode()}` from topic `{message.topic}`")
        _thread.start_new_thread(self.on_message_thread, (message, ))
