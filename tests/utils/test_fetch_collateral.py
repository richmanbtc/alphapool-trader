from unittest import TestCase
from unittest.mock import MagicMock
from src.utils import fetch_collateral
import pandas as pd
from pandas.testing import assert_frame_equal

# https://docs.ftx.com/#get-account-information

response_ftx = {
    'result': {
        'collateral': '1.0'
    },
}

# https://github.com/ccxt/ccxt/blob/513fe849c7db64d7f3b3927a8f1c7855b8166a01/python/ccxt/binance.py#L1758

response_binance = {
    'totalMarginBalance': '1.0',
}


class TestUtilsFetchCollateral(TestCase):
    def test_ok_ftx(self):
        client = MagicMock()
        client.id = 'ftx'
        client.privateGetAccount.return_value = response_ftx

        collateral = fetch_collateral(client)
        self.assertEqual(collateral, 1)

    def test_ok_binance(self):
        client = MagicMock()
        client.id = 'binance'
        client.fapiPrivateGetAccount.return_value = response_binance

        collateral = fetch_collateral(client)
        self.assertEqual(collateral, 1)
