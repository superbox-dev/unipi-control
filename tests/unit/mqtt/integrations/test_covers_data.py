"""Data for covers unit tests."""

from typing import Final

CONFIG_CONTENT: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
mqtt:
  host: localhost
  port: 1883
  connection:
    keepalive: 15
    retry_limit: 30
    reconnect_interval: 10
homeassistant:
  enabled: True
  discovery_prefix: homeassistant
features:
  ro_2_01:
    object_id: MOCKED_ID_RO_2_01
    friendly_name: MOCKED_FRIENDLY_NAME - RO_2_01
    suggested_area: MOCKED AREA 2
    invert_state: True
  ro_2_02:
    object_id: MOCKED_ID_RO_2_02
    friendly_name: MOCKED_FRIENDLY_NAME - RO_2_02
    suggested_area: MOCKED AREA 2
    icon: mdi:power-standby
    device_class: switch
covers:
  - object_id: MOCKED_BLIND_TOPIC_NAME
    friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    device_class: blind
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
logging:
  level: debug
"""
