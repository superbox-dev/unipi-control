# Unipi Mqtt API

## Installation

Install the python package in your virtualenv:

```shell
$ cd /opt
$ git@github.com:mh-superbox/unipi-mqtt-api.git
$ pip install -e /opt/unipi-mqtt-api
```

### Systemd Service

Install and start the systemd service:

```shell
$ sudo cp /opt/unipi-mqtt-api/src/lib/systemd/uma.service /lib/systemd
$ sudo chown root:root /lib/systemd/uma.service
$ sudo chmod 644 /lib/systemd/uma.service

$ sudo systemctl daemon-reload
$ sudo systemctl enable uma.service
$ sudo systemctl start uma.service
```

### Configuration

You can set the mqtt broker and logger in the `/etc/default/uma`.

Example:

```yaml
sysfs:
  devices: /sys/bus/platform/devices
mqtt:
  host: localhost
  port: 1883
logger: systemd
```

Key | Value
------ | ------
`mqtt/host` | mqtt broker host
`mqtt/port` | mqtt broker port
`logger` | `systemd` or `file`

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
