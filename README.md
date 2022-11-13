[![license-url](https://img.shields.io/npm/l/make-coverage-badge.svg)](https://opensource.org/licenses/MIT)
![coverage-badge](https://raw.githubusercontent.com/mh-superbox/unipi-control/main/coverage.svg)
![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)

### Support me if you like this project 😀

I want to extend the code to support Unipi extensions modules.
The necessary hardware is also required for this.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/mhacker)

# Unipi Control

Control Unipi I/O directly with MQTT commands and without [Evok](https://github.com/UniPiTechnology/evok). Unipi Control use Modbus for fast access to the I/O and provide MQTT topics for reading and writing the circuits. Optionally you can enable the Home Assistant MQTT discovery for binary sensors, sensors, switches and covers.

## Installation

**Requirements:**

* Unipi Neuron Kernel Module and Unipi tools
  * Use the officially APT mirror (https://repo.unipi.technology/debian/) from Unipi Technology
  * Or compile it
    * https://github.com/UniPiTechnology/unipi-kernel
    * https://github.com/UniPiTechnology/unipi-tools
* Python 3.8

### From GIT

```shell
$ sudo -i
$ cd /opt
$ git clone https://github.com/mh-superbox/unipi-control.git
$ pip install -e /opt/unipi-control
$ unipi-control --install
```

### From PyPi

```shell
$ sudo -i
$ pip install unipi-control
$ unipi-control --install
```

## Arguments

| Argument    | Description                                                           |
|-------------|-----------------------------------------------------------------------|
| `--install` | install unipi control                                                 |
| `--yes`     | automatic yes to install prompts                                      |
| `-v`        | verbose mode: multiple -v options increase the verbosity (maximum: 4) |

## Supported Devices

* Unipi Neuron L203

If you have an Unipi device, that is not supported, then contact me.

### External Modbus RTU devices supported:

* [Eastron SDM120M](https://www.eastroneurope.com/products/view/sdm120modbus)


## Configuration

You can set the client settings in the `/etc/unipi/control.yaml`.

### Device

| Key    | Value                                                                                                                                                               |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `name` | The device name for the subscribe and publish topics. Default is the hostname. This name must be unique. This is important if multiple Unipi devices are available. |

```yaml
# control.yaml
device_info:
  name: Unipi
```

### MQTT

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

### Modbus

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

### Home Assistant

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

### Features

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

### Covers

**Warning:** Driving both signals up and down at the same time can damage the motor. There are a couple of checks to prevent such situation. Use this software at your own risk! I do not take any responsibility for it!

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

#### Calibration

The covers save its cover and tilt position in a temporary file each time a stop command is executed. If the Unipi Control is interrupted, and a command (open/closing) is currently being executed, or the system is restarted, the calibration mode is enabled.
When the Unipi Control starts in calibration mode, the cover fully open and disable calibration mode. This is required for the correct cover and tilt position.

### Logging

| Key     | Value                                                                  |
|---------|------------------------------------------------------------------------|
| `level` | Set level to `debug`, `info`, `warning` or `error`. Default is `info`. |

```yaml
# control.yaml
logging:
  level: info
```

## Usage

Available MQTT topics:

### Features

#### Unipi Neuron

| Topic                                         | Response/Request | Description                                                                                          |
|-----------------------------------------------|------------------|------------------------------------------------------------------------------------------------------|
| `[device_name]/relay/ro_[1-9]_[0-9][0-9]/get` | `ON` or `OFF`    | Get a string with the value `ON` or `OFF` from this topic.                                           |
| `[device_name]/relay/do_[1-9]_[0-9][0-9]/get` | `ON` or `OFF`    | Get a string with the value `ON` or `OFF` from this topic.                                           |
| `[device_name]/input/di_[1-9]_[0-9][0-9]/get` | `ON` or `OFF`    | Get a string with the value `ON` or `OFF` from this topic.                                           |
| `[device_name]/relay/ro_[1-9]_[0-9][0-9]/set` | `ON` or `OFF`    | Send a string with the value `ON` or `OFF` to this topic. This enable or disable the selected relay. |
| `[device_name]/relay/do_[1-9]_[0-9][0-9]/set` | `ON` or `OFF`    | Send a string with the value `ON` or `OFF` to this topic. This enable or disable the selected relay. |

#### Eastron SDM120M

| Topic                                                              | Unit  |
|--------------------------------------------------------------------|-------|
| `[device_name]/meter/voltage_[unit]/get`                           | V     |
| `[device_name]/meter/current[unit]/get`                            | A     |
| `[device_name]/meter/current_demand[unit]/get`                     | A     |
| `[device_name]/meter/maximum_current_demand[unit]/get`             | A     |
| `[device_name]/meter/active_power[unit]/get`                       | W     |
| `[device_name]/meter/total_system_power_demand[unit]/get`          | W     |
| `[device_name]/meter/maximum_total_system_power_demand[unit]/get`  | W     |
| `[device_name]/meter/import_system_power_demand[unit]/get`         | W     |
| `[device_name]/meter/maximum_import_system_power_demand[unit]/get` | W     |
| `[device_name]/meter/export_system_power_demand[unit]/get`         | W     |
| `[device_name]/meter/maximum_export_system_power_demand[unit]/get` | W     |
| `[device_name]/meter/apparent_power[unit]/get`                     | VA    |
| `[device_name]/meter/reactive_power[unit]/get`                     | var   |
| `[device_name]/meter/frequency[unit]/get`                          | Hz    |
| `[device_name]/meter/import_active_energy[unit]/get`               | kWh   |
| `[device_name]/meter/export_active_energy[unit]/get`               | kWh   |
| `[device_name]/meter/total_active_energy[unit]/get`                | kWh   |
| `[device_name]/meter/import_reactive_energy[unit]/get`             | kvarh |
| `[device_name]/meter/export_reactive_energy[unit]/get`             | kvarh |
| `[device_name]/meter/total_reactive_energy[unit]/get`              | kvarh |
| `[device_name]/meter/power_factor[unit]/get`                       |       |
| `[device_name]/meter/phase_angle[unit]/get`                        |       |

### Covers

| Topic                                                  | Response/Request                                    | Description                                                          |
|--------------------------------------------------------|-----------------------------------------------------|----------------------------------------------------------------------|
| `[device_name]/[object_id]/cover/[device_class]/state` | `open`, `opening`, `closing`, `closed` or `stopped` | Get the cover state.                                                 |
| `[device_name]/[object_id]/cover/[device_class]/set`          | `OPEN`, `CLOSE` or `STOP`                    | Send a string to control the cover.                                  |
| `[device_name]/[object_id]/cover/[device_class]/position`     | `0` to `100`                                 | Get the cover position. `100` is fully open and `0` is fully closed. |
| `[device_name]/[object_id]/cover/[device_class]/position/set` | `0` to `100`                                 | Send an integer to set the cover position.                           |
| `[device_name]/[object_id]/cover/[device_class]/tilt`         | `0` to `100`                                 | Get the tilt position. `100` is fully open and `0` is fully closed.  |
| `[device_name]/[object_id]/cover/[device_class]/tilt/set`     | `0` to `100`                                 | Send an integer to set the cover position.                           |

## Extras

I have written a Home Assistant blueprint automation to control covers with binary sensors. Take a look in the extra's folder.
