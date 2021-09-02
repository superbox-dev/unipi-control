# Unipi Mqtt API

## Installation

### Systemd Service

Install all required python packages in your virtualenv:

```console
$ pip install -r requirements.txt
```

Install and start the systemd service:

```console
$ sudo cp systemd/unipi-mqtt-api.service /etc/systemd/system
$ sudo chown root:root /etc/systemd/system/unipi-mqtt-api.service
$ sudo chmod 644 /etc/systemd/system/unipi-mqtt-api.service

$ sudo systemctl daemon-reload
$ sudo systemctl enable unipi-mqtt-api.service
$ sudo systemctl start unipi-mqtt-api.service
```

## Usage

Available mqtt topics:

Topic | Message | Description
------ | ------ | ------
`unipi/relay/ro_[1-9]_[0-9][0-9]/set` | `{ "value": "1" }` | Send a **dict** with the value. Value can be **0 (False)** or **1 (True)**. | Enable/disable the selected relay.
`unipi/relay/ro_[1-9]_[0-9][0-9]/get` | `{"dev": "relay", "circuit": "ro_1_01", "value": "1"}` | Get a **dict** with the device type, circuit name and value from the selected relay. Value can be **0 (False)** or **1 (True)**. | This topic contains the current status for one of the relays.
`unipi/input/di_[1-9]_[0-9][0-9]/get` | `{"dev": "input", "circuit": "di_1_01", "value": "1"}` | Get a **dict** with the device type, circuit name and value from the selected digital input. Value can be **0 (False)** or **1 (True)**. | This topic contains the current status for one of the digital inputs.
