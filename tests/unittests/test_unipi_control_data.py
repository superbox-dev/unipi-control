from typing import Final

UNIPI_CONTROL_INSTALLER_WITH_ENABLE_SYSTEMD_OUTPUT: Final[
    str
] = """Copy config files to '{config_loader_temp}'
Copy systemd service 'unipi-control.service'
Enable systemd service 'unipi-control.service'
"""


UNIPI_CONTROL_INSTALLER_WITHOUT_ENABLE_SYSTEMD_OUTPUT: Final[
    str
] = """Copy config files to '{config_loader_temp}'
Copy systemd service 'unipi-control.service'

You can enable the systemd service with the command:
systemctl enable --now unipi-control
"""

UNIPI_CONTROL_INSTALLER_WITHOUT_OVERWRITE_CONFIG_OUTPUT: Final[
    str
] = """Copy systemd service 'unipi-control.service'

You can enable the systemd service with the command:
systemctl enable --now unipi-control
"""
