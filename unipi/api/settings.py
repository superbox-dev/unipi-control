import logging

from systemd import journal
import yaml


def load_config(file_name: str) -> dict:
    yaml_file = open(f"configs/{file_name}", "r")
    return yaml.load(yaml_file, Loader=yaml.FullLoader)


API = load_config("api.yaml")


def load_ha_config(file_name: str) -> dict:
    ha: dict = load_config(file_name)

    device: dict = {
        "manufacturer": "Unipi",
    }

    with open(f"""{API["sysfs"]["devices"]}/unipi_plc/model_name""", "r") as f:
        device["model"] = f.read().rstrip()

    # TODO: Firmware per group in ha discovery!
    with open(f"""{API["sysfs"]["devices"]}/unipi_plc/io_group1/firmware_version""", "r") as f:
        device["sw_version"] = f.read().rstrip()

    ha["device"] = device

    return ha


HA = load_ha_config("ha.yaml")

logger_type: str = API["logger"]
logger = logging.getLogger(__name__)

if logger_type == "systemd":
    logger.addHandler(journal.JournalHandler())
    logger.setLevel(level=logging.DEBUG)
elif logger_type == "file":
    logging.basicConfig(
        level=logging.DEBUG,
        filename="/var/log/unipi.log",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
