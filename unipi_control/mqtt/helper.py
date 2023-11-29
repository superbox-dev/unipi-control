"""Modbus helper to connect, subcribe and publish to MQTT."""

import asyncio
import time
import uuid
from asyncio import Task
from typing import ClassVar
from typing import List
from typing import Optional
from typing import Set

from aiomqtt import MqttError

from unipi_control.config import Config
from unipi_control.config import LogPrefix
from unipi_control.config import UNIPI_LOGGER
from unipi_control.features.eastron import Eastron
from unipi_control.features.unipi import DigitalInput
from unipi_control.features.unipi import DigitalOutput
from unipi_control.features.unipi import Led
from unipi_control.features.unipi import Relay
from unipi_control.features.utils import FeatureType
from unipi_control.helpers.exception import UnexpectedError
from unipi_control.helpers.log import LOG_LEVEL
from unipi_control.helpers.log import LOG_MQTT_PUBLISH
from unipi_control.helpers.log import LOG_MQTT_SUBSCRIBE
from unipi_control.helpers.text import slugify
from unipi_control.integrations.covers import CoverMap
from unipi_control.mqtt.discovery.binary_sensors import HassBinarySensorsDiscovery
from unipi_control.mqtt.discovery.sensors import HassSensorsDiscovery
from unipi_control.mqtt.discovery.switches import HassSwitchesDiscovery
from unipi_control.devices.unipi import Unipi

from aiomqtt import Client as MqttClient

from unipi_control.mqtt.integrations.covers import CoversMqttHelper


