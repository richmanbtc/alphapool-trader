from unittest import TestCase
from unittest.mock import MagicMock
from src.utils import fetch_positions
import pandas as pd
from pandas.testing import assert_frame_equal

# https://github.com/ccxt/ccxt/wiki/Manual#position-structure
# https://github.com/ccxt/ccxt/blob/81c44dfdcd6729ef5b4e10635919571de4e0d82f/python/ccxt/ftx.py#L1852

response = [{
    'symbol': 'BTC/USD:USD',
    'side': 'long',
    'contracts': 1,
}, {
    'symbol': 'ETH/USD:USD',
    'side': 'short',
    'contracts': 2,
}]


class TestUtilsFetchPositions(TestCase):
    def test_ok(self):
        client = MagicMock()
        client.fetch_positions.return_value = response

        df = fetch_positions(client)

        expected = pd.DataFrame([
            ['BTC/USD:USD', 1],
            ['ETH/USD:USD', -2],
        ], columns=['symbol', 'position']).set_index('symbol')

        assert_frame_equal(df, expected)
