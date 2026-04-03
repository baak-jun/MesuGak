import argparse
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from dotenv import load_dotenv

from local_chart_refresh import (
    parse_kr_markets,
    parse_markets,
    refresh_pending_orders,
    resolve_cred_path,
    resolve_market_max_stocks,
    run_chart_refresh,
    init_firestore,
    strtobool_env,
)

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_RUNTIME_DIR = Path(os.getenv("BOT_RUNTIME_DIR", "/home/ubuntu/mesugak-runtime")).expanduser()
DEFAULT_CHECKPOINT_DIR = DEFAULT_RUNTIME_DIR / "checkpoints"
DEFAULT_LOG_DIR = DEFAULT_RUNTIME_DIR / "logs"
DEFAULT_LOCK_FILE = DEFAULT_RUNTIME_DIR / "oracle_chart_refresh.lock"
DEFAULT_ENV_PATH = BASE_DIR / ".env.oracle"


class TeeWriter:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


@contextmanager
def file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        if fcntl is not None:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(f"Another chart refresh is already running: {lock_path}") from exc
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def tee_stdout(log_dir: Path) -> Iterator[Path]:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"oracle_chart_refresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    with log_path.open("a", encoding="utf-8") as fh:
        tee = TeeWriter(original_stdout, fh)
        sys.stdout = tee
        sys.stderr = tee
        try:
            yield log_path
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Oracle Free Tier wrapper for local_chart_refresh.py"
    )
    parser.add_argument(
        "--env-file",
        default=os.getenv("BOT_ENV_FILE", str(DEFAULT_ENV_PATH if DEFAULT_ENV_PATH.exists() else "")) or None,
        help="Optional env file path for OCI runtime",
    )
    parser.add_argument(
        "--market",
        default=os.getenv("BOT_MARKET", "KR,US"),
        help="Single market or comma-separated markets, e.g. KR or KR,US",
    )
    parser.add_argument(
        "--kr-markets",
        default=os.getenv("BOT_KR_MARKETS") or "KOSPI,KOSDAQ",
        help="Comma-separated KR submarkets",
    )
    parser.add_argument("--cred-path", default=os.getenv("BOT_FIREBASE_CRED_PATH") or None)
    parser.add_argument(
        "--checkpoint-dir",
        default=os.getenv("BOT_CHECKPOINT_DIR", str(DEFAULT_CHECKPOINT_DIR)),
        help="Checkpoint directory for OCI runtime",
    )
    parser.add_argument(
        "--log-dir",
        default=os.getenv("BOT_LOG_DIR", str(DEFAULT_LOG_DIR)),
        help="Directory for execution logs",
    )
    parser.add_argument(
        "--lock-file",
        default=os.getenv("BOT_LOCK_FILE", str(DEFAULT_LOCK_FILE)),
        help="Single-instance lock file path",
    )
    parser.add_argument(
        "--max-stocks",
        type=int,
        default=None,
        help="Optional per-market CLI override",
    )
    parser.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="Ignore today's checkpoint and start over",
    )
    parser.add_argument(
        "--skip-pending-orders",
        action="store_true",
        default=strtobool_env(os.getenv("BOT_SKIP_PENDING_ORDERS", "false")),
        help="Skip pending_orders refresh after chart refresh",
    )
    return parser


def resolve_default_env_file() -> Optional[str]:
    if os.getenv("BOT_ENV_FILE"):
        return os.getenv("BOT_ENV_FILE")
    if DEFAULT_ENV_PATH.exists():
        return str(DEFAULT_ENV_PATH)
    return None


def bootstrap_env_file() -> Optional[str]:
    bootstrap_parser = argparse.ArgumentParser(add_help=False)
    bootstrap_parser.add_argument("--env-file", default=resolve_default_env_file())
    args, _ = bootstrap_parser.parse_known_args()
    return args.env_file


def load_runtime_env(env_file: Optional[str]) -> None:
    load_dotenv()
    load_dotenv(BASE_DIR / ".env")
    if env_file:
        load_dotenv(Path(env_file).expanduser(), override=True)


def main() -> None:
    env_file = bootstrap_env_file()
    load_runtime_env(env_file)
    args = build_parser().parse_args()

    lock_path = Path(args.lock_file).expanduser()
    log_dir = Path(args.log_dir).expanduser()

    with file_lock(lock_path):
        with tee_stdout(log_dir) as log_path:
            print(f"[OCI_CHART] log_path={log_path}")
            print(f"[OCI_CHART] pid={os.getpid()}")

            cred_path = resolve_cred_path(args.cred_path)
            db = init_firestore(cred_path)

            markets = parse_markets(args.market)
            kr_markets = parse_kr_markets(args.kr_markets)

            print(f"[OCI_CHART] markets={markets}")
            print(f"[OCI_CHART] checkpoint_dir={args.checkpoint_dir}")
            if kr_markets:
                print(f"[OCI_CHART] kr_markets={kr_markets}")

            for market in markets:
                market_max_stocks = resolve_market_max_stocks(market, args.max_stocks)
                print(f"[OCI_CHART] start market={market} max_stocks={market_max_stocks or 'ALL'}")

                run_chart_refresh(
                    db,
                    market=market,
                    max_stocks=market_max_stocks,
                    checkpoint_dir=args.checkpoint_dir,
                    reset_checkpoint=args.reset_checkpoint,
                    kr_markets=kr_markets if market == "KR" else None,
                )

                if not args.skip_pending_orders:
                    if refresh_pending_orders is None:
                        print("[OCI_CHART] skip pending_orders: local_refresh_pending_orders.py not found")
                    else:
                        refresh_pending_orders(db, market=market, dry_run=False)

            print("[OCI_CHART] all markets completed")


if __name__ == "__main__":
    main()
