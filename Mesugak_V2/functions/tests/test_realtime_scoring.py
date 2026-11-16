from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strategy_engine.realtime_scoring import valid_history, score_live_history
from strategy_engine.realtime_policy import TradeTick


class RealtimeScoringTests(unittest.TestCase):
    def history(self):
        closes = [100 + i * .2 for i in range(160)]
        return pd.DataFrame({'date': pd.date_range('2026-01-01', periods=160),
                             'open': closes, 'high': [x + 1 for x in closes],
                             'low': [x - 1 for x in closes], 'close': closes, 'volume': 10000})

    def test_real_quote_changes_score_without_altering_completed_candles(self):
        history = valid_history(self.history().to_dict('records'), date(2026, 10, 12))
        original = history.copy(deep=True)
        up = score_live_history(history, TradeTick('A', 1, 145, 60000, day_open=132, day_high=145, day_low=131), date(2026, 10, 12))
        down = score_live_history(history, TradeTick('A', 2, 100, 65000, day_open=132, day_high=145, day_low=100), date(2026, 10, 12))
        self.assertTrue(up['liveScoreReady'])
        self.assertGreater(up['liveConfidenceScore'], down['liveConfidenceScore'])
        self.assertEqual(up['scoreSessionDate'], '2026-10-12')
        pd.testing.assert_frame_equal(history, original)

    def test_invalid_zero_history_and_incomplete_history_cannot_create_a_live_score(self):
        rows = self.history().to_dict('records')
        for row in rows[:50]:
            row['close'] = 0
        with self.assertRaises(ValueError):
            valid_history(rows, date(2026, 10, 12))
        with self.assertRaises(ValueError):
            valid_history(self.history().tail(50).to_dict('records'), date(2026, 10, 12))

    def test_todays_completed_row_is_not_counted_twice(self):
        rows = self.history().to_dict('records')
        rows.append({**rows[-1], 'date': '2026-10-12'})
        history = valid_history(rows, date(2026, 10, 12))
        self.assertEqual(len(history), 160)


if __name__ == '__main__':
    unittest.main()
