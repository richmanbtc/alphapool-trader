from unittest import TestCase, mock
from unittest.mock import MagicMock
import pandas as pd
from src.bot_maker import BotMaker
from src.logger import create_logger
from src.utils import create_ccxt_client

get_account_response_ftx = {
    'result': {
        'collateral': 1
    },
}

fetch_positions_response_ftx = [{
    'symbol': 'BTC/USD:USD',
    'side': 'long',
    'contracts': 1,
}]


get_account_response_binance = {
    'totalMarginBalance': '1.0',
}

fetch_positions_response_binance = [{
    'symbol': 'BTC/USDT',
    'side': 'long',
    'contracts': 1,
}]

fetch_ticker_response_binance = {
    'last': 10000.0
}

fetch_order_book_response_binance = {
    'asks': [
        [11000.0, 100],
        [12000.0, 100],
    ],
    'bids': [
        [9000.0, 100],
        [8000.0, 100],
    ]
}

class TestBotMakerStep(TestCase):
    # def test_step_ftx(self):
    #     agent_base_url = os.getenv('ALPHASEA_AGENT_BASE_URL')
    #     logger = create_logger('debug')
    #
    #     client = create_ccxt_client(exchange='ftx')
    #     client.privateGetAccount = MagicMock(return_value=get_account_response_ftx)
    #     client.fetch_positions = MagicMock(return_value=fetch_positions_response_ftx)
    #     client.create_order = MagicMock()
    #
    #     bot = Bot(
    #         client=client,
    #         logger=logger,
    #         leverage=1.0,
    #         agent_base_url=agent_base_url
    #     )
    #
    #     bot._step()
    #
    #     client.create_order.assert_called()

    @mock.patch('time.time', mock.MagicMock(return_value=pd.to_datetime('2020/01/01 3:00:00', utc=True).timestamp()))
    def test_step_binance(self):
        logger = create_logger('debug')

        client = create_ccxt_client(exchange='binance')
        client.fapiPrivateGetAccount = MagicMock(return_value=get_account_response_binance)
        client.fetch_positions = MagicMock(return_value=fetch_positions_response_binance)
        client.fetch_ticker = MagicMock(return_value=fetch_ticker_response_binance)
        client.fetch_order_book = MagicMock(return_value=fetch_order_book_response_binance)
        client.create_order = MagicMock()
        client.cancel_all_orders = MagicMock()

        alphapool_client = MagicMock()
        alphapool_client.get_positions = MagicMock(return_value=pd.DataFrame([
            {
                'model_id': 'pf-portfolio1',
                'timestamp': pd.to_datetime('2020/01/01 00:00:00', utc=True),
                'w.model1': 1.0,
            },
            {
                'model_id': 'model1',
                'timestamp': pd.to_datetime('2020/01/01 00:00:00', utc=True),
                'p.BTC': 2.0,
            },
        ]).set_index(['model_id', 'timestamp']))

        bot = BotMaker(
            client=client,
            logger=logger,
            leverage=1.0,
            model_id='pf-portfolio1',
            alphapool_client=alphapool_client,
        )

        bot._step()

        client.create_order.assert_called_with(
            'BTC/USDT',
            'limit',
            'buy',
            1.0,
            9000.0,
        )
        client.cancel_all_orders.assert_called_with(symbol='BTC/USDT')
