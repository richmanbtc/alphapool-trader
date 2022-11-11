import argparse
import os
from .utils import (
    create_ccxt_client,
)
from .logger import create_logger


def start():
    parser = argparse.ArgumentParser()
    parser.add_argument('symbol')
    parser.add_argument('leverage', type=int)
    args = parser.parse_args()

    exchange = os.getenv('CCXT_EXCHANGE')
    api_key = os.getenv('CCXT_API_KEY')
    api_secret = os.getenv('CCXT_API_SECRET')
    subaccount = os.getenv('CCXT_SUBACCOUNT')
    log_level = os.getenv('ALPHAPOOL_LOG_LEVEL')

    logger = create_logger(log_level)
    logger.info(exchange)
    logger.info(args)

    client = create_ccxt_client(
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        subaccount=subaccount,
    )

    client.setLeverage(args.leverage, args.symbol)
    logger.info('leverage set')


start()
