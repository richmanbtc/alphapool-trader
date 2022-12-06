import os
import dataset
import tracemalloc
from alphapool import Client
from .utils import (
    create_ccxt_client,
)
from .logger import create_logger
from .bot_maker import BotMaker
from .alphapool_mock import MockClient


def start():
    exchange = os.getenv('CCXT_EXCHANGE')
    api_key = os.getenv('CCXT_API_KEY')
    api_secret = os.getenv('CCXT_API_SECRET')
    api_password = os.getenv('CCXT_API_PASSWORD')
    subaccount = os.getenv('CCXT_SUBACCOUNT')
    leverage = float(os.getenv('ALPHAPOOL_LEVERAGE'))
    log_level = os.getenv('ALPHAPOOL_LOG_LEVEL')
    model_id = os.getenv('ALPHAPOOL_MODEL_ID')

    database_url = os.getenv("ALPHAPOOL_DATABASE_URL")
    if database_url == 'mock':
        alphapool_client = MockClient()
    else:
        db = dataset.connect(database_url)
        alphapool_client = Client(db)

    logger = create_logger(log_level)

    client = create_ccxt_client(
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        api_password=api_password,
        subaccount=subaccount,
    )

    bot = BotMaker(
        client=client,
        logger=logger,
        leverage=leverage,
        alphapool_client=alphapool_client,
        model_id=model_id
    )
    bot.run()


tracemalloc_enabled = int(os.getenv('TRACEMALLOC_ENABLED', 0))

if tracemalloc_enabled != 0:
    tracemalloc.start(int(os.getenv('TRACEMALLOC_FRAMES', 1)))

    try:
        start()
    except:
        print('exception')

    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    for stat in top_stats[:100]:
        print(stat)
else:
    start()
