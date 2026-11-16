from __future__ import annotations

import ast
import unittest
from pathlib import Path


FUNCTIONS_DIR = Path(__file__).resolve().parents[1]
PUBLIC_PIPELINE = (
    FUNCTIONS_DIR / "jobs" / "analyze_market.py",
    FUNCTIONS_DIR / "jobs" / "publish_public_analysis.py",
    FUNCTIONS_DIR / "strategy_engine" / "market_data.py",
)
KIS_PAPER_RUNTIME = frozenset(
    {
        FUNCTIONS_DIR / "jobs" / "school_paper_trader.py",
        FUNCTIONS_DIR / "jobs" / "manual_kis_order.py",
        FUNCTIONS_DIR / "jobs" / "kis_realtime_trader.py",
        FUNCTIONS_DIR / "jobs" / "contest_market_scan.py",
        FUNCTIONS_DIR / "jobs" / "contest_daily_report.py",
        FUNCTIONS_DIR / "strategy_engine" / "kis_paper.py",
        FUNCTIONS_DIR / "strategy_engine" / "kis_realtime.py",
    }
)
BANNED_PROVIDERS = ("financedatareader", "yfinance", "pykrx", "pandas_datareader", "investpy")


class DataSourceBoundaryTests(unittest.TestCase):
    def test_public_pipeline_has_no_unofficial_or_kis_imports(self) -> None:
        for path in PUBLIC_PIPELINE:
            source = path.read_text(encoding="utf-8")
            lowered = source.lower()
            self.assertFalse(any(provider in lowered for provider in BANNED_PROVIDERS), path.name)

            imported = []
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.append(node.module or "")
            self.assertFalse(any("kis" in module.lower() for module in imported), path.name)

    def test_daily_analysis_does_not_duplicate_full_candidate_snapshots(self) -> None:
        source = (FUNCTIONS_DIR / "jobs" / "analyze_market.py").read_text(encoding="utf-8")
        self.assertNotIn("save_strategy_candidate", source)

    def test_kis_client_is_isolated_to_paper_runtime(self) -> None:
        """Keep brokerage credentials and calls out of every non-paper job."""
        for path in FUNCTIONS_DIR.rglob("*.py"):
            if "tests" in path.parts:
                continue
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports_kis = any(
                isinstance(node, ast.ImportFrom)
                and (node.module or "").lower().endswith("kis_paper")
                for node in ast.walk(tree)
            ) or any(
                isinstance(node, ast.Import)
                and any(alias.name.lower().endswith("kis_paper") for alias in node.names)
                for node in ast.walk(tree)
            )
            imports_client = any(
                isinstance(node, ast.ImportFrom)
                and any(alias.name in {"KISPaperClient", "KISPaperConfig"} for alias in node.names)
                for node in ast.walk(tree)
            )
            if imports_kis or imports_client:
                self.assertIn(path, KIS_PAPER_RUNTIME, path.name)

        worker = (FUNCTIONS_DIR / "jobs" / "school_paper_trader.py").read_text(encoding="utf-8")
        self.assertIn("client.fetch_balance", worker)
        self.assertIn("client.submit_market_order", worker)
        self.assertIn("client.quote", worker)


if __name__ == "__main__":
    unittest.main()
