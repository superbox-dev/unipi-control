![coverage-badge](https://raw.githubusercontent.com/superbox-dev/unipi-control/main/coverage.svg)
[![CI](https://github.com/superbox-dev/unipi-control/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/superbox-dev/unipi-control/actions/workflows/ci.yml)
[![Version](https://img.shields.io/pypi/pyversions/unipi-control.svg)](https://pypi.python.org/pypi/unipi-control)

[![license-url](https://img.shields.io/pypi/l/unipi-control.svg)](https://github.com/superbox-dev/unipi-control/blob/main/LICENSE)
![PyPi downloads](https://img.shields.io/pypi/dm/unipi-control)
![Typing: strict](https://img.shields.io/badge/typing-strict-green.svg)
![Code style: black](https://img.shields.io/badge/code%20style-black-black)
![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v1.json)

<!-- pitch start -->
# Unipi Control

Unipi Control use Modbus for fast access to the I/O and provide MQTT topics for reading and writing the circuits. Optionally you can enable the Home Assistant MQTT discovery for binary sensors, sensors, switches and covers.
<!-- pitch end -->

---

For more information please read the documentation at:
[docs.superbox.one](https://docs.superbox.one)

---

<!-- quickstart start -->
## Getting started

### Recommended installation (only for Unipi Neuron)

We have a ready to use SD card image called [Unipi Control OS](https://github.com/superbox-dev/unipi-control-os).

### Alternative installation with pip (Debian based systems)

**Requirements:**

* Unipi Neuron Kernel Module and Unipi tools (Use the officially APT mirror (https://repo.unipi.technology/debian/) from Unipi Technology)
* Python >= 3.8

Create a virtual environment:

```bash
python3 -m venv PATH_TO_VENV
```

Activate the virtual environment:

```bash
source PATH_TO_VENV/bin/activate
```

Install `unipi-control` with pip:

```bash
pip install unipi-control
```

Copy the [config files](https://github.com/superbox-dev/unipi-control/data/opkg/data/local/etc/unipi) to `/etc/unipi` and configurate the `/etc/unipi/control.yaml`.

Create the systemd service `/etc/systemd/system/unipi-control.service` with following content:

```ini
[Unit]
Description=Unipi Control
After=multi-user.target

[Service]
Type=simple
ExecStart=PATH_TO_VENV/bin/unipi-control --log systemd
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start the systemd service:

```bash
systemctl --system daemon-reload
systemctl enable unipi-control.service
systemctl start unipi-control.service
```
<!-- quickstart end -->

## Changelog

The changelog lives in the [CHANGELOG.md](CHANGELOG.md) document. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## Contributing

We're happy about your contributions to the project!

You can get started by reading the [CONTRIBUTING.md](CONTRIBUTING.md).

<!-- donation start -->
## Donation

We put a lot of time into this project. If you like it, you can support us with a donation.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/F2F0KXO6D)
<!-- donation end -->

## Extras

We have a Home Assistant blueprint automation to control covers with binary sensors. Take a look in the [extras](data/extras) directory.

<!-- additional_info start -->
## Additional information

This is a third-party software for [Unipi Neuron](https://www.unipi.technology). This software **is NOT** from [Unipi Technology s.r.o.](https://www.unipi.technology). 
<!-- additional_info end -->
