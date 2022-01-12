from unittest import TestCase
from src.utils import round_precision


class TestUtilsRoundPrecision(TestCase):
    def test_int(self):
        self.assertEqual(round_precision(12.34, 0), 12)
        self.assertEqual(round_precision(12.34, 1), 12.3)
        self.assertEqual(round_precision(12.34, 2), 12.34)

    def test_float(self):
        self.assertEqual(round_precision(12.34, 1.0), 12)
        self.assertEqual(round_precision(12.34, 0.5), 12.5)
        self.assertAlmostEqual(round_precision(12.34, 0.05), 12.35)

