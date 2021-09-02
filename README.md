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

Topic | Description
------ | ------
`unipi/relay/ro_[1-9]_[0-9][0-9]/set`   | Cell 
