"""Accounting and timing controls for Stage 1G; no model or performance tests."""
import unittest
from src.data.return_reconstruction import (
    reconstruct_returns, reconstruct_adjusted_returns,
    rounding_bound, return_span_trading_days,
)


class ReturnReconstructionTests(unittest.TestCase):
    def test_nonordinary_survives_price_return_and_ordinary_only_total(self):
        rx, rt = reconstruct_returns(100, 100, 1, 5, 3)
        self.assertAlmostEqual(rx, 0.05)
        self.assertAlmostEqual(rt, 0.08)

    def test_split_neutrality(self):
        self.assertEqual(reconstruct_returns(50, 100, 2, 0, 0), (0, 0))

    def test_cumulative_distribution_double_count_control(self):
        expected = reconstruct_returns(100, 110, 1, 10, 0)
        adjusted = reconstruct_adjusted_returns(100, 110, 1, 10, 0, 1, 1.1)
        for a, b in zip(adjusted, expected):
            self.assertAlmostEqual(a, b)
        naive = (100/1 + 10/1.1)/(110/1.1)-1
        self.assertNotAlmostEqual(naive, expected[0])

    def test_missing_inputs_and_zero_denominator_are_not_filled(self):
        self.assertEqual(reconstruct_returns(100, 100, 1, None, 0), (None, None))
        self.assertEqual(reconstruct_returns(100, 0, 1, 0, 0), (None, None))
        self.assertEqual(reconstruct_adjusted_returns(100, 100, 1, 0, 0, 1, None), (None, None))

    def test_precision_bound_includes_fractional_previous_price_rounding(self):
        calculated, _ = reconstruct_returns(0.03125, 0.023438, 1, 0, 0)
        error = abs(calculated - 0.333333)
        self.assertGreater(error, 1e-6)
        self.assertLess(error, rounding_bound(0.03125, 0.023438, 1, calculated, 1))

    def test_multi_period_return_is_not_single_day(self):
        self.assertEqual(return_span_trading_days('P1'), 2)
        self.assertEqual(return_span_trading_days('P2'), 3)
        self.assertEqual(return_span_trading_days('D3'), 1)
        self.assertIsNone(return_span_trading_days('DD'))
        self.assertIsNone(return_span_trading_days('MR'))


if __name__ == '__main__':
    unittest.main()
