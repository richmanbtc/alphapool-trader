from unittest import TestCase
from src.utils import symbol_to_ccxt_symbol


class TestUtilsSymbolToCcxtSymbol(TestCase):
    def test_ok(self):
        self.assertEqual(symbol_to_ccxt_symbol('BTC', exchange='ftx'), 'BTC/USD:USD')
        self.assertEqual(symbol_to_ccxt_symbol('BTC', exchange='binance'), 'BTC/USDT')
        self.assertEqual(symbol_to_ccxt_symbol('BTC', exchange='okx'), 'BTC/USDT:USDT')
        self.assertEqual(symbol_to_ccxt_symbol('BTC', exchange='bybit'), 'BTC/USDT:USDT')
        self.assertEqual(symbol_to_ccxt_symbol('BTC', exchange='bitflyer'), 'BTC/JPY:JPY')
