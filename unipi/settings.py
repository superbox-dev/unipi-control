import logging

import yaml

def load_config() -> dict:
    yaml_file = open("config.yaml", "r")
    return yaml.load(yaml_file, Loader=yaml.FullLoader)


CONFIG = load_config()

logging.basicConfig(
    filename="/var/log/unipi.log",
    level=logging.DEBUG,
    format=("[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s"),
)

logger = logging.getLogger(__name__)
