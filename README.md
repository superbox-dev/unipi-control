# Unipi Control

Control Unipi I/O directly with MQTT commands and without [Evok](https://github.com/UniPiTechnology/evok). Unipi Control use Modbus for fast access to the I/O and provide MQTT topics for reading and writing the circuits. Optionally you can enable the Home Assistant MQTT discovery for binary sensors, switches and covers.

## Installation

**Requirements:**

* Unipi Neuron Kernel Module and Unipi tools
  * Use the officially APT mirror (https://repo.unipi.technology/debian/) from Unipi Technology
  * Or compile it
    * https://github.com/UniPiTechnology/unipi-kernel
    * https://github.com/UniPiTechnology/unipi-tools
* Python 3.7

```shell
$ cd /opt
$ git clone git@github.com:mh-superbox/unipi-control.git
$ pip install -e /opt/unipi-control
$ unipi-control --install
```

### Configuration

You can set the client settings in the `/etc/unipi/control.yaml`.

#### Device

Key | Value
------ | ------
`device_name` | The device name for the subscribe and publish topics. Default is the hostname.

```yaml
# control.yaml
device_name: unipi
```

#### MQTT

Key | Value
------ | ------
`host` | The hostname or IP address of the remote broker: Default is `localhost`.
`port` | The network port of the server host to connect to. Defaults is `1883`.
`keepalive` | Maximum period in seconds allowed between communications with the broker. If no other messages are being exchanged, this controls the rate at which the client will send ping messages to the broker. Default tis `15`.
`retry_limit` | Number of attempts to connect to the MQTT broker. Default to `30` (Disable with `False`).
`reconnect_interval` | Time between connection attempts. Default is `10`.

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

#### Home Assistant

Key | Value
------ | ------
`enabled` | Enable Home Assistant MQTT Discovery. Default is `true`.
`discovery_prefix` | The prefix for the discovery topic. Default is `homeassistant`.

```yaml
# control.yaml
homeassistant:
  enabled: true
  discovery_prefix: homeassistant
```

#### Features

It's possible to give the circuits friendly names. This names will be used for switches and binary sensors in Home Assistant.

```yaml
# control.yaml
features:
  di_3_02:
    friendly_name: "Workspace - Switch up"
  di_3_03:
    friendly_name: "Workspace - Switch down"
```

#### Covers

**Warning:** Driving both signals up and down at the same time can damage the motor. There are a couple of checks to prevent such situation. Use this software at your own risk! I do not take any responsibility for it!

The Home Assistant Discovery for the covers is optionally. Covers can be control with MQTT topics without Home Assistant.

Key | Value
------ | ------
`friendly_name` | Friendly name of the cover. It is used e.g. for Home Assistant.
`cover_type` | Cover types can be "blind", "roller_shutter", or "garage_door".
`topic_name` | Unique name for the MQTT topic.
`full_open_time` | Define the time (in seconds) it takes for the cover to fully open.
`full_close_time` | Define the time (in seconds) it takes for the cover to fully close.
`tilt_change_time` | Define the time (in seconds) that the tilt changes from fully open to fully closed state.
`circuit_up` | Output circuit name from a relay or digital output.
`circuit_down` | Output circuit name from a relay or digital output.

```yaml
# control.yaml
covers:
  - friendly_name: "Workspace - Blind 1"
    cover_type: "blind"
    topic_name: workspace_1
    full_open_time: 35.5
    full_close_time: 35.5
    tilt_change_time: 1.5
    circuit_up: ro_3_03
    circuit_down: ro_3_02
```

#### Logging

Key | Value
------ | ------
`logger` | Set logger to `systemd` or `file`. Default is `systemd`.
`level` | Set level to debug, info, warning or error. Default is `info`.

```yaml
# control.yaml
logging:
  logger: systemd
  level: info
```

## Usage

Available MQTT topics:

### Features

Topic | Response/Request | Description
------ | ------ | ------
`[device_name]/relay/physical/ro_[1-9]_[0-9][0-9]/get` | `ON` or `OFF` | Get a string with the value `ON` or `OFF` from this topic.
`[device_name]/relay/digital/do_[1-9]_[0-9][0-9]/get` | `ON` or `OFF` | Get a string with the value `ON` or `OFF` from this topic.
`[device_name]/input/digital/di_[1-9]_[0-9][0-9]/get` | `ON` or `OFF` | Get a string with the value `ON` or `OFF` from this topic.
`[device_name]/relay/physical/ro_[1-9]_[0-9][0-9]/set` | `ON` or `OFF` | Send a string with the value `ON` or `OFF` to this topic. This enable or disable the selected relay.
`[device_name]/relay/digital/do_[1-9]_[0-9][0-9]/set` | `ON` or `OFF` |  Send a string with the value `ON` or `OFF` to this topic. This enable or disable the selected relay.

### Covers

Topic | Response/Request | Description
------ | ------ | ------
`[device_name]/[topic_name]/cover/[cover_type]/state` | `open`, `opening`, `closing`, `closed` or `stopped` | Get the cover state.
`[device_name]/[topic_name]/cover/[cover_type]/set` | `OPEN`, `CLOSE` or `STOP` | Send a string to control the cover.
`[device_name]/[topic_name]/cover/[cover_type]/position` | `0` to `100` | Get the cover position. `100` is fully open and `0` is fully closed.
`[device_name]/[topic_name]/cover/[cover_type]/position/set` |  `0` to `100` | Send an integer to set the cover position.
`[device_name]/[topic_name]/cover/[cover_type]/tilt` |  `0` to `100` | Get the tilt position. `100` is fully open and `0` is fully closed.
`[device_name]/[topic_name]/cover/[cover_type]/tilt/set` |  `0` to `100` | Send an integer to set the cover position.
