# Configuration

This are the configuration settings for the `/etc/unipi/control.yaml`.

## Device

| Key    | Value                                                                                                                                                               |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `name` | The device name for the subscribe and publish topics. Default is the hostname. This name must be unique. This is important if multiple Unipi devices are available. |

```yaml
# control.yaml
device_info:
  name: Unipi
```

## MQTT

| Key                  | Value                                                                                                                                                                                                                  |
|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `host`               | The hostname or IP address of the remote broker: Default is `localhost`.                                                                                                                                               |
| `port`               | The network port of the server host to connect to. Defaults is `1883`.                                                                                                                                                 |
| `keepalive`          | Maximum period in seconds allowed between communications with the broker. If no other messages are being exchanged, this controls the rate at which the client will send ping messages to the broker. Default is `15`. |
| `retry_limit`        | Number of attempts to connect to the MQTT broker. Default to `30` (Disable with `False`).                                                                                                                              |
| `reconnect_interval` | Time between connection attempts. Default is `10`.                                                                                                                                                                     |

```yaml
# control.yaml
mqtt:
  host: localhost
  port: 1883
  connection:
    keepalive: 15
    retry_limit: 30
    reconnect_interval: 10
```

## Modbus

| Key                       | Value                                               |
|---------------------------|-----------------------------------------------------|
| `baud_rate`               | The baud rate for modbus RTU. Default is `2400`.    |
| `parity`                  | The parity for modbus RTU. Default is `N`.          |
| `unit`                    | A list of all modbus RTU devices.                   |
| `unit` » `unit`          | The unique modbus RTU unit ID.                       |
| `unit` » `device_name`    | Custom device name. Used for the Home Assistant UI. |
| `unit` » `suggested_area` | Used as entity area in Home Assistant.              |

```yaml
# control.yaml
modbus:
  baud_rate: 9600
  parity: N
  units:
    - unit: 1
      device_name: Eastron SDM120M
      identifier: Eastron_SDM120M
      suggested_area: Workspace
```

## Home Assistant

| Key                | Value                                                           |
|--------------------|-----------------------------------------------------------------|
| `enabled`          | Enable Home Assistant MQTT Discovery. Default is `true`.        |
| `discovery_prefix` | The prefix for the discovery topic. Default is `homeassistant`. |

```yaml
# control.yaml
homeassistant:
  enabled: true
  discovery_prefix: homeassistant
```

## Features

It's possible to give the features friendly names. This names will be used for switches and binary sensors and sensors in Home Assistant.

| Key                   | Value                                                                                                                                                      |            |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| `object_id`           | Used as entity ID in Home Assistant.                                                                                                                       | optionally |
| `friendly_name`       | Used as entity name in Home Assistant.                                                                                                                     | optionally |
| `icon`                | Used as icon in Home Assistant. Any icon from [materialdesignicons.com](https://materialdesignicons.com). Prefix name with mdi:, ie `mdi:home`.            | optionally |
| `device_class`        | Used for [Device Class](https://www.home-assistant.io/docs/configuration/customizing-devices/#device-class) in Home Assistant.                             | optionally |
| `state_class`         | Used for [State Class](https://developers.home-assistant.io/docs/core/entity/sensor/#available-state-classes) in Home Assistant. Thid is only for sensors. | optionally |
| `unit_of_measurement` | Used as measurement unit in Home Assistant. Only for sensors.                                                                                              | optionally |
| `suggested_area`      | Used as entity area in Home Assistant.                                                                                                                     | optionally |
| `invert_state`        | Invert the `ON`/`OFF` state. Default is `false`. Only for binary sensors.                                                                                  | optionally |

```yaml
# control.yaml
features:
  di_3_02:
    object_id: workspace_switch_up
    friendly_name: Workspace - Switch up
    suggested_area: Workspace
  di_3_03:
    object_id: workspace_switch_down
    friendly_name: Workspace - Switch down
    suggested_area: Workspace
  active_power_1:
    object_id: workspace_active_power
    friendly_name: Workspace - Active Power
    suggested_area: Workspace
    device_class: power
    state_class: measurement
    unit_of_measurement: W
```

## Covers

> **Warning:** Driving both signals up and down at the same time can damage the motor. There are a couple of checks to prevent such situation. Use this software at your own risk! I do not take any responsibility for it!

The Home Assistant Discovery for the covers is optionally. Covers can be control with MQTT topics without Home Assistant.

| Key                | Value                                                                                                                                      |            |
|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------|------------|
| `object_id`        | Used as entity ID in Home Assistant.                                                                                                       |            |
| `friendly_name`    | Used as entity name in Home Assistant.                                                                                                     | optionally |
| `suggested_area`   | Used as entity area in Home Assistant.                                                                                                     | optionally |
| `device_class`     | Device class can be "blind", "roller_shutter", or "garage_door".                                                                           | optionally |
| `cover_run_time`   | Define the time (in seconds) it takes for the cover to fully open or close.                                                                |            |
| `tilt_change_time` | Define the time (in seconds) that the tilt changes from fully open to fully closed state. Tilt is only available for device class "blind". | optionally |
| `cover_up`         | Output circuit name from a relay or digital output.                                                                                        |            |
| `cover_down`       | Output circuit name from a relay or digital output.                                                                                        |            |

```yaml
# control.yaml
covers:
  - id: workspace_1
    friendly_name: "Workspace - Blind 1"
    suggested_area: "Workspace"
    device_class: "blind"
    cover_run_time: 35.5
    tilt_change_time: 1.5
    cover_up: ro_3_03
    cover_down: ro_3_02
```

### Calibration

The covers save its cover and tilt position in a temporary file each time a stop command is executed. If the Unipi Control is interrupted, and a command (open/closing) is currently being executed, or the system is restarted, the calibration mode is enabled.
When the Unipi Control starts in calibration mode, the cover fully open and disable calibration mode. This is required for the correct cover and tilt position.

## Logging

| Key     | Value                                                                  |
|---------|------------------------------------------------------------------------|
| `level` | Set level to `debug`, `info`, `warning` or `error`. Default is `info`. |

```yaml
# control.yaml
logging:
  level: info
```
