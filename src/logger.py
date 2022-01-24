import logging
from logging import getLogger, StreamHandler

initialized = False


def create_logger(log_level):
    global initialized

    logger = getLogger(__name__)

    if not initialized:
        level = getattr(logging, log_level.upper())
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        logger.setLevel(level)
        logger.propagate = False

        err = StreamHandler()
        err.setLevel(level)
        err.setFormatter(formatter)
        logger.addHandler(err)

        initialized = True

    return logger
