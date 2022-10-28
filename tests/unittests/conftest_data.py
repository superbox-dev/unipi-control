from typing import Final
from typing import List
from unittest.mock import PropertyMock

CONFIG_CONTENT: Final[
    str
] = """device_info:
  name: MOCKED_UNIPI
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
  di_1_01:
    id: MOCKED_ID_DI_1_01
    friendly_name: MOCKED_FRIENDLY_NAME - DI_1_01
    suggested_area: MOCKED AREA 1
    invert_state: True
  di_1_02:
    id: MOCKED_ID_DI_1_02
    friendly_name: MOCKED_FRIENDLY_NAME - DI_1_02
    suggested_area: MOCKED AREA 2
  di_3_01:
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_01
    suggested_area: MOCKED AREA 1
  di_3_02:
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_02
    suggested_area: MOCKED AREA 1
  ro_2_01:
    id: MOCKED_ID_RO_2_01
    friendly_name: MOCKED_FRIENDLY_NAME - RO_2_01
    suggested_area: MOCKED AREA 2
    invert_state: True
  ro_2_02:
    id: MOCKED_ID_RO_2_02
    friendly_name: MOCKED_FRIENDLY_NAME - RO_2_02
    suggested_area: MOCKED AREA 2
covers:
  - id: MOCKED_ID_COVER_BLIND
    friendly_name: MOCKED_FRIENDLY_NAME - BLIND
    cover_type: blind
    topic_name: MOCKED_BLIND_TOPIC_NAME
    cover_run_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_3_01
    circuit_down: ro_3_02
  - friendly_name: MOCKED_FRIENDLY_NAME - ROLLER SHUTTER
    suggested_area: MOCKED AREA
    cover_type: roller_shutter
    topic_name: MOCKED_ROLLER_SHUTTER_TOPIC_NAME
    circuit_up: ro_3_03
    circuit_down: ro_3_04
modbus:
  - id: MOCKED_EASTRON_SDM120
    device:
      manufacturer: Eastron
      model: eastron_SDM120M.yaml
    address: 1
    baud_rate: 2400
    parity: N
    friendly_name: MOCKED EASTRON eastron_SDM120M.yaml
    suggested_area: MOCKED AREA
logging:
  level: debug
"""

HARDWARE_DATA_CONTENT: Final[
    str
] = """type: L203
modbus_register_blocks:
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
  - type: DO
    count: 4
    major_group: 1
    val_reg: 1
    val_coil: 0
  - type: DI
    count: 4
    major_group: 1
    val_reg: 0
  - type: LED
    major_group: 1
    count: 4
    val_coil: 8
    val_reg: 20
  - type: DI
    count: 16
    major_group: 2
    val_reg: 100
  - type: RO
    major_group: 2
    count: 14
    val_reg: 101
    val_coil: 100
  - type: DI
    count: 16
    major_group: 3
    val_reg: 200
  - type: RO
    major_group: 3
    count: 14
    val_reg: 201
    val_coil: 200
"""

THIRD_PARTY_HARDWARE_DATA_CONTENT: Final[
    str
] = """type: SDM120M
modbus_register_blocks:
    # Voltage
  - start_reg: 0
    count: 2
    unit: 1
    # Current
  - start_reg: 6
    count: 2
    unit: 1
    # Power (Active)
  - start_reg: 12
    count: 2
    unit: 1
    # Power (Apparent)
  - start_reg: 18
    count: 2
    unit: 1
    # Power (Reactive)
  - start_reg: 24
    count: 2
    unit: 1
    # Power factor
  - start_reg: 30
    count: 2
    unit: 1
    # Phase Angle
  - start_reg: 36
    count: 2
    unit: 1
    # Frequency
    # Imported Energy (Active)
    # Exported Energy (Active)
    # Imported Energy (Reactive)
    # Exported Energy (Reactive)
  - start_reg: 70
    count: 10
    unit: 1
    # Total Demand Power (Active)
    # Maximum Total Demand Power (Active)
    # Import Demand Power (Active)
    # Maximum Import Demand Power (Active)
  - start_reg: 84
    count: 8
    unit: 1
    # Export Demand Power (Active)
    # Maximum Export Demand Power (Active)
  - start_reg: 92
    count: 4
    unit: 1
    # Total Demand Current
  - start_reg: 258
    count: 2
    unit: 1
    # Maximum Total Demand Current
  - start_reg: 264
    count: 2
    unit: 1
    # Total Energy (Reactive)
    # Total Energy (Reactive)
  - start_reg: 342
    count: 4
    unit: 1
"""

MODBUS_FEATURE_ENABLED: Final[int] = 1

MODBUS_REGISTER: Final[List] = [
    # L203
    PropertyMock(registers=[0, 12]),  # DI 1.x / DO 1.x
    PropertyMock(registers=[0]),  # LED 1.x
    PropertyMock(registers=[16384, 10240]),  # DI 2.x / RO 2.x
    PropertyMock(registers=[24576, 8192]),  # DI 3.x / RO 3.x
    # SDM120M
    PropertyMock(registers=[17259, 13107]),  # Voltage
    PropertyMock(registers=[16018, 28312]),  # Current
    PropertyMock(registers=[16918, 52429]),  # Power (Active)
    PropertyMock(registers=[16932, 32072]),  # Power (Apparent)
    PropertyMock(registers=[49538, 26214]),  # Power (Reactive)
    PropertyMock(registers=[16234, 55535]),  # Power factor
    PropertyMock(registers=[0, 0]),  # Phase Angle
    PropertyMock(
        registers=[16968, 10486, 16525, 20447, 0, 0, 16023, 36176, 16431, 11010]
    ),  # Frequency, Imported Energy (Active), Exported Energy (Active), Imported Energy (Reactive), Exported Energy (Reactive)
    PropertyMock(
        registers=[16917, 5097, 17058, 5854, 16917, 5097, 17058, 5854]
    ),  # Total Demand Power (Active), Maximum Total Demand Power (Active), Import Demand Power (Active), Maximum Import Demand Power (Active)
    PropertyMock(registers=[0, 0, 15609, 56093]),  # Export Demand Power (Active), Maximum Export Demand Power (Active)
    PropertyMock(registers=[16020, 2247]),  # Total Demand Current
    PropertyMock(registers=[16182, 44756]),  # Maximum Total Demand Current
    PropertyMock(registers=[16525, 20447, 16450, 7340]),  # Total Energy (Reactive), Total Energy (Reactive)
]
