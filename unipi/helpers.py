import logging

import yaml


LOG_FORMAT = ("[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

logging.basicConfig(
    filename="/var/log/unipi.log",
    level=logging.INFO,
    format=LOG_FORMAT,
)


class VerboseMixin:
    def show_msg(self, msg) -> None:
        if self._verbose:
            print(msg)

        logger.info(msg)


class ConfigMixin:
    @property
    def config(self) -> dict:
        yaml_file = open("config.yaml", "r")
        return yaml.load(yaml_file, Loader=yaml.FullLoader)

    @property
    def topics(self) -> list:
        return [(f"unipi/{value}", 0) for key, value in self.config["observe"].items()]

    def get_topic(self, name: str) -> str:
        return self.config["observe"].get(name)
