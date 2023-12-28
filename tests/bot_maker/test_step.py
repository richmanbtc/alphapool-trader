from unittest import TestCase, mock
from unittest.mock import MagicMock
import pandas as pd
from src.bot_maker import BotMaker
from src.logger import create_logger
from src.utils import create_ccxt_client


get_account_response_binance = {
    'totalMarginBalance': '10000.0',
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
    @mock.patch('time.time', mock.MagicMock(return_value=pd.to_datetime('2020/01/01 3:00:00', utc=True).timestamp()))
    def test_step_binance(self):
        logger = create_logger('debug')

        client = create_ccxt_client(exchange='binance')
        client.fapiPrivateV2GetAccount = MagicMock(return_value=get_account_response_binance)
        client.fetch_positions = MagicMock(return_value=fetch_positions_response_binance)
        client.fetch_ticker = MagicMock(return_value=fetch_ticker_response_binance)
        client.fetch_order_book = MagicMock(return_value=fetch_order_book_response_binance)
        client.create_order = MagicMock()
        client.set_leverage = MagicMock()

        alphapool_client = MagicMock()

        t = pd.to_datetime('2020/01/01 00:00:00', utc=True).timestamp()
        df = pd.DataFrame([
            {
                'model_id': 'model1',
                'timestamp': t,
                'positions': {
                    'BTC': 2.0
                },
                'weights': {},
                'orders': {}
            }, {
                'model_id': 'pf-portfolio1',
                'timestamp': t,
                'positions': {},
                'weights': {
                    'model1': 1.0
                },
                'orders': {}
            }
        ])
        df['timestamp'] = pd.to_datetime(df["timestamp"], utc=True, unit='s')
        df = df.set_index(['timestamp', 'model_id']).sort_index()
        alphapool_client.get_positions = MagicMock(return_value=df)

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
            { 'timeInForce': 'GTX', 'reduceOnly': 'false' }
        )
        client.set_leverage.assert_called_with(10, 'BTC/USDT')
