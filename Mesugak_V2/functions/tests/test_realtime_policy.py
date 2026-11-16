from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.realtime_policy import (  # noqa: E402
    ConfirmationTracker,
    RealtimePolicyConfig,
    RollingQuotes,
    TradeTick,
    candidate_gate,
    entry_signal,
    drawdown_exit,
    exit_reason,
    select_watch_codes,
    should_hold_overnight,
)


def candidate(code: str = "005930") -> dict:
    return {
        "code": code,
        "status": "BUY_CANDIDATE",
        "confidenceScore": 72,
        "currentPrice": 1000,
        "volume": 5_000_000,
        "marcap": 50_000_000_000,
    }


class RealtimePolicyTests(unittest.TestCase):
    def test_new_subscription_does_not_count_the_entire_day_as_recent_volume(self):
        quotes = RollingQuotes()
        quotes.add(TradeTick('005930', 0, 1000, 5_000_000))
        self.assertEqual(quotes.snapshot()['tradeValue30s'], 0)
        quotes.add(TradeTick('005930', 1, 1010, 5_000_100))
        self.assertEqual(quotes.snapshot()['tradeValue30s'], 100 * 1010)
    def test_rolling_quotes_derives_return_value_vwap_and_spread(self) -> None:
        quotes = RollingQuotes()
        quotes.add(TradeTick("005930", 0, 1000, 1000, 1001, 999))
        quotes.add(TradeTick("005930", 1, 1002, 1100, 1003, 1001))
        quotes.add(TradeTick("005930", 11, 1010, 1500, 1011, 1009))
        snapshot = quotes.snapshot()
        self.assertAlmostEqual(snapshot["return10s"], 1010 / 1002 - 1, places=6)
        self.assertEqual(snapshot["tradeValue10s"], 100 * 1002 + 400 * 1010)
        self.assertAlmostEqual(snapshot["spreadPct"], 2 / 1009, places=6)
        self.assertGreater(snapshot["vwap30s"], 0)

    def test_candidate_gate_enforces_daily_status_and_liquidity(self) -> None:
        ok, reason = candidate_gate(candidate(), RealtimePolicyConfig())
        self.assertTrue(ok)
        self.assertEqual(reason, "daily_gate")
        rejected = candidate()
        rejected["status"] = "WATCH"
        self.assertEqual(candidate_gate(rejected, RealtimePolicyConfig())[1], "daily_status")

    def test_score_entry_is_immediate_without_momentum_or_daily_label_filters(self) -> None:
        cfg = RealtimePolicyConfig()
        quote = {'ready': True, 'price': 1000, 'liveScoreReady': True, 'liveConfidenceScore': 58.0}
        self.assertEqual(entry_signal({**candidate(), 'status': 'WATCH', 'confidenceScore': 10}, quote, cfg), (True, 'live_score_entry'))
        self.assertFalse(entry_signal(candidate(), {**quote, 'liveConfidenceScore': 57.99}, cfg)[0])
        self.assertFalse(entry_signal(candidate(), {**quote, 'liveScoreReady': False}, cfg)[0])

    def test_partial_drawdown_occurs_once_and_gap_goes_directly_to_full_exit(self):
        self.assertIsNone(drawdown_exit(98.21, 100, False))
        self.assertEqual(drawdown_exit(98.2, 100, False), ('monitored_high_partial_exit', .5))
        self.assertIsNone(drawdown_exit(98.1, 100, True))
        self.assertEqual(drawdown_exit(97, 100, True), ('monitored_high_full_exit', 1.0))
        self.assertEqual(drawdown_exit(95, 100, False), ('monitored_high_full_exit', 1.0))

    def test_confirmation_requires_two_positive_evaluations(self) -> None:
        tracker = ConfirmationTracker()
        cfg = RealtimePolicyConfig()
        self.assertFalse(tracker.confirm("005930", True, 10, cfg))
        self.assertTrue(tracker.confirm("005930", True, 12, cfg))
        self.assertFalse(tracker.confirm("005930", False, 13, cfg))

    def test_exit_rules_and_overnight_filter(self) -> None:
        today = date(2026, 9, 23)
        position = {"buyPrice": 100, "highestPrice": 100, "boughtAt": "2026-09-23T09:00:00+09:00"}
        stop = {"ready": True, "price": 96, "return10s": 0, "vwap30s": 100}
        self.assertEqual(exit_reason(position, stop, session_date=today), "same_day_stop_loss")
        trail = {"ready": True, "price": 110, "return10s": 0, "vwap30s": 100}
        high_position = {"buyPrice": 100, "highestPrice": 120, "boughtAt": "2026-09-22T09:00:00+09:00"}
        self.assertEqual(exit_reason(high_position, trail), "trailing_stop")
        lock = {"ready": True, "price": 107.5, "return10s": 0, "vwap30s": 105}
        lock_position = {"buyPrice": 100, "highestPrice": 110, "boughtAt": "2026-09-22T09:00:00+09:00"}
        self.assertEqual(exit_reason(lock_position, lock), "profit_lock_trailing_stop")
        reversal = {"ready": True, "price": 108.5, "return10s": -0.01, "vwap30s": 110}
        self.assertEqual(exit_reason({**high_position, "highestPrice": 110}, reversal), "momentum_reversal")
        self.assertTrue(should_hold_overnight({"buyPrice": 100}, {**candidate(), "confidenceScore": 70}, {"price": 110, "vwap60s": 105, "return30s": 0.01}))

    def test_watch_list_keeps_held_symbols_first_and_is_bounded(self) -> None:
        rows = [candidate("A"), candidate("B"), candidate("C")]
        self.assertEqual(select_watch_codes(rows, ["C"], max_codes=2, exploration_count=0), ["C", "A"])

    def test_core_floor_keeps_exactly_55_and_protects_weak_holdings(self):
        rows = [{**candidate(code), 'confidenceScore': score} for code, score in [('A', 54.99), ('B', 55), ('C', 60), ('H', 10)]]
        self.assertEqual(select_watch_codes(rows, ['H'], max_codes=4, exploration_count=0, minimum_score=55), ['H', 'C', 'B'])

    def test_eighteen_high_scores_and_two_explorers_do_not_displace_holdings(self):
        rows = [{**candidate(str(i)), 'confidenceScore': 100 - i} for i in range(40)]
        watch = select_watch_codes(rows, [], max_codes=20, exploration_codes=['30', '31', '32'], exploration_count=2)
        self.assertEqual(watch, [str(i) for i in range(18)] + ['30', '31'])
        watch = select_watch_codes(rows, ['39'], max_codes=20, exploration_codes=['30', '31'], exploration_count=2)
        self.assertEqual(watch, ['39'] + [str(i) for i in range(17)] + ['30', '31'])
        with self.assertRaises(ValueError):
            select_watch_codes(rows, ['A', 'B', 'C'], max_codes=2)


if __name__ == "__main__":
    unittest.main()
