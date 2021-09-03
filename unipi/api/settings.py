import logging

from systemd import journal
import yaml


def load_config() -> dict:
    yaml_file = open("configs/api.yaml", "r")
    return yaml.load(yaml_file, Loader=yaml.FullLoader)


CONFIG = load_config()

logger_type: str = CONFIG["logger"]
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
