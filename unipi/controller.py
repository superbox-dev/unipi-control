#!/usr/bin/env python3

import argparse

from mqtt import Mqtt


class ReceiverMqtt(Mqtt):
    def on_message(self, client, userdata, message) -> None:
        super().on_message(client, userdata, message)
        print(message, message.payload, type(message.payload), message.payload.decode(), type(message.payload.decode()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    mqtt = ReceiverMqtt(client_id="unipi-controller", run_async=False, verbose=args.verbose)

    mqttc = mqtt.run()
    mqttc.subscribe(mqtt.topics)
    mqttc.loop_forever()
