# Unipi Control

## Installation

**Requirements:**

* Unipi Neuron Kernel Module and Unipi tools
  * Use the officially APT mirror (https://repo.unipi.technology/debian/) from Unipi Technology
  * Or compile it https://github.com/UniPiTechnology/unipi-kernel / https://github.com/UniPiTechnology/unipi-tools
* Python 3.7

Install the python package in your virtualenv:

```shell
$ cd /opt
$ git clone git@github.com:mh-superbox/unipi-control.git
$ pip install -e /opt/unipi-control
```

### Configuration

```shell
$ sudo cp -R /opt/unipi-control/src/etc/unipi /etc
```

You can set the client settings in the `/etc/unipi/control.yaml`.

Key | Value
------ | ------
`device_name` | The device name for the subscribe and publish topics. Default is the hostname.
`mqtt/host` | The hostname or IP address of the remote broker: Default is `localhost`.
`mqtt/port` | The network port of the server host to connect to. Defaults is `1883`.
`mqtt/keepalive` | Maximum period in seconds allowed between communications with the broker. If no other messages are being exchanged, this controls the rate at which the client will send ping messages to the broker. Default tis `15`.
`mqtt/retry_limit` | Number of attempts to connect to the MQTT broker. Default to `30` (Disable with `False`).
`mqtt/reconnect_interval` | Time between connection attempts. Default is `10`.
`homeassistant/enabled` | Enable Home Assistant MQTT Discovery. Default is `true`.
`homeassistant/discovery_prefix` | The prefix for the discovery topic. Default is `homeassistant`.
`logging/logger` | Set logger to `systemd` or `file`. Default to `systemd`.
`logging/level` | Set level to debug, info, warning or error. Default to `info`.

### Systemd Service

Install and start the systemd service:

```shell
$ sudo cp /opt/unipi-control/src/lib/systemd/system/unipi-control.service /lib/systemd/system
$ sudo chown root:root /lib/systemd/system/unipi-control.service
$ sudo chmod 644 /lib/systemd/system/unipi-control.service

$ sudo systemctl daemon-reload
$ sudo systemctl enable unipi-control.service
$ sudo systemctl start unipi-control.service
```

## Usage

Available mqtt topics:

### Subscribe

Topic | Response | Description
------ | ------ | ------
`unipi/relay/physical/ro_[1-9]_[0-9][0-9]/get` | `{"dev": "relay", "dev_type": "physical", "circuit": "1_01", "value": "1"}` | **Value (string):** "0" is False and "1" is True.
`unipi/relay/digital/do_[1-9]_[0-9][0-9]/get` | `{"dev": "relay", "dev_type": "digital", "circuit": "1_01", "value": "1"}` | **Value (string):** "0" is False and "1" is True.
`unipi/input/digital/di_[1-9]_[0-9][0-9]/get` | `{"dev": "input", "dev_type": "digital", "circuit": "1_01", "value": "1"}` | **Value (string):** "0" is False and "1" is True.

### Publish

Topic | Request | Description
------ | ------ | ------
`unipi/relay/physical/ro_[1-9]_[0-9][0-9]/set` | `"0" or "1"` | Send a string with the value to this topic. **Value (string):** "0" is False and "1" is True. This enable or disable the selected relay.
`unipi/relay/digital/do_[1-9]_[0-9][0-9]/set` | `"0" or "1"` | Send a string with the value to this topic. **Value (string):** "0" is False and "1" is True. This enable or disable the selected relay.
