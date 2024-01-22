from unittest import TestCase
import os
import tempfile
import json
from src.logger import create_logger
from src.smoother import Smoother


class TestSmootherInit(TestCase):
    def test_ok(self):
        logger = create_logger('debug')
        smoother = Smoother(
            logger=logger,
            halflife=10,
            reset_threshold=0.2,
            save_path=None
        )
        self.assertEqual(smoother._states, {})

    def test_file_broken(self):
        logger = create_logger('debug')
        smoother = Smoother(
            logger=logger,
            halflife=10,
            reset_threshold=0.2,
            save_path='./LICENSE'
        )
        self.assertEqual(smoother._states, {})

    def test_invalid_format(self):
        logger = create_logger('debug')
        with tempfile.TemporaryDirectory() as dir:
            tmp_path = os.path.join(dir, 'states.json')
            with open(tmp_path, 'w') as f:
                json.dump({ 'BTC': {} }, f)
            smoother = Smoother(
                logger=logger,
                halflife=10,
                reset_threshold=0.2,
                save_path=tmp_path,
            )
        self.assertEqual(smoother._states, {})

    def test_valid_format(self):
        logger = create_logger('debug')
        with tempfile.TemporaryDirectory() as dir:
            tmp_path = os.path.join(dir, 'states.json')
            with open(tmp_path, 'w') as f:
                json.dump({ 'BTC': { 'value': 1.2, 't': 3.4 } }, f)
            smoother = Smoother(
                logger=logger,
                halflife=10,
                reset_threshold=0.2,
                save_path=tmp_path,
            )
        self.assertEqual(smoother._states, { 'BTC': { 'value': 1.2, 't': 3.4 } })
