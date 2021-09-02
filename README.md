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

### Configuration

You can set the mqtt broker and logger in the `config.yaml`

Example:

```yaml
sysfs:
  devices: /sys/bus/platform/devices
mqtt:
  host: localhost
  port: 1883
log:
  systemd: True
  file: /var/log/unipi.log
```

Key | Value
------ | ------
`mqtt/host` | mqtt broker host
`mqtt/port` | mqtt broker port
`log/systemd` | Enable systemd journal (`True`/`False`)
`log/file` | path to the log file (Set `False` for disable file logging)

## Usage

Available mqtt topics:

### Subscribe

Topic | Response | Description
------ | ------ | ------
`unipi/relay/ro_[1-9]_[0-9][0-9]/get` | `{"dev": "relay", "relay_type": "physical", "circuit": "ro_1_01", "value": "1"}` | This topic contains the current status for the selected relay. Returns a dict with the dev (string), relay_type (string), circuit (string) and value (string) from the selected relay. Value can be **"0" (False)** or **"1" (True)**. 
`unipi/relay/do_[1-9]_[0-9][0-9]/get` | `{"dev": "relay", "relay_type": "digital", "circuit": "do_1_01", "value": "1"}` | This topic contains the current status for the selected digital output. Returns a dict with the dev (string), relay_type (string), circuit (string) and value (string) from the selected digital output. Value can be **"0" (False)** or **"1" (True)**. 
`unipi/input/di_[1-9]_[0-9][0-9]/get` | `{"dev": "input", "circuit": "di_1_01", "value": "1"}` | This topic contains the current status for the selected inputs. Returns a dict with the dev (string), circuit (string) and value (string) from the selected digital input. Value can be **"0" (False)** or **"1" (True)**. 

### Publish

Topic | Request | Description
------ | ------ | ------
`unipi/relay/ro_[1-9]_[0-9][0-9]/set` | `{ "value": "1" }` | Send a JSON string, with the value (string) to this topic. Value can be **"0" (False)** or **"1" (True)**. This enable or disable the selected relay.
`unipi/relay/do_[1-9]_[0-9][0-9]/set` | `{ "value": "1" }` | Send a JSON string, with the value (string) to this topic. Value can be **"0" (False)** or **"1" (True)**. This enable or disable the selected digital output.
