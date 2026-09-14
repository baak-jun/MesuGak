"""Root wrapper for Mesugak V2 analyze_market job.

Executes the active V2 analyze_market job directly to ensure
batched writes and consistent environment configuration.
"""
from __future__ import annotations

import sys
from pathlib import Path

V2_JOB_DIR = Path(__file__).resolve().parent / "Mesugak_V2" / "functions" / "jobs"
if str(V2_JOB_DIR) not in sys.path:
    sys.path.insert(0, str(V2_JOB_DIR))

import analyze_market

if __name__ == "__main__":
    analyze_market.main()
