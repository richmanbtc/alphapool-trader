from unittest import TestCase
from unittest.mock import MagicMock
from src.utils import fetch_collateral
import pandas as pd
from pandas.testing import assert_frame_equal

# https://docs.ftx.com/#get-account-information

response = {
    'result': {
        'collateral': 1
    },
}


class TestUtilsFetchCollateral(TestCase):
    def test_ok(self):
        client = MagicMock()
        client.id = 'ftx'
        client.privateGetAccount.return_value = response

        collateral = fetch_collateral(client)
        self.assertEqual(collateral, 1)
