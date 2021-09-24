# Unipi Mqtt Client

## Installation

**Requirements:**

* Unipi Neuron Kernel Module for SysFS.
  * Use the officially APT mirror (https://repo.unipi.technology/debian/) from Unipi Technology
  * Or compile it https://github.com/mh-superbox/unipi-kernel
* Python 3.7

Install the python package in your virtualenv:

```shell
$ cd /opt
$ git clone git@github.com:mh-superbox/unipi-mqtt-client.git
$ pip install -e /opt/unipi-mqtt-client
```

### Systemd Service

Install and start the systemd service:

```shell
$ sudo cp /opt/unipi-mqtt-client/src/lib/systemd/system/umc.service /lib/systemd/system
$ sudo chown root:root /lib/systemd/system/umc.service
$ sudo chmod 644 /lib/systemd/system/umc.service

$ sudo systemctl daemon-reload
$ sudo systemctl enable umc.service
$ sudo systemctl start umc.service
```

### Configuration

```shell
$ sudo cp -R /opt/unipi-mqtt-client/src/etc/umc /etc
```

You can set the client settings in the `/etc/umc/client.yaml`.

Key | Value
------ | ------
`device_name` | The device name for the subscribe and publish topics. Default to `unipi`.
`mqtt/host` | The hostname or IP address of the remote broker: Default to `localhost`.
`mqtt/port` | The network port of the server host to connect to. Defaults to `1883`.
`mqtt/keepalive` | Maximum period in seconds allowed between communications with the broker. If no other messages are being exchanged, this controls the rate at which the client will send ping messages to the broker. Default to `15`.
`mqtt/retry_limit` | Number of attempts to connect to the MQTT broker. Default to `30` (Disable with `False`).
`mqtt/reconnect_interval` | Time between connection attempts. Default to `10`.
`homeassistant/discovery_prefix` | The prefix for the discovery topic
`logging/logger` | Set logger to `systemd` or `file`. Default to `systemd`.
`logging/level` | Set level to debug, info, warning or error. Default to `info`.

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
