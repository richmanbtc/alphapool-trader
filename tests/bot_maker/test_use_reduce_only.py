from unittest import TestCase
from parameterized import parameterized
from src.bot_maker import use_reduce_only


def wrap_by_list(x):
    return [x]


class TestBotMakerIsReduceOnly(TestCase):
    @parameterized.expand(map(wrap_by_list, [
        {
            "signed_amount": 0,
            "cur_pos": 0,
            "exchange": None,
            "expected": False,
        },
        {
            "signed_amount": 1,
            "cur_pos": 0,
            "exchange": None,
            "expected": False,
        },
        {
            "signed_amount": -1,
            "cur_pos": 0,
            "exchange": None,
            "expected": False,
        },
        {
            "signed_amount": 1,
            "cur_pos": 1,
            "exchange": None,
            "expected": False,
        },
        {
            "signed_amount": -1,
            "cur_pos": 1,
            "exchange": None,
            "expected": True,
        },
        {
            "signed_amount": -1,
            "cur_pos": 1,
            "exchange": 'bitflyer',
            "expected": False,
        },
        {
            "signed_amount": -10,
            "cur_pos": 1,
            "exchange": None,
            "expected": True,
        },
        {
            "signed_amount": -11,
            "cur_pos": 1,
            "exchange": None,
            "expected": False,
        },
    ]))
    def test_ok(self, params):
        self.assertEqual(use_reduce_only(
            signed_amount=params['signed_amount'],
            cur_pos=params['cur_pos'],
            exchange=params['exchange'],
        ), params['expected'])

        self.assertEqual(use_reduce_only(
            signed_amount=-params['signed_amount'],
            cur_pos=-params['cur_pos'],
            exchange=params['exchange'],
        ), params['expected'])

