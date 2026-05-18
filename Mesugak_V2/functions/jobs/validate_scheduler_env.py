"""Validate Mesugak V2 scheduled function environment settings."""

from __future__ import annotations

import argparse
import os


ENV_DEFAULTS = {
    "MESUGAK_MARKET": "KR",
    "MESUGAK_CODES": "",
    "MESUGAK_KR_MARKETS": "KOSPI,KOSDAQ",
    "MESUGAK_MAX_STOCKS": "300",
    "MESUGAK_MAX_POSITIONS": "5",
    "MESUGAK_MIN_CONFIDENCE": "65.0",
    "MESUGAK_MAX_POSITION_WEIGHT": "0.25",
    "MESUGAK_ACCOUNT_VALUE": "10000000",
    "MESUGAK_INITIAL_CASH": "10000000",
    "MESUGAK_META_CHUNK_SIZE": "400",
    "MESUGAK_PROGRESS_INTERVAL": "25",
    "MESUGAK_DRY_RUN": "false",
    "MESUGAK_SKIP_ANALYSIS": "false",
    "MESUGAK_SKIP_REBALANCE": "false",
    "MESUGAK_SKIP_APPLY": "false",
}

INT_KEYS = {"MESUGAK_MAX_STOCKS", "MESUGAK_MAX_POSITIONS", "MESUGAK_META_CHUNK_SIZE", "MESUGAK_PROGRESS_INTERVAL"}
FLOAT_KEYS = {"MESUGAK_MIN_CONFIDENCE", "MESUGAK_MAX_POSITION_WEIGHT", "MESUGAK_ACCOUNT_VALUE", "MESUGAK_INITIAL_CASH"}
BOOL_KEYS = {"MESUGAK_DRY_RUN", "MESUGAK_SKIP_ANALYSIS", "MESUGAK_SKIP_REBALANCE", "MESUGAK_SKIP_APPLY"}


def load_env(path: str | None = None) -> dict[str, str]:
    values = dict(ENV_DEFAULTS)
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                values[key.strip()] = value.strip()
    for key in ENV_DEFAULTS:
        if os.getenv(key) is not None:
            values[key] = os.getenv(key, "")
    return values


def validate_env(values: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for key in INT_KEYS:
        try:
            if int(values.get(key, "")) < 0:
                errors.append(f"{key} must be non-negative")
        except ValueError:
            errors.append(f"{key} must be an integer")
    for key in FLOAT_KEYS:
        try:
            if float(values.get(key, "")) < 0:
                errors.append(f"{key} must be non-negative")
        except ValueError:
            errors.append(f"{key} must be a number")
    for key in BOOL_KEYS:
        if values.get(key, "").lower() not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
            errors.append(f"{key} must be boolean-like")
    if values.get("MESUGAK_MARKET", "").upper() not in {"KR", "US"}:
        errors.append("MESUGAK_MARKET must be KR or US")
    max_weight = float(values.get("MESUGAK_MAX_POSITION_WEIGHT", "0"))
    if max_weight > 1:
        errors.append("MESUGAK_MAX_POSITION_WEIGHT must be <= 1")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate scheduled function environment settings")
    parser.add_argument("--env-file", default="Mesugak_V2/functions/.env.example")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    values = load_env(args.env_file)
    errors = validate_env(values)
    print({"status": "ok" if not errors else "failed", "errors": errors, "values": values})
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
