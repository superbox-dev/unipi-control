from typing import List

discovery_message_expected: List[dict] = [
    {
        "message": {
            "name": "MOCKED_FRIENDLY_NAME - DI_1_01",
            "unique_id": "mocked_unipi_mocked_id_di_1_01",
            "state_topic": "mocked_unipi/input/di_1_01/get",
            "qos": 2,
            "object_id": "mocked_id_di_1_01",
            "icon": "mdi:power-standby",
            "payload_on": "OFF",
            "payload_off": "ON",
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_mocked_id_di_1_01/config",
    },
    {
        "message": {
            "name": "MOCKED_FRIENDLY_NAME - DI_1_02",
            "unique_id": "mocked_unipi_mocked_id_di_1_02",
            "state_topic": "mocked_unipi/input/di_1_02/get",
            "qos": 2,
            "object_id": "mocked_id_di_1_02",
            "device_class": "heat",
            "device": {
                "name": "MOCKED UNIPI - MOCKED AREA 2",
                "identifiers": "MOCKED UNIPI - MOCKED AREA 2",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "via_device": "MOCKED UNIPI",
                "manufacturer": "Unipi technology",
                "suggested_area": "MOCKED AREA 2",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_mocked_id_di_1_02/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 1.03",
            "unique_id": "mocked_unipi_di_1_03",
            "state_topic": "mocked_unipi/input/di_1_03/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_1_03/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 1.04",
            "unique_id": "mocked_unipi_di_1_04",
            "state_topic": "mocked_unipi/input/di_1_04/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_1_04/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.01",
            "unique_id": "mocked_unipi_di_2_01",
            "state_topic": "mocked_unipi/input/di_2_01/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_01/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.02",
            "unique_id": "mocked_unipi_di_2_02",
            "state_topic": "mocked_unipi/input/di_2_02/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_02/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.03",
            "unique_id": "mocked_unipi_di_2_03",
            "state_topic": "mocked_unipi/input/di_2_03/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_03/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.04",
            "unique_id": "mocked_unipi_di_2_04",
            "state_topic": "mocked_unipi/input/di_2_04/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_04/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.05",
            "unique_id": "mocked_unipi_di_2_05",
            "state_topic": "mocked_unipi/input/di_2_05/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_05/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.06",
            "unique_id": "mocked_unipi_di_2_06",
            "state_topic": "mocked_unipi/input/di_2_06/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_06/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.07",
            "unique_id": "mocked_unipi_di_2_07",
            "state_topic": "mocked_unipi/input/di_2_07/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_07/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.08",
            "unique_id": "mocked_unipi_di_2_08",
            "state_topic": "mocked_unipi/input/di_2_08/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_08/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.09",
            "unique_id": "mocked_unipi_di_2_09",
            "state_topic": "mocked_unipi/input/di_2_09/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_09/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.10",
            "unique_id": "mocked_unipi_di_2_10",
            "state_topic": "mocked_unipi/input/di_2_10/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_10/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.11",
            "unique_id": "mocked_unipi_di_2_11",
            "state_topic": "mocked_unipi/input/di_2_11/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_11/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.12",
            "unique_id": "mocked_unipi_di_2_12",
            "state_topic": "mocked_unipi/input/di_2_12/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_12/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.13",
            "unique_id": "mocked_unipi_di_2_13",
            "state_topic": "mocked_unipi/input/di_2_13/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_13/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.14",
            "unique_id": "mocked_unipi_di_2_14",
            "state_topic": "mocked_unipi/input/di_2_14/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_14/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.15",
            "unique_id": "mocked_unipi_di_2_15",
            "state_topic": "mocked_unipi/input/di_2_15/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_15/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 2.16",
            "unique_id": "mocked_unipi_di_2_16",
            "state_topic": "mocked_unipi/input/di_2_16/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_2_16/config",
    },
    {
        "message": {
            "name": "MOCKED_FRIENDLY_NAME - DI_3_01",
            "unique_id": "mocked_unipi_di_3_01",
            "state_topic": "mocked_unipi/input/di_3_01/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI - MOCKED AREA 1",
                "identifiers": "MOCKED UNIPI - MOCKED AREA 1",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
                "suggested_area": "MOCKED AREA 1",
                "via_device": "MOCKED UNIPI",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_01/config",
    },
    {
        "message": {
            "name": "MOCKED_FRIENDLY_NAME - DI_3_02",
            "unique_id": "mocked_unipi_di_3_02",
            "state_topic": "mocked_unipi/input/di_3_02/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI - MOCKED AREA 1",
                "identifiers": "MOCKED UNIPI - MOCKED AREA 1",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
                "suggested_area": "MOCKED AREA 1",
                "via_device": "MOCKED UNIPI",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_02/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.03",
            "unique_id": "mocked_unipi_di_3_03",
            "state_topic": "mocked_unipi/input/di_3_03/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_03/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.04",
            "unique_id": "mocked_unipi_di_3_04",
            "state_topic": "mocked_unipi/input/di_3_04/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_04/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.05",
            "unique_id": "mocked_unipi_di_3_05",
            "state_topic": "mocked_unipi/input/di_3_05/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_05/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.06",
            "unique_id": "mocked_unipi_di_3_06",
            "state_topic": "mocked_unipi/input/di_3_06/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_06/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.07",
            "unique_id": "mocked_unipi_di_3_07",
            "state_topic": "mocked_unipi/input/di_3_07/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_07/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.08",
            "unique_id": "mocked_unipi_di_3_08",
            "state_topic": "mocked_unipi/input/di_3_08/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_08/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.09",
            "unique_id": "mocked_unipi_di_3_09",
            "state_topic": "mocked_unipi/input/di_3_09/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_09/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.10",
            "unique_id": "mocked_unipi_di_3_10",
            "state_topic": "mocked_unipi/input/di_3_10/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_10/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.11",
            "unique_id": "mocked_unipi_di_3_11",
            "state_topic": "mocked_unipi/input/di_3_11/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_11/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.12",
            "unique_id": "mocked_unipi_di_3_12",
            "state_topic": "mocked_unipi/input/di_3_12/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_12/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.13",
            "unique_id": "mocked_unipi_di_3_13",
            "state_topic": "mocked_unipi/input/di_3_13/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_13/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.14",
            "unique_id": "mocked_unipi_di_3_14",
            "state_topic": "mocked_unipi/input/di_3_14/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_14/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.15",
            "unique_id": "mocked_unipi_di_3_15",
            "state_topic": "mocked_unipi/input/di_3_15/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_15/config",
    },
    {
        "message": {
            "name": "MOCKED UNIPI: Digital Input 3.16",
            "unique_id": "mocked_unipi_di_3_16",
            "state_topic": "mocked_unipi/input/di_3_16/get",
            "qos": 2,
            "device": {
                "name": "MOCKED UNIPI",
                "identifiers": "MOCKED UNIPI",
                "model": "MOCKED_NAME MOCKED_MODEL",
                "sw_version": "0.0",
                "manufacturer": "Unipi technology",
            },
        },
        "topic": "homeassistant/binary_sensor/mocked_unipi_di_3_16/config",
    },
]
