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
from .panic_manager import PanicManager
from .stock.stock_client import StockClient
from .stock.bot_stock import BotStock
from .smoother import Smoother, NullSmoother


def start():
    exchange = os.getenv('CCXT_EXCHANGE')
    api_key = os.getenv('CCXT_API_KEY')
    api_secret = os.getenv('CCXT_API_SECRET')
    api_password = os.getenv('CCXT_API_PASSWORD')
    subaccount = os.getenv('CCXT_SUBACCOUNT')
    api_base_url = os.getenv('CCXT_API_BASE_URL') # for stock
    leverage = float(os.getenv('ALPHAPOOL_LEVERAGE'))
    log_level = os.getenv('ALPHAPOOL_LOG_LEVEL')
    model_id = os.getenv('ALPHAPOOL_MODEL_ID')
    unit_pos_halflife = float(os.getenv('ALPHAPOOL_UNIT_POS_HALFLIFE', '0'))
    unit_pos_reset_threshold = float(os.getenv('ALPHAPOOL_UNIT_POS_RESET_THRESHOLD', '0.1'))

    logger = create_logger(log_level)

    panic_manager = PanicManager(logger=logger)
    panic_manager.register('bot', 5 * 60, 5 * 60)
    def health_check_ping():
        panic_manager.ping('bot')

    database_url = os.getenv("ALPHAPOOL_DATABASE_URL")
    if database_url == 'mock':
        alphapool_client = MockClient()
    else:
        db = dataset.connect(database_url)
        alphapool_client = Client(db)

    if exchange in ['kabucom']:
        client = StockClient(
            api_key=api_key,
            api_password=api_password,
            api_base_url=api_base_url,
            is_corp=True,
            logger=logger,
        )

        bot = BotStock(
            client=client,
            logger=logger,
            leverage=leverage,
            alphapool_client=alphapool_client,
            model_id=model_id,
            health_check_ping=health_check_ping,
        )
    else:
        client = create_ccxt_client(
            exchange=exchange,
            api_key=api_key,
            api_secret=api_secret,
            api_password=api_password,
            subaccount=subaccount,
        )

        if unit_pos_halflife > 0:
            logger.info(f'unit_pos_smoother enabled halflife {unit_pos_halflife} reset_threshold {unit_pos_reset_threshold}')
            unit_pos_smoother = Smoother(
                logger=logger,
                halflife=unit_pos_halflife,
                reset_threshold=unit_pos_reset_threshold,
                save_path='./unit_pos_smoother_states.json'
            )
        else:
            logger.info('unit_pos_smoother disabled')
            unit_pos_smoother = NullSmoother()

        bot = BotMaker(
            client=client,
            logger=logger,
            leverage=leverage,
            alphapool_client=alphapool_client,
            model_id=model_id,
            health_check_ping=health_check_ping,
            unit_pos_smoother=unit_pos_smoother,
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
    top_stats = snapshot.statistics('traceback')
    for stat in top_stats[:100]:
        print(stat)
        print('count {} size {}'.format(stat.count, stat.size))
        for line in stat.traceback.format():
            print(line)
else:
    start()
