import logging

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
