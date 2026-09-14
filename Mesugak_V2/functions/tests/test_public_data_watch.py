from __future__ import annotations

import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
if str(FUNCTIONS_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_DIR))

from strategy_engine.market_data import PublicDataClient, STOCK_PRICE_URL
from jobs.watch_public_data import poll_once


class _Response:
    def __init__(self, raw: bytes):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.raw


def _payload(rows: list[dict]) -> bytes:
    return json.dumps(
        {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                "body": {"items": {"item": rows}, "totalCount": len(rows)},
            }
        }
    ).encode()


class _FakeDateClient:
    def __init__(self, latest: dt.date):
        self.latest = latest
        self.calls: list[tuple[int, dt.date]] = []

    def latest_stock_date(self, *, max_age_days: int, today: dt.date) -> dt.date:
        self.calls.append((max_age_days, today))
        return self.latest


class PublicDataWatchTests(unittest.TestCase):
    def test_latest_stock_date_uses_one_row_probe(self):
        calls: list[dict[str, list[str]]] = []

        def opener(request, timeout):
            del timeout
            params = parse_qs(urlparse(request.full_url).query)
            calls.append(params)
            requested = params["basDt"][0]
            rows = [{"basDt": "20260909"}] if requested == "20260909" else []
            return _Response(_payload(rows))

        client = PublicDataClient("encoded-key", opener=opener, retries=0, request_delay=0)
        latest = client.latest_stock_date(max_age_days=2, today=dt.date(2026, 9, 10))

        self.assertEqual(latest, dt.date(2026, 9, 9))
        self.assertEqual([params["basDt"][0] for params in calls], ["20260910", "20260909"])
        self.assertTrue(all(params["numOfRows"] == ["1"] for params in calls))
        self.assertEqual(urlparse(STOCK_PRICE_URL).netloc, "apis.data.go.kr")

    def test_unchanged_date_never_starts_pipeline(self):
        now = dt.datetime(2026, 9, 10, 13, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        with tempfile.TemporaryDirectory() as tmp, patch("jobs.watch_public_data.subprocess.run") as run:
            marker = Path(tmp) / "watch.json"
            marker.write_text(json.dumps({"refreshedDate": "2026-09-09"}), encoding="utf-8")
            result = poll_once(
                root=Path(tmp),
                marker_path=marker,
                runner_path=Path(tmp) / "run.sh",
                client=_FakeDateClient(dt.date(2026, 9, 9)),
                now=now,
            )
            state = json.loads(marker.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        run.assert_not_called()
        self.assertEqual(state["status"], "unchanged")

    def test_new_date_runs_once_and_records_success(self):
        now = dt.datetime(2026, 9, 10, 13, 3, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        with tempfile.TemporaryDirectory() as tmp, patch("jobs.watch_public_data.subprocess.run") as run:
            run.return_value.returncode = 0
            marker = Path(tmp) / "watch.json"
            result = poll_once(
                root=Path(tmp),
                marker_path=marker,
                runner_path=Path(tmp) / "run.sh",
                client=_FakeDateClient(dt.date(2026, 9, 10)),
                now=now,
            )

            self.assertEqual(result, 0)
            run.assert_called_once()
            state = json.loads(marker.read_text(encoding="utf-8"))

        self.assertEqual(state["status"], "refreshed")
        self.assertEqual(state["refreshedDate"], "2026-09-10")

    def test_failed_attempt_is_cooled_down(self):
        first = dt.datetime(2026, 9, 10, 13, 3, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        second = first + dt.timedelta(minutes=3)
        with tempfile.TemporaryDirectory() as tmp, patch("jobs.watch_public_data.subprocess.run") as run:
            run.return_value.returncode = 1
            marker = Path(tmp) / "watch.json"
            args = {
                "root": Path(tmp),
                "marker_path": marker,
                "runner_path": Path(tmp) / "run.sh",
                "client": _FakeDateClient(dt.date(2026, 9, 10)),
            }
            self.assertEqual(poll_once(now=first, **args), 1)
            self.assertEqual(poll_once(now=second, **args), 0)
            state = json.loads(marker.read_text(encoding="utf-8"))

        run.assert_called_once()
        self.assertEqual(state["status"], "retry_cooldown")

    def test_used_pacific_quota_day_skips_runner_without_alert_attempt(self):
        now = dt.datetime(2026, 9, 11, 13, 3, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        with tempfile.TemporaryDirectory() as tmp, patch("jobs.watch_public_data.subprocess.run") as run:
            root = Path(tmp)
            cost_dir = root / "runtime" / "cost"
            cost_dir.mkdir(parents=True)
            db = sqlite3.connect(cost_dir / "budget.sqlite3")
            try:
                db.execute("CREATE TABLE budget (day TEXT, key TEXT, used INTEGER, PRIMARY KEY(day,key))")
                db.execute("INSERT INTO budget VALUES ('2026-09-10', 'analysis', 1)")
                db.commit()
            finally:
                db.close()
            marker = root / "runtime" / "watch.json"
            result = poll_once(
                root=root,
                marker_path=marker,
                runner_path=root / "run.sh",
                client=_FakeDateClient(dt.date(2026, 9, 11)),
                now=now,
            )
            state = json.loads(marker.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        run.assert_not_called()
        self.assertEqual(state["status"], "cost_cooldown")
        self.assertEqual(state["costQuotaDay"], "2026-09-10")


if __name__ == "__main__":
    unittest.main()
