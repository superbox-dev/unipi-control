from typing import Final

CONFIG_INVALID_DEVICE_NAME: Final[
    str
] = """device_name: INVALID DEVICE NAME
logging:
  level: debug"""

CONFIG_INVALID_FEATURE_TYPE: Final[
    str
] = """device_name: MOCKED_UNIPI
features: INVALID
logging:
  level: debug"""

CONFIG_INVALID_HOMEASSISTANT_DISCOVERY_PREFIX: Final[
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
  discovery_prefix: INVALID DISCOVERY NAME
logging:
  level: debug"""

CONFIG_INVALID_FEATURE_PROPERTY: Final[
    str
] = """device_name: MOCKED_UNIPI
features:
  di_3_01:
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_01
    suggested_area: MOCKED AREA 1
    invalid_property: INVALID
logging:
  level: debug"""

CONFIG_INVALID_COVER_PROPERTY: Final[
    str
] = """device_name: MOCKED_UNIPI
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    cover_type: blind
    topic_name: MOCKED_BLIND_TOPIC_NAME
    cover_run_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_3_01
    circuit_down: ro_3_02
    invalid_property: INVALID
logging:
  level: debug"""


CONFIG_INVALID_COVER_TOPIC_NAME: Final[
    str
] = """device_name: MOCKED_UNIPI
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    cover_type: blind
    topic_name: INVALID TOPIC NAME
    cover_run_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_3_01
    circuit_down: ro_3_02
logging:
  level: debug"""

CONFIG_INVALID_COVER_TYPE: Final[
    str
] = """device_name: MOCKED_UNIPI
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    cover_type: INVALID
    topic_name: MOCKED_BLIND_TOPIC_NAME
    cover_run_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_3_01
    circuit_down: ro_3_02
logging:
  level: debug"""

CONFIG_MISSING_COVER_KEY: Final[
    str
] = """device_name: MOCKED_UNIPI
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    cover_type: blind
    cover_run_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_3_01
    circuit_down: ro_3_02
logging:
  level: debug"""

CONFIG_DUPLICATE_COVERS_CIRCUITS: Final[
    str
] = """device_name: MOCKED_UNIPI
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    cover_type: blind
    topic_name: MOCKED_BLIND_TOPIC_NAME
    cover_run_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_3_01
    circuit_down: ro_3_02
  - friendly_name: MOCKED_FRIENDLY_NAME - ROLLER SHUTTER
    cover_type: roller_shutter
    topic_name: MOCKED_ROLLER_SHUTTER_TOPIC_NAME
    circuit_up: ro_3_01
    circuit_down: ro_3_02
logging:
  level: debug"""
