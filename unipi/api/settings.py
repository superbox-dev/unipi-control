import logging

from systemd import journal
import yaml


def load_config(file_name: str) -> dict:
    yaml_file = open(f"configs/{file_name}", "r")
    return yaml.load(yaml_file, Loader=yaml.FullLoader)


API = load_config("api.yaml")
HA = load_config("home-assistant.yaml")

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
