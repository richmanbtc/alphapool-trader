from unittest import TestCase
from src.utils import normalize_amount

market = {
    'limits': {
        'amount': {
            'min': 1,
            'max': 10,
        },
        'cost': {
            'min': 2
        }
    },
    'precision': {
        'amount': 0.5,
    }
}


class TestUtilsNormalizeAmount(TestCase):
    def test_ok(self):
        self.assertEqual(normalize_amount(1, price=4, market=market), 1)

    def test_cost_min(self):
        self.assertEqual(normalize_amount(1, price=3, market=market), 0)

    def test_amount_min(self):
        self.assertEqual(normalize_amount(0.5, price=8, market=market), 0)

    def test_amount_max(self):
        self.assertEqual(normalize_amount(11, price=4, market=market), 10)

    def test_precision(self):
        self.assertEqual(normalize_amount(1.3, price=4, market=market), 1.5)

    def test_negative(self):
        self.assertEqual(normalize_amount(-1, price=4, market=market), -1)
