from unittest import TestCase
import os
import tempfile
import json
from src.logger import create_logger
from src.smoother import Smoother


class TestSmootherStep(TestCase):
    def test_ok(self):
        logger = create_logger('debug')
        with tempfile.TemporaryDirectory() as dir:
            tmp_path = os.path.join(dir, 'states.json')
            smoother = Smoother(
                logger=logger,
                halflife=10,
                reset_threshold=100,
                save_path=tmp_path,
            )
            self.assertEqual(smoother.step('BTC', 1, t=1), 1)
            self.assertEqual(smoother.step('BTC', 2, t=11), 1.5)
            self.assertEqual(smoother._states, { 'BTC': { 'value': 1.5, 't': 11 } })
            with open(tmp_path) as f:
                self.assertEqual(json.load(f), { 'BTC': { 'value': 1.5, 't': 11 } })

    def test_restart(self):
        logger = create_logger('debug')
        with tempfile.TemporaryDirectory() as dir:
            tmp_path = os.path.join(dir, 'states.json')
            smoother = Smoother(
                logger=logger,
                halflife=10,
                reset_threshold=100,
                save_path=tmp_path,
            )
            self.assertEqual(smoother.step('BTC', 1, t=1), 1)
            smoother = Smoother(
                logger=logger,
                halflife=10,
                reset_threshold=100,
                save_path=tmp_path,
            )
            self.assertEqual(smoother.step('BTC', 2, t=11), 1.5)
            self.assertEqual(smoother._states, { 'BTC': { 'value': 1.5, 't': 11 } })

    def test_reset_too_big(self):
        logger = create_logger('debug')
        smoother = Smoother(
            logger=logger,
            halflife=10,
            reset_threshold=0.2,
            save_path=None,
        )
        self.assertEqual(smoother.step('BTC', 10, t=1), 10)
        self.assertEqual(smoother.step('ETH', 20, t=5), 20)
        self.assertEqual(smoother.step('BTC', 12, t=11), 11)
        self.assertEqual(smoother.step('ETH', 24.01, t=11), 24.01) # reset
        self.assertEqual(smoother._states, { 'ETH': { 'value': 24.01, 't': 11 } })

    def test_reset_too_small(self):
        logger = create_logger('debug')
        smoother = Smoother(
            logger=logger,
            halflife=10,
            reset_threshold=0.2,
            save_path=None,
        )
        self.assertEqual(smoother.step('BTC', 10, t=1), 10)
        self.assertEqual(smoother.step('ETH', 20, t=5), 20)
        self.assertEqual(smoother.step('BTC', 8, t=11), 9)
        self.assertEqual(smoother.step('ETH', 15.99, t=11), 15.99) # reset
        self.assertEqual(smoother._states, { 'ETH': { 'value': 15.99, 't': 11 } })

    def test_various_t(self):
        logger = create_logger('debug')
        smoother = Smoother(
            logger=logger,
            halflife=10,
            reset_threshold=100,
            save_path=None,
        )
        self.assertEqual(smoother.step('BTC', 20, t=1), 20)
        self.assertEqual(smoother.step('BTC', 40, t=21), 35)
