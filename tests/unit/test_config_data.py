"""Data for config unit tests."""

from typing import Final

CONFIG_LOGGING_LEVEL_INFO: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
logging:
  level: info
"""

CONFIG_LOGGING_LEVEL_ERROR: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
logging:
  level: error
"""

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

CONFIG_INVALID_COVER_TYPE: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
covers: INVALID
logging:
  level: debug"""

CONFIG_INVALID_MQTT_PORT_TYPE: Final[
    str
] = """device_info:
  name: MOCKED UNIPI
mqtt:
  host: localhost
  port: INVALID
  connection:
    keepalive: 15
    retry_limit: 30
    reconnect_interval: 10"""

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
  - object_id: MOCKED_FRIENDLY_NAME - BLIND
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
  - object_id: INVALID ID
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
  - object_id: MOCKED_BLIND_TOPIC_NAME
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
  - object_id: MOCKED_BLIND_TOPIC_NAME
    friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    device_class: blind
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
  - object_id: MOCKED_ROLLER_SHUTTER_TOPIC_NAME
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
  - object_id: MOCKED_DUPLICATE_ID
    friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    device_class: blind
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_01
    cover_down: ro_3_02
  - object_id: MOCKED_DUPLICATE_ID
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
      device_name: MOCKED Eastron SDM120M
      identifier: Eastron_SDM120M
    - unit: 1
      device_name: MOCKED Eastron SDM120M
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


HARDWARE_DATA_INVALID_KEY: Final[
    str
] = """modbus_register_block:
    # DI 1.x / DO 1.x
  - start_reg: 0
    count: 2
    # LED 1.x
  - start_reg: 20
    count: 1
    # DI 2.x / RO 2.x
  - start_reg: 100
    count: 2
    # DI 3.x / RO 3.x
  - start_reg: 200
    count: 2
modbus_features:
  - feature_type: DI
    count: 4
    major_group: 1
    val_reg: 0
  - feature_type: DO
    count: 4
    major_group: 1
    val_reg: 1
    val_coil: 0
  - feature_type: LED
    major_group: 1
    count: 4
    val_coil: 8
    val_reg: 20
  - feature_type: DI
    count: 16
    major_group: 2
    val_reg: 100
  - feature_type: RO
    major_group: 2
    count: 14
    val_reg: 101
    val_coil: 100
  - feature_type: DI
    count: 16
    major_group: 3
    val_reg: 200
  - feature_type: RO
    major_group: 3
    count: 14
    val_reg: 201
    val_coil: 200
"""

HARDWARE_DATA_IS_LIST: Final[
    str
] = """- start_reg: 0
  count: 2
- start_reg: 20
  count: 1
- start_reg: 100
  count: 2
- start_reg: 200
  count: 2
"""

HARDWARE_DATA_IS_INVALID_YAML: Final[str] = """modbus_features: INVALID:"""

EXTENSION_HARDWARE_DATA_INVALID_KEY: Final[
    str
] = """manufacturer: Eastron
model: SDM120M
modbus_register_block:
  # Voltage
  - start_reg: 0
    count: 2
modbus_features:
  - feature_type: METER
    friendly_name: Voltage
    device_class: voltage
    state_class: measurement
    unit_of_measurement: V
    val_reg: 0
    count: 2
"""

EXTENSION_HARDWARE_DATA_IS_LIST: Final[
    str
] = """- start_reg: 0
  count: 2
"""

EXTENSION_HARDWARE_DATA_IS_INVALID_YAML: Final[str] = """manufacturer: INVALID:"""
