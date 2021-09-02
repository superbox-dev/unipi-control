import logging

from systemd import journal
import yaml


def load_config() -> dict:
    yaml_file = open("configs/api.yaml", "r")
    return yaml.load(yaml_file, Loader=yaml.FullLoader)


CONFIG = load_config()

file_log: str = CONFIG["log"].get("file")
systemd_log: bool = CONFIG["log"].get("systemd")

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

if file_log:
    fh = logging.FileHandler(file_log)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

if systemd_log:
    logger.addHandler(journal.JournalHandler())
