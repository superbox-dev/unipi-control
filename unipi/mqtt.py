from typing import Optional

import paho.mqtt.client as mqtt

from config import Config
from log import VerboseMixin


class Mqtt(Config, VerboseMixin):
    def __init__(self, client_id: Optional[str] = None, run_async: bool = False, host: str = "localhost", port: int = 1883, verbose: bool = False):
        self.client_id = client_id
        self.host = self.config["mqtt"].get("host", host)
        self.port = self.config["mqtt"].get("port", port)
        self._verbose = verbose
        self._run_async = run_async

    @property
    def topics(self) -> list:
        return [(f"unipi/{value}", 0) for key, value in self.config["observe"].items()]

    def run(self):
        self.client = mqtt.Client(client_id=self.client_id)

        # self.client.on_publish = self.on_publish
        # self.client.on_subscribe = self.on_subscribe
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        if self._run_async:
            self.client.connect_async(self.host, self.port)
            self.client.loop_start()
        else:
            self.client.connect(self.host, self.port)

        return self.client

    def on_publish(self, client, userdata, mid) -> None:
        self.show_msg(f"Message ID: {mid}")

    def on_subscribe(self, client, userdata, mid, granted_qos) -> None:
        self.show_msg(f"Granted QOS: {granted_qos}, Message ID: {mid}")

    def on_message(self, client, userdata, message) -> None:
        self.show_msg(f"Received `{message.payload.decode()}` from `{message.topic}` topic")

        if message.retain == 1:
            self.show_msg("This is a retained message")

    def on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            msg = f"Connected to MQTT Broker at `{self.host}:{self.port}`"
        else:
            msg = f"Failed to connect, return code `{rc}`"

        self.show_msg(msg)

    def on_disconnect(self, client, userdata, rc=0) -> None:
        if self._run_async:
            self.client.loop_stop()

        self.show_msg(f"Disconnected result code `{rc}`")
