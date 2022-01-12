from unittest import TestCase
from src.utils import round_to_execution_start_at


class TestUtilsRoundToExecutionStartAt(TestCase):
    def test_ok(self):
        self.assertEqual(round_to_execution_start_at(0), 1 * 60 * 60)
        self.assertEqual(round_to_execution_start_at(0.1), 1 * 60 * 60)
        self.assertEqual(round_to_execution_start_at(1 * 60 * 60), 1 * 60 * 60)
        self.assertEqual(round_to_execution_start_at(2 * 60 * 60), 1 * 60 * 60)
        self.assertEqual(round_to_execution_start_at(13 * 60 * 60), 25 * 60 * 60)
        self.assertEqual(round_to_execution_start_at(36 * 60 * 60), 25 * 60 * 60)
