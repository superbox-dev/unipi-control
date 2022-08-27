from typing import Final

CONFIG_CONTENT: Final[
    str
] = """device_name: MOCKED_UNIPI
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
  di_1_01:
    friendly_name: MOCKED_FRIENDLY_NAME - 1_01
    suggested_area: MOCKED AREA 1
  di_1_02:
    friendly_name: MOCKED_FRIENDLY_NAME - 1_02
    suggested_area: MOCKED AREA 1
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    cover_type: blind
    topic_name: mocked_topic_name
    cover_run_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_1_01
    circuit_down: ro_1_02
logging:
  level: debug
"""
