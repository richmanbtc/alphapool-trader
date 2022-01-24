import os
from .utils import (
    create_ccxt_client,
)
from .logger import create_logger
from .bot import Bot


def start():
    exchange = os.getenv('CCXT_EXCHANGE')
    api_key = os.getenv('CCXT_API_KEY')
    api_secret = os.getenv('CCXT_API_SECRET')
    subaccount = os.getenv('CCXT_SUBACCOUNT')
    leverage = float(os.getenv('ALPHASEA_LEVERAGE'))
    agent_base_url = os.getenv('ALPHASEA_AGENT_BASE_URL')
    log_level = os.getenv('ALPHASEA_LOG_LEVEL')

    logger = create_logger(log_level)

    client = create_ccxt_client(
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        subaccount=subaccount,
    )

    bot = Bot(
        client=client,
        logger=logger,
        leverage=leverage,
        agent_base_url=agent_base_url
    )
    bot.run()

start()
