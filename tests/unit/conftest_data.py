"""Data for pytest fixtures configuration."""

from typing import Final
from typing import List
from unittest.mock import MagicMock

from pymodbus.pdu import ModbusResponse

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
modbus:
  baud_rate: 2400
  parity: N
  units:
    - unit: 1
      device_name: MOCKED Eastron SDM120M
      identifier: MOCKED_EASTRON
      suggested_area: Workspace
homeassistant:
  enabled: True
  discovery_prefix: homeassistant
features:
  di_1_01:
    object_id: MOCKED_ID_DI_1_01
    friendly_name: MOCKED_FRIENDLY_NAME - DI_1_01
    invert_state: True
    icon: mdi:power-standby
  di_1_02:
    object_id: MOCKED_ID_DI_1_02
    friendly_name: MOCKED_FRIENDLY_NAME - DI_1_02
    suggested_area: MOCKED AREA 2
    device_class: heat
  di_3_01:
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_01
    suggested_area: MOCKED AREA 1
  di_3_02:
    friendly_name: MOCKED_FRIENDLY_NAME - DI_3_02
    suggested_area: MOCKED AREA 1
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
  apparent_power_1:
    object_id: MOCKED_ID_APPARENT_POWER
    friendly_name: MOCKED_FRIENDLY_NAME - APPARENT_POWER
    suggested_area: MOCKED AREA 3
    icon: mdi:power-standby
  reactive_power_1:
    device_class: power
    state_class: total
    unit_of_measurement: W
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
    suggested_area: MOCKED AREA
    device_class: roller_shutter
    cover_up: ro_3_03
    cover_down: ro_3_04
logging:
  level: debug
"""

HARDWARE_DATA_CONTENT: Final[
    str
] = """modbus_register_blocks:
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

EXTENSION_HARDWARE_DATA_CONTENT: Final[
    str
] = """manufacturer: Eastron
model: SDM120M
modbus_register_blocks:
  # Voltage
  - start_reg: 0
    count: 2
  # Current
  - start_reg: 6
    count: 2
  # Active Power
  - start_reg: 12
    count: 2
  # Apparent Power
  - start_reg: 18
    count: 2
  # Reactive Power
  - start_reg: 24
    count: 2
  # Power Factor
  - start_reg: 30
    count: 2
  # Phase Angle
  - start_reg: 36
    count: 2
  # Frequency
  # Import Active Energy
  # Export Active Energy
  # Import Reactive Energy
  # Export Reactive Energy
  - start_reg: 70
    count: 10
  # Total System Power Demand
  # Maximum Total System Power Demand
  # Import System Power Demand
  # Maximum Import System Power Demand
  - start_reg: 84
    count: 8
  # Export System Power Demand
  # Maximum Export System Power Demand
  - start_reg: 92
    count: 4
    # Current Demand
  - start_reg: 258
    count: 2
  # Maximum Current Demand
  - start_reg: 264
    count: 2
  # Total Active Energy
  # Total Reactive Energy
  - start_reg: 342
    count: 4
modbus_features:
  - feature_type: METER
    friendly_name: Voltage
    device_class: voltage
    state_class: measurement
    unit_of_measurement: V
    val_reg: 0
    count: 2
  - feature_type: METER
    friendly_name: Current
    device_class: current
    state_class: measurement
    unit_of_measurement: A
    val_reg: 6
    count: 2
  - feature_type: METER
    friendly_name: Active Power
    device_class: power
    state_class: measurement
    unit_of_measurement: W
    val_reg: 12
    count: 2
  - feature_type: METER
    friendly_name: Apparent Power
    device_class: apparent_power
    state_class: measurement
    unit_of_measurement: VA
    val_reg: 18
    count: 2
  - feature_type: METER
    friendly_name: Reactive Power
    device_class: reactive_power
    state_class: measurement
    unit_of_measurement: var
    val_reg: 24
    count: 2
  - feature_type: METER
    friendly_name: Power Factor
    device_class: power_factor
    state_class: measurement
    val_reg: 30
    count: 2
  - feature_type: METER
    friendly_name: Phase Angle
    state_class: measurement
    val_reg: 36
    count: 2
  - feature_type: METER
    friendly_name: Frequency
    device_class: frequency
    state_class: measurement
    unit_of_measurement: Hz
    val_reg: 70
    count: 2
  - feature_type: METER
    friendly_name: Import Active Energy
    device_class: energy
    state_class: total
    unit_of_measurement: kWh
    val_reg: 72
    count: 2
  - feature_type: METER
    friendly_name: Export Active Energy
    device_class: energy
    state_class: measurement
    unit_of_measurement: kWh
    val_reg: 74
    count: 2
  - feature_type: METER
    friendly_name: Import Reactive Energy
    state_class: total
    unit_of_measurement: kvarh
    val_reg: 76
    count: 2
  - feature_type: METER
    friendly_name: Export Reactive Energy
    state_class: total
    unit_of_measurement: kvarh
    val_reg: 78
    count: 2
  - feature_type: METER
    friendly_name: Total System Power Demand
    device_class: power
    state_class: measurement
    unit_of_measurement: W
    val_reg: 84
    count: 2
  - feature_type: METER
    friendly_name: Maximum Total System Power Demand
    device_class: power
    state_class: total
    unit_of_measurement: W
    val_reg: 86
    count: 2
  - feature_type: METER
    friendly_name: Import System Power Demand
    device_class: power
    state_class: measurement
    unit_of_measurement: W
    val_reg: 88
    count: 2
  - feature_type: METER
    friendly_name: Maximum Import System Power Demand
    device_class: power
    state_class: measurement
    unit_of_measurement: W
    val_reg: 90
    count: 2
  - feature_type: METER
    friendly_name: Export System Power Demand
    device_class: power
    state_class: measurement
    unit_of_measurement: W
    val_reg: 92
    count: 2
  - feature_type: METER
    friendly_name: Maximum Export System Power Demand
    device_class: power
    state_class: measurement
    unit_of_measurement: W
    val_reg: 94
    count: 2
  - feature_type: METER
    friendly_name: Current Demand
    device_class: current
    state_class: measurement
    unit_of_measurement: A
    val_reg: 258
    count: 2
  - feature_type: METER
    friendly_name: Maximum Current Demand
    device_class: current
    state_class: measurement
    unit_of_measurement: A
    val_reg: 264
    count: 2
  - feature_type: METER
    friendly_name: Total Active Energy
    device_class: energy
    state_class: total
    unit_of_measurement: kWh
    val_reg: 342
    count: 2
  - feature_type: METER
    friendly_name: Total Reactive Energy
    state_class: total
    unit_of_measurement: kvarh
    val_reg: 344
    count: 2
"""

