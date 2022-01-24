from unittest import TestCase
import os
import pandas as pd
from pandas.testing import assert_frame_equal
from src.agent_api import fetch_target_positions


class TestFetchTargetPositions(TestCase):
    def test_ok(self):
        agent_base_url = os.getenv('ALPHASEA_AGENT_BASE_URL')
        df = fetch_target_positions(
            agent_base_url=agent_base_url,
            timestamp=1
        )

        expected = pd.DataFrame([
        ], columns=['symbol', 'position']).set_index('symbol')
        expected['position'] = expected['position'].astype(float)

        assert_frame_equal(df, expected)
