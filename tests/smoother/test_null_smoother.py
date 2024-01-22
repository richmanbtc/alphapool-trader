from unittest import TestCase
from src.smoother import NullSmoother


class TestSmootherStep(TestCase):
    def test_ok(self):
        smoother = NullSmoother()
        self.assertEqual(smoother.step('BTC', 1, t=1), 1)
        self.assertEqual(smoother.step('BTC', 2, t=11), 2)
        self.assertEqual(smoother.step('ETH', 2, t=11), 2)
