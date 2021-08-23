#!/usr/bin/env python3

import argparse

from helpers import (
    ConfigMixin,
    logger,
    VerboseMixin
)
from mqtt import Mqtt


class ReceiverMqtt(Mqtt):
    def on_message(self, client, userdata, message) -> None:
        super().on_message(client, userdata, message)
        print(message, message.payload, type(message.payload), message.payload.decode(), type(message.payload.decode()))
        print(self.config)


class Controller(ConfigMixin):
    def __init__(self, args):
        self._verbose = args.verbose
        
        mqtt = ReceiverMqtt(client_id="unipi-controller", verbose=args.verbose)
        self.mqttc = mqtt.run()
        self.mqttc.connect(self.config["mqtt"]["host"], self.config["mqtt"]["port"])

    def listen(self):
        self.mqttc.subscribe(self.topics)
        self.mqttc.loop_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    controller = Controller(args=args)

    try:
        controller.listen()
    except KeyboardInterrupt:
        logger.info("Process interrupted")
    except Exception as e:
        print(e)
