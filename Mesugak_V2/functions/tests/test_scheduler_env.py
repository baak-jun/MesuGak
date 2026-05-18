from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "jobs"))

from validate_scheduler_env import load_env, validate_env  # noqa: E402


class SchedulerEnvTests(unittest.TestCase):
    def test_env_example_is_valid(self) -> None:
        values = load_env("Mesugak_V2/functions/.env.example")

        self.assertEqual(validate_env(values), [])

    def test_invalid_env_reports_errors(self) -> None:
        values = load_env("Mesugak_V2/functions/.env.example")
        values["MESUGAK_MARKET"] = "JP"
        values["MESUGAK_MAX_STOCKS"] = "many"
        values["MESUGAK_DRY_RUN"] = "maybe"
        values["MESUGAK_MAX_POSITION_WEIGHT"] = "2"

        errors = validate_env(values)

        self.assertIn("MESUGAK_MARKET must be KR or US", errors)
        self.assertIn("MESUGAK_MAX_STOCKS must be an integer", errors)
        self.assertIn("MESUGAK_DRY_RUN must be boolean-like", errors)
        self.assertIn("MESUGAK_MAX_POSITION_WEIGHT must be <= 1", errors)


if __name__ == "__main__":
    unittest.main()
