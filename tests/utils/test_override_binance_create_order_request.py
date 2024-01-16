from unittest import TestCase
from src.utils import _override_binance_create_order_request as func


class Client:
    def __init__(self):
        self.x = 123

    def create_order_request(self, symbol, type, side, amount, price=None, params={}):
        return {
            'symbol': symbol,
            'price': price,
            'x': self.x,
        }


class TestUtilsOverrideBinanceCreateOrderRequest(TestCase):
    def test_not_bbo_ok(self):
        client = Client()
        func(client)
        res = client.create_order_request(
            symbol='btc',
            type='limit',
            side='buy',
            amount=2,
            price=3,
            params={}
        )
        self.assertEqual(res, {
            'symbol': 'btc',
            'price': 3,
            'x': 123
        })

    def test_not_bbo2_ok(self):
        client = Client()
        func(client)
        res = client.create_order_request(
            symbol='btc',
            type='limit',
            side='buy',
            amount=2,
            price=3,
            params={ 'priceMatch': None }
        )
        self.assertEqual(res, {
            'symbol': 'btc',
            'price': 3,
            'x': 123
        })

    def test_bbo_ok(self):
        client = Client()
        func(client)
        res = client.create_order_request(
            symbol='btc',
            type='limit',
            side='buy',
            amount=2,
            price=None,
            params={ 'priceMatch': 'QUEUE' }
        )
        self.assertEqual(res, {
            'symbol': 'btc',
            'x': 123
        })

    def test_bbo_error(self):
        client = Client()
        func(client)

        with self.assertRaises(AssertionError):
            client.create_order_request(
                symbol='btc',
                type='limit',
                side='buy',
                amount=2,
                price=3,
                params={ 'priceMatch': 'QUEUE' }
            )
