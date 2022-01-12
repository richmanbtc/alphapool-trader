from unittest import TestCase
import os
import pandas as pd
from pandas.testing import assert_frame_equal
from src.agent_api import fetch_blended_prediction


class TestFetchBlendedPrediction(TestCase):
    def test_ok(self):
        agent_base_url = os.getenv('ALPHASEA_AGENT_BASE_URL')
        df = fetch_blended_prediction(
            agent_base_url=agent_base_url,
            execution_start_at=1
        )

        expected = pd.DataFrame([
        ], columns=['symbol', 'position']).set_index('symbol')

        assert_frame_equal(df, expected)
