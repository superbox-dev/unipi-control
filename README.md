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
$ sudo cp /opt/unipi-mqtt-api/src/lib/systemd/system/uma.service /lib/systemd/system
$ sudo chown root:root /lib/systemd/system/uma.service
$ sudo chmod 644 /lib/systemd/system/uma.service

$ sudo systemctl daemon-reload
$ sudo systemctl enable uma.service
$ sudo systemctl start uma.service
```

### Configuration

```shell
$ sudo cp -R /opt/unipi-mqtt-api/src/etc/uma /etc
```

* You can set the api settings in the `/etc/uma/api.yaml`
* You can set the Home Assistant settings in the `/etc/uma/ha.yaml`

#### API settings

Key | Value
------ | ------
`device_name` | The device name for the subscribe and publish topics
`mqtt/host` | Mqtt broker host
`mqtt/port` | mqtt broker port
`logger` | Set logger to `systemd` or `file`

#### Home Assistant settings

Key | Value
------ | ------
`discovery_prefix` | The prefix for the discovery topic

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