MODBUS_FEATURE_ENABLED: Final[int] = 1

NEURON_L203_MODBUS_REGISTER: Final[List[MagicMock]] = [
    # DI 1.x / DO 1.x
    MagicMock(spec=ModbusResponse, registers=[0, 0]),
    # LED 1.x
    MagicMock(spec=ModbusResponse, registers=[0]),
    # DI 2.x / RO 2.x
    MagicMock(spec=ModbusResponse, registers=[16384, 10240]),
    # DI 3.x / RO 3.x
    MagicMock(spec=ModbusResponse, registers=[24576, 8192]),
]

EXTENSION_EASTRON_SDM120M_MODBUS_REGISTER: Final[List[MagicMock]] = [
    # Voltage
    MagicMock(spec=ModbusResponse, registers=[17259, 13107]),
    # Current
    MagicMock(spec=ModbusResponse, registers=[16018, 28312]),
    # Active power
    MagicMock(spec=ModbusResponse, registers=[16918, 52429]),
    # Apparent power
    MagicMock(spec=ModbusResponse, registers=[16932, 32072]),
    # Reactive power
    MagicMock(spec=ModbusResponse, registers=[49538, 26214]),
    # Power factor
    MagicMock(spec=ModbusResponse, registers=[16234, 55535]),
    # Phase Angle
    MagicMock(spec=ModbusResponse, registers=[0, 0]),
    # Frequency, Import active energy, Export active energy, Imported reactive energy, Exported reactive energy
    MagicMock(spec=ModbusResponse, registers=[16968, 10486, 16525, 20447, 0, 0, 16023, 36176, 16431, 11010]),
    # Total system power demand, Maximum total system power demand,
    # Import system power demand, Maximum import system power demand
    MagicMock(spec=ModbusResponse, registers=[16917, 5097, 17058, 5854, 16917, 5097, 17058, 5854]),
    # Export system power demand, Maximum export system power demand
    MagicMock(spec=ModbusResponse, registers=[0, 0, 15609, 56093]),
    # Current demand
    MagicMock(spec=ModbusResponse, registers=[16020, 2247]),
    # Maximum current demand
    MagicMock(spec=ModbusResponse, registers=[16182, 44756]),
    # Total active energy, Total reactive energy
    MagicMock(spec=ModbusResponse, registers=[16525, 20447, 16450, 7340]),
]
