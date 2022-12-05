import os
import pprint
from .utils import (
    create_ccxt_client,
)
from .logger import create_logger


def start():
    exchange = os.getenv('CCXT_EXCHANGE')
    log_level = os.getenv('ALPHAPOOL_LOG_LEVEL')

    logger = create_logger(log_level)
    logger.info(exchange)

    client = create_ccxt_client(
        exchange=exchange,
    )

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(client.fetch_markets())


start()
