from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))

import monitor_school_server as monitor  # noqa: E402
from monitor_school_server import KST, find_health_issue, mark_success  # noqa: E402


class SchoolServerMonitorTests(unittest.TestCase):
    def test_success_from_friday_is_current_during_weekend(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mark_success(root, "KR", dt.datetime(2026, 8, 28, 20, 0, tzinfo=KST))

            issue, _ = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 30, 23, 40, tzinfo=KST), "23:30", 90
            )

            self.assertIsNone(issue)

    def test_stale_running_checkpoint_is_reported_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = root / "runtime" / "checkpoints" / "analyze_market_KR.json"
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text(
                json.dumps({"status": "running", "updatedAt": "2026-08-31T18:00:00+09:00"}),
                encoding="utf-8",
            )

            issue, _ = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 31, 20, 0, tzinfo=KST), "23:30", 90
            )

            self.assertEqual(issue, "checkpoint_stalled")

    def test_previous_business_day_missing_is_reported_after_deadline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mark_success(root, "KR", dt.datetime(2026, 8, 28, 20, 0, tzinfo=KST))

            issue, _ = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 31, 23, 40, tzinfo=KST), "23:30", 90
            )

            self.assertEqual(issue, "publication_stale")

    def test_recent_unchanged_provider_date_suppresses_holiday_like_stale_alert(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mark_success(root, "KR", dt.datetime(2026, 8, 28, 20, 0, tzinfo=KST))
            watch = root / "runtime" / "watch" / "public_data_KR.json"
            watch.parent.mkdir(parents=True, exist_ok=True)
            watch.write_text(
                json.dumps(
                    {
                        "status": "unchanged",
                        "latestAvailableDate": "2026-08-28",
                        "checkedAt": "2026-08-31T23:35:00+09:00",
                    }
                ),
                encoding="utf-8",
            )

            issue, detail = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 31, 23, 40, tzinfo=KST), "23:30", 90
            )

            self.assertIsNone(issue)
            self.assertIn("새 거래일 데이터가 없습니다", detail)

    def test_failed_provider_watcher_does_not_hide_publication_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mark_success(root, "KR", dt.datetime(2026, 8, 28, 20, 0, tzinfo=KST))
            watch = root / "runtime" / "watch" / "public_data_KR.json"
            watch.parent.mkdir(parents=True, exist_ok=True)
            watch.write_text(
                json.dumps(
                    {
                        "status": "poll_failed",
                        "latestAvailableDate": "2026-08-28",
                        "checkedAt": "2026-08-31T23:35:00+09:00",
                    }
                ),
                encoding="utf-8",
            )

            issue, _ = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 31, 23, 40, tzinfo=KST), "23:30", 90
            )

            self.assertEqual(issue, "publication_stale")

    def test_old_unchanged_provider_probe_does_not_hide_publication_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mark_success(root, "KR", dt.datetime(2026, 8, 28, 20, 0, tzinfo=KST))
            watch = root / "runtime" / "watch" / "public_data_KR.json"
            watch.parent.mkdir(parents=True, exist_ok=True)
            watch.write_text(
                json.dumps(
                    {
                        "status": "unchanged",
                        "latestAvailableDate": "2026-08-28",
                        "checkedAt": "2026-08-31T20:59:00+09:00",
                    }
                ),
                encoding="utf-8",
            )

            issue, _ = find_health_issue(
                root, "KR", dt.datetime(2026, 8, 31, 23, 40, tzinfo=KST), "23:30", 90
            )

            self.assertEqual(issue, "publication_stale")

    def test_cost_guard_failure_is_reported_before_stale_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mark_success(root, "KR", dt.datetime(2026, 8, 31, 20, 0, tzinfo=KST))
            status = root / "runtime" / "cost" / "status.json"
            status.parent.mkdir(parents=True, exist_ok=True)
            status.write_text(json.dumps({"blocked": True, "reason": "storage limit"}), encoding="utf-8")

            issue, detail = find_health_issue(
                root, "KR", dt.datetime(2026, 9, 1, 10, 0, tzinfo=KST), "23:30", 90
            )

            self.assertEqual(issue, "cost_guard_blocked")
            self.assertIn("storage limit", detail)

    def test_pipeline_alerts_share_one_incident_during_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = dt.datetime(2026, 9, 1, 13, 30, tzinfo=KST)
            second = first + dt.timedelta(minutes=5)
            with patch("monitor_school_server.send_gmail") as send_gmail:
                self.assertTrue(
                    monitor._notify(root, "KR", "checkpoint_interrupted", "interrupted", first)
                )
                self.assertFalse(
                    monitor._notify(root, "KR", "pipeline_failure", "wrapper failed", second, force=True)
                )

            self.assertEqual(send_gmail.call_count, 1)
            state = json.loads(
                (root / "runtime" / "health" / "alert_state_KR.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["incidentKey"], "analysis_pipeline")


if __name__ == "__main__":
    unittest.main()
