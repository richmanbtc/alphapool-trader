import os
from unittest import TestCase
from unittest.mock import MagicMock
from src.bot import Bot
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

class TestBotStep(TestCase):
    def test_step_ftx(self):
        agent_base_url = os.getenv('ALPHASEA_AGENT_BASE_URL')
        logger = create_logger('debug')

        client = create_ccxt_client(exchange='ftx')
        client.privateGetAccount = MagicMock(return_value=get_account_response_ftx)
        client.fetch_positions = MagicMock(return_value=fetch_positions_response_ftx)
        client.create_order = MagicMock()

        bot = Bot(
            client=client,
            logger=logger,
            leverage=1.0,
            agent_base_url=agent_base_url
        )

        bot._step()

        client.create_order.assert_called()

    def test_step_binance(self):
        agent_base_url = os.getenv('ALPHASEA_AGENT_BASE_URL')
        logger = create_logger('debug')

        client = create_ccxt_client(exchange='binance')
        client.fapiPrivateGetAccount = MagicMock(return_value=get_account_response_binance)
        client.fetch_positions = MagicMock(return_value=fetch_positions_response_binance)
        client.create_order = MagicMock()

        bot = Bot(
            client=client,
            logger=logger,
            leverage=1.0,
            agent_base_url=agent_base_url
        )

        bot._step()

        client.create_order.assert_called()