class MqttHelper:
    PUBLISH_RUNNING: bool = True
    subscribe_feature_types: ClassVar[List[FeatureType]] = [FeatureType.DO, FeatureType.RO]
    fast_scan_publish_feature_types: ClassVar[List[FeatureType]] = [
        FeatureType.DI,
        FeatureType.DO,
        FeatureType.RO,
    ]
    slow_scan_publish_feature_types: ClassVar[List[FeatureType]] = [
        FeatureType.METER,
    ]

    fast_scan_invertal: ClassVar[float] = 1 / 50
    slow_scan_invertal: ClassVar[float] = 20

    def __init__(self, unipi: Unipi) -> None:
        self.config: Config = unipi.config
        self.unipi: Unipi = unipi

        self.publish_feature_types: List[FeatureType] = (
            self.fast_scan_publish_feature_types + self.slow_scan_publish_feature_types
        )

    async def run(self) -> None:
        """Connect/reconnect to MQTT and start publish/subscribe."""
        covers = CoverMap(self.config, self.unipi.features)
        covers.init()

        mqtt_client = MqttClient(
            self.config.mqtt.host,
            port=self.config.mqtt.port,
            username=self.config.mqtt.username,
            password=self.config.mqtt.password,
        )

        mqtt_client_id: str = f"{slugify(self.config.device_info.name)}-{uuid.uuid4()}"
        UNIPI_LOGGER.info("%s Client ID: %s", LogPrefix.MQTT, mqtt_client_id)

        reconnect_interval: int = self.config.mqtt.reconnect_interval
        retry_limit: Optional[int] = self.config.mqtt.retry_limit
        retry_reconnect: int = 0
        discovery_initialized: bool = False

        while True:
            start_time = time.time()
            tasks: Set[Task] = set()

            try:
                async with mqtt_client:
                    if self.config.homeassistant.enabled and not discovery_initialized:
                        UNIPI_LOGGER.info("%s Initialize Home Assistant discovery", LogPrefix.MQTT)
                        await self.discovery(client=mqtt_client)
                        discovery_initialized = True

                    tasks.add(asyncio.create_task(self.subscribe(client=mqtt_client)))
                    tasks.add(
                        asyncio.create_task(
                            self.publish(
                                client=mqtt_client,
                                feature_types=self.fast_scan_publish_feature_types,
                                scan_interval=self.fast_scan_invertal,
                            )
                        )
                    )
                    tasks.add(
                        asyncio.create_task(
                            self.publish(
                                client=mqtt_client,
                                feature_types=self.slow_scan_publish_feature_types,
                                scan_interval=self.slow_scan_invertal,
                            )
                        )
                    )

                    covers_mqtt_helper = CoversMqttHelper(
                        client=mqtt_client, covers=covers, scan_interval=self.fast_scan_invertal
                    )
                    await covers_mqtt_helper.init(tasks=tasks)

                    await asyncio.gather(*tasks)
            except MqttError as error:
                UNIPI_LOGGER.error(
                    "%s Error '%s'. Connecting attempt #%s. Reconnecting in %s seconds.",
                    LogPrefix.MQTT,
                    error,
                    retry_reconnect + 1,
                    reconnect_interval,
                )

                if retry_limit and retry_reconnect > retry_limit:
                    msg: str = "Shutdown, due to too many MQTT connection attempts."
                    raise UnexpectedError(msg) from error

                retry_reconnect += 1
                await asyncio.sleep(reconnect_interval)

            UNIPI_LOGGER.info("%s", time.time() - start_time)

    async def subscribe(self, client: MqttClient) -> None:
        """Subscribe feature topics to MQTT."""
        async with client.messages() as messages:
            await client.subscribe(f"{slugify(self.config.device_info.name)}/#")

            async for message in messages:
                for feature in self.unipi.features.by_feature_types(self.subscribe_feature_types):
                    topic: str = f"{feature.topic}/set"

                    if message.topic.matches(topic) and (payload := message.payload) and isinstance(payload, bytes):
                        value: str = payload.decode()

                        if isinstance(feature, (DigitalOutput, Relay)):
                            if value == "ON":
                                feature.set_state(True)
                            elif value == "OFF":
                                feature.set_state(False)

                            if (
                                value in {"ON", "OFF"}
                                and LOG_LEVEL[self.unipi.config.logging.mqtt.features_level] <= LOG_LEVEL["info"]
                            ):
                                UNIPI_LOGGER.log(
                                    level=LOG_LEVEL["info"],
                                    msg=LOG_MQTT_SUBSCRIBE % (topic, value),
                                )

        await asyncio.sleep(self.fast_scan_invertal)

    async def publish(self, client: MqttClient, feature_types: List[FeatureType], scan_interval: float) -> None:
        """Publish feature changes to MQTT."""
        while self.PUBLISH_RUNNING:
            for feature in self.unipi.features.by_feature_types(feature_types):
                if feature.changed:
                    topic: str = f"{feature.topic}/get"
                    await client.publish(topic=topic, payload=feature.payload, qos=1, retain=True)

                    if (
                        isinstance(feature, Eastron)
                        and LOG_LEVEL[self.unipi.config.logging.mqtt.meters_level] <= LOG_LEVEL["info"]
                    ) or (
                        isinstance(feature, (DigitalInput, DigitalOutput, Led, Relay))
                        and LOG_LEVEL[self.unipi.config.logging.mqtt.features_level] <= LOG_LEVEL["info"]
                    ):
                        UNIPI_LOGGER.log(
                            level=LOG_LEVEL["info"],
                            msg=LOG_MQTT_PUBLISH % (topic, feature.payload),
                        )

            await asyncio.sleep(scan_interval)

    async def discovery(self, client: MqttClient) -> None:
        """Publish MQTT Home Assistant discovery topics."""
        for feature in self.unipi.features.by_feature_types(self.publish_feature_types):
            if isinstance(feature, DigitalInput):
                await HassBinarySensorsDiscovery(unipi=self.unipi, client=client).publish(feature)
            elif isinstance(feature, Eastron):
                await HassSensorsDiscovery(unipi=self.unipi, client=client).publish(feature)
            elif isinstance(feature, (DigitalOutput, Relay)):
                await HassSwitchesDiscovery(unipi=self.unipi, client=client).publish(feature)
