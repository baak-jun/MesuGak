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


if __name__ == "__main__":
    unittest.main()
