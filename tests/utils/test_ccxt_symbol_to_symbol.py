from unittest import TestCase
from src.utils import ccxt_symbol_to_symbol


class TestUtilsCcxtSymbolToSymbol(TestCase):
    def test_ok(self):
        self.assertEqual(ccxt_symbol_to_symbol('BTC/USD:USD'), 'BTC')
        self.assertEqual(ccxt_symbol_to_symbol('BTC/USDT'), 'BTC')
        self.assertEqual(ccxt_symbol_to_symbol('BTC/USDT:USDT'), 'BTC')
        self.assertEqual(ccxt_symbol_to_symbol('BTC/JPY:JPY'), 'BTC')
