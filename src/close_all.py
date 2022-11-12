import os
from .utils import (
    create_ccxt_client,
)
from .logger import create_logger


def start():
    exchange = os.getenv('CCXT_EXCHANGE')
    api_key = os.getenv('CCXT_API_KEY')
    api_secret = os.getenv('CCXT_API_SECRET')
    subaccount = os.getenv('CCXT_SUBACCOUNT')
    log_level = os.getenv('ALPHAPOOL_LOG_LEVEL')

    logger = create_logger(log_level)
    logger.info(exchange)

    client = create_ccxt_client(
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        subaccount=subaccount,
    )

    poss = client.fetch_positions()
    for pos in poss:
        amount = pos['contracts']
        if amount == 0:
            continue

        symbol = pos['symbol']
        side = 'sell' if pos['side'] == 'long' else 'buy'

        params = {}
        if client.id == 'binance':
            params['reduceOnly'] = 'true'

        logger.info('cancel_all_orders {}'.format(symbol))
        client.cancel_all_orders(symbol)

        logger.info('create_order symbol {} amount {} side {} params {}'.format(
            symbol, amount, side, params
        ))
        client.create_order(
            symbol,
            'market',
            side,
            amount,
            params=params
        )


start()
