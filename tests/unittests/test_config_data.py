from typing import Final

CONFIG_INVALID_DEVICE_NAME: Final[
    str
] = """device_info:
  name: INVALID DEVICE NAME$
logging:
  level: debug"""

CONFIG_INVALID_FEATURE_TYPE: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
features: INVALID
logging:
  level: debug"""

CONFIG_INVALID_HOMEASSISTANT_DISCOVERY_PREFIX: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
homeassistant:
  enabled: true
  discovery_prefix: INVALID DISCOVERY NAME
logging:
  level: debug"""

CONFIG_INVALID_FEATURE_PROPERTY: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
features:
  di_3_01:
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_01
    suggested_area: MOCKED AREA 1
    invalid_property: INVALID
logging:
  level: debug"""

CONFIG_INVALID_COVER_PROPERTY: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
covers:
  - id: MOCKED_FRIENDLY_NAME - BLIND
    device_class: blind
    topic_name: MOCKED_BLIND_TOPIC_NAME
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
    invalid_property: INVALID
logging:
  level: debug"""


CONFIG_INVALID_COVER_ID: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
covers:
  - id: INVALID ID
    friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    device_class: blind
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
logging:
  level: debug"""

CONFIG_INVALID_DEVICE_CLASS: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
covers:
  - id: MOCKED_BLIND_TOPIC_NAME
    friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    device_class: INVALID
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
logging:
  level: debug"""

CONFIG_MISSING_COVER_KEY: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    device_class: blind
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
logging:
  level: debug"""

CONFIG_DUPLICATE_COVERS_CIRCUITS: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
covers:
  - id: MOCKED_BLIND_TOPIC_NAME
    friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    device_class: blind
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
  - id: MOCKED_ROLLER_SHUTTER_TOPIC_NAME
    friendly_name: MOCKED_FRIENDLY_NAME - ROLLER SHUTTER
    device_class: roller_shutter
    cover_up: ro_3_01
    cover_down: ro_3_02
logging:
  level: debug"""

CONFIG_INVALID: Final[
    str
] = """device_info:
  name: MOCKED UNIPI:
logging:
  level: debug"""

CONFIG_INVALID_LOG_LEVEL: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
logging:
  level: invalid"""

CONFIG_DUPLICATE_COVER_ID: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
covers:
  - id: MOCKED_DUPLICATE_ID
    friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    device_class: blind
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
  - id: MOCKED_DUPLICATE_ID
    friendly_name: MOCKED_FRIENDLY_NAME - ROLLER SHUTTER
    device_class: roller_shutter
    cover_up: ro_3_03
    cover_down: ro_3_04
logging:
  level: debug"""

CONFIG_DUPLICATE_OBJECT_ID: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
features:
  di_3_01:
    object_id: MOCKED_DUPLICATE_ID
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_01
    suggested_area: MOCKED AREA 1
  di_3_02:
    object_id: MOCKED_DUPLICATE_ID
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_02
    suggested_area: MOCKED AREA 1
logging:
  level: debug"""

CONFIG_INVALID_FEATURE_ID: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
features:
  di_3_01:
    object_id: INVALID ID
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_01
    suggested_area: MOCKED AREA 1
logging:
  level: debug"""

CONFIG_INVALID_MODBUS_BAUD_RATE: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
modbus:
  baud_rate: 2401
  parity: N
logging:
  level: debug"""

CONFIG_INVALID_MODBUS_PARITY: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
modbus:
  baud_rate: 2400
  parity: S
logging:
  level: debug"""

CONFIG_DUPLICATE_MODBUS_UNIT: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
modbus:
  baud_rate: 2400
  units:
    - unit: 1
      device_name: Eastron SDM120M
      identifier: Eastron_SDM120M
    - unit: 1
      device_name: Eastron SDM120M
      identifier: Eastron_SDM120M
logging:
  level: debug"""

CONFIG_MISSING_DEVICE_NAME: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
modbus:
  baud_rate: 2400
  units:
    - unit: 1
      identifier: Eastron_SDM120M
logging:
  level: debug"""
