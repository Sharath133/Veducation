"""Unit tests for settlement prize math (stdlib only)."""
import unittest
from decimal import Decimal

from app.services.settlement_prize_math import split_prize_pool_rupees


class TestSplitPrizePool(unittest.TestCase):
    def test_equal_split_three_way(self):
        parts = split_prize_pool_rupees(Decimal("10.00"), 3)
        self.assertEqual(len(parts), 3)
        self.assertEqual(sum(parts), Decimal("10.00"))

    def test_zero_pool_returns_zeros(self):
        parts = split_prize_pool_rupees(Decimal("0"), 4)
        self.assertEqual(parts, [Decimal("0")] * 4)

    def test_paise_remainder_distribution(self):
        parts = split_prize_pool_rupees(Decimal("1.01"), 2)
        self.assertEqual(sum(parts), Decimal("1.01"))


if __name__ == "__main__":
    unittest.main()
