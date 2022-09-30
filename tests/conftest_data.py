from typing import Final
from typing import List
from unittest.mock import PropertyMock

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
    id: MOCKED_ID_DI_1_01
    friendly_name: MOCKED_FRIENDLY_NAME - DI_1_01
    suggested_area: MOCKED AREA 1
    invert_state: true
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
    invert_state: true
  ro_2_02:
    id: MOCKED_ID_RO_2_02
    friendly_name: MOCKED_FRIENDLY_NAME - RO_2_02
    suggested_area: MOCKED AREA 2
covers:
  - friendly_name: MOCKED_FRIENDLY_NAME - BLIND
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
logging:
  level: debug
"""

HARDWARE_DATA_CONTENT: Final[
    str
] = """---
type: L203
modbus_register_blocks:
    - board_index : 1
      start_reg   : 0
      count       : 2
      frequency   : 1
    - board_index : 1
      start_reg   : 2
      count       : 3
      frequency   : 10
    - board_index : 1
      start_reg   : 5
      count       : 16
      frequency   : 1
    - board_index : 1
      start_reg   : 1000
      count       : 32
      frequency   : 5
    - board_index : 2
      start_reg   : 100
      count       : 35
      frequency   : 1
    - board_index : 2
      start_reg   : 1100
      count       : 29
      frequency   : 5
    - board_index : 3
      start_reg   : 200
      count       : 35
      frequency   : 1
    - board_index : 3
      start_reg   : 1200
      count       : 29
      frequency   : 5
modbus_features:
    - type        : AO
      count       : 1
      major_group : 1
      modes       :
        - Voltage
        - Current
        - Resistance
      min_v       : 0
      max_v       : 10
      min_c       : 0
      max_c       : 0.020
      min_r       : 0
      max_r       : 2000
      val_reg     : 2
      res_val_reg : 4
      cal_reg     : 1024
      mode_reg    : 1019
    - type        : AI
      count       : 1
      major_group : 1
      modes       :
        - Voltage
        - Current
      tolerances  : brain
      min_v       : 0
      max_v       : 10
      min_c       : 0
      max_c       : 0.020
      val_reg     : 3
      cal_reg     : 1024
      mode_reg    : 1024
    - type        : DO
      count       : 4
      major_group : 1
      modes       :
        - Simple
        - PWM
      val_reg     : 1
      val_coil    : 0
      pwm_reg     : 16
      pwm_ps_reg  : 1017
      pwm_c_reg   : 1018
    - type        : DI
      count       : 4
      major_group : 1
      modes       :
        - Simple
        - DirectSwitch
      ds_modes    :
        - Simple
        - Inverted
        - Toggle
      min_v       : 5
      max_v       : 24
      val_reg     : 0
      counter_reg : 8
      direct_reg  : 1014
      deboun_reg  : 1010
      polar_reg   : 1015
      toggle_reg  : 1016
    - type        : UART
      major_group : 1
      parity_modes :
        - None
        - Odd
        - Even
      speed_modes :
        - 2400bps
        - 4800bps
        - 9600bps
        - 19200bps
        - 38400bps
        - 57600bps
        - 115200bps
      stopb_modes :
        - One
        - Two
      count       : 1
      conf_reg    : 1031
    - type        : LED
      major_group : 1
      count       : 4
      val_coil    : 8
      val_reg     : 20
    - type        : WD
      major_group : 1
      count       : 1
      val_reg     : 6
      timeout_reg : 1008
      nv_sav_coil : 1003
      reset_coil  : 1002
    - type        : REGISTER
      major_group : 1
      count       : 21
      start_reg   : 0
    - type        : REGISTER
      major_group : 1
      count       : 32
      start_reg   : 1000
    - type        : DI
      count       : 16
      major_group : 2
      modes       :
        - Simple
        - DirectSwitch
      ds_modes    :
        - Simple
        - Inverted
        - Toggle
      min_v       : 5
      max_v       : 24
      val_reg     : 100
      counter_reg : 103
      direct_reg  : 1126
      deboun_reg  : 1110
      polar_reg   : 1127
      toggle_reg  : 1128
    - type        : RO
      major_group : 2
      count       : 14
      val_reg     : 101
      val_coil    : 100
      modes       :
        - Simple
    - type        : WD
      count       : 1
      major_group : 2
      val_reg     : 102
      timeout_reg : 1108
      nv_sav_coil : 1103
      reset_coil  : 1102
    - type        : REGISTER
      major_group : 2
      count       : 35
      start_reg   : 100
    - type        : REGISTER
      major_group : 2
      count       : 29
      start_reg   : 1100
    - type        : DI
      count       : 16
      major_group : 3
      modes       :
        - Simple
        - DirectSwitch
      ds_modes    :
        - Simple
        - Inverted
        - Toggle
      min_v       : 5
      max_v       : 24
      val_reg     : 200
      counter_reg : 203
      direct_reg  : 1226
      deboun_reg  : 1210
      polar_reg   : 1227
      toggle_reg  : 1228
    - type        : RO
      major_group : 3
      count       : 14
      val_reg     : 201
      val_coil    : 200
      modes       :
        - Simple
    - type        : WD
      count       : 1
      major_group : 3
      val_reg     : 202
      timeout_reg : 1208
      nv_sav_coil : 1203
      reset_coil  : 1202
    - type        : REGISTER
      major_group : 3
      count       : 35
      start_reg   : 200
    - type        : REGISTER
      major_group : 3
      count       : 29
      start_reg   : 1200
"""

MODBUS_FEATURE_ENABLED: Final[int] = 1

MODBUS_HOLDING_REGISTER: Final[List] = [
    PropertyMock(registers=[0, 0]),
    PropertyMock(registers=[0, 4, 7]),
    PropertyMock(registers=[11332, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0]),
    PropertyMock(
        registers=[
            1336,
            1028,
            785,
            16,
            32,
            5433,
            0,
            5,
            5000,
            12216,
            50,
            50,
            50,
            50,
            0,
            0,
            0,
            4799,
            255,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            14,
        ]  # noqa
    ),
    PropertyMock(
        registers=[
            16384,
            6144,
            8,
            4,
            0,
            0,
            0,
            4,
            0,
            0,
            0,
            10,
            0,
            6,
            0,
            60,
            0,
            56,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            18,
            0,
            14,
            0,
        ]
    ),
    PropertyMock(
        registers=[
            1336,
            4110,
            0,
            2064,
            784,
            7912,
            0,
            5,
            5000,
            1520,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            0,
            0,
            0,
        ]
    ),
    PropertyMock(
        registers=[
            8192,
            8192,
            0,
            20,
            0,
            29,
            0,
            0,
            0,
            0,
            0,
            4,
            0,
            0,
            0,
            5,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            3,
            0,
            84,
            0,
            95,
            0,
            0,
            0,
            0,
            0,
        ]
    ),
    PropertyMock(
        registers=[
            1336,
            4110,
            0,
            2064,
            784,
            7926,
            0,
            5,
            5000,
            1530,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            50,
            0,
            0,
            0,
        ]
    ),
]
