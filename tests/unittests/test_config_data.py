from typing import Final

CONFIG_INVALID_DEVICE_NAME: Final[
    str
] = """device_name: Invalid Device Name
mqtt:
  host: localhost
  port: 1883
  connection:
    keepalive: 15
    retry_limit: 30
    reconnect_interval: 10
homeassistant:
  enabled: true
  discovery_prefix: homeassistant
features:
  di_3_01:
    friendly_name: MOCKED_FRIENDLY_NAME - 3_01
    suggested_area: MOCKED AREA 1
  di_3_02:
    friendly_name: MOCKED_FRIENDLY_NAME - 3_02
    suggested_area: MOCKED AREA 1
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    cover_type: blind
    topic_name: mocked_blind_topic_name
    cover_run_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_3_01
    circuit_down: ro_3_02
  - friendly_name: MOCKED_FRIENDLY_NAME - ROLLER SHUTTER
    suggested_area: MOCKED AREA
    cover_type: roller_shutter
    topic_name: mocked_roller_shutter_topic_name
    circuit_up: ro_3_03
    circuit_down: ro_3_04
logging:
  level: debug"""
