from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
JOBS_DIR = FUNCTIONS_DIR / "jobs"
for path in (FUNCTIONS_DIR, JOBS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from publish_private_performance import run  # noqa: E402


class FakeRepo:
    def __init__(self, account: dict | None):
        self.account = account
        self.saved = None

    def fetch_account_snapshot(self):
        return self.account

    def save_private_paper_performance(self, payload):
        self.saved = payload


class PublishPrivatePerformanceTests(unittest.TestCase):
    def test_job_publishes_admin_only_summary(self) -> None:
        repo = FakeRepo({"market": "KR", "initialCash": 1000, "totalEquity": 1030, "totalPnl": 30, "returnPct": 3.0, "holdingCount": 2})
        args = argparse.Namespace(market="KR", baseline_date="2026-07-01", cred_path=None)

        def loader(label, _baseline):
            return {"label": label, "returnPct": 1.0 if label == "KOSPI" else -1.0, "baselineDate": "2026-07-01", "asOfDate": "2026-07-10", "source": "test"}

        result = run(args, repo=repo, benchmark_loader=loader)

        self.assertEqual(result["status"], "published")
        self.assertEqual(repo.saved["visibility"], "admin_only")
        self.assertEqual(repo.saved["benchmarks"]["KOSPI"]["gapPctPoints"], 2.0)
        self.assertNotIn("holdings", repo.saved)

    def test_job_skips_without_explicit_baseline_date(self) -> None:
        result = run(argparse.Namespace(market="KR", baseline_date="", cred_path=None), repo=FakeRepo(None))
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "baseline_date_not_configured")


if __name__ == "__main__":
    unittest.main()