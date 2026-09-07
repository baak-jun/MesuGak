"""Email the operator when the KR close pipeline fails or stops refreshing."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

KST = ZoneInfo("Asia/Seoul")


def _now() -> dt.datetime:
    return dt.datetime.now(KST)


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _parse_time(value: object) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def _expected_run_date(now: dt.datetime, expected_by: str) -> dt.date:
    hour, minute = (int(part) for part in expected_by.split(":", 1))
    candidate = now.date() if now.time() >= dt.time(hour, minute) else now.date() - dt.timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= dt.timedelta(days=1)
    return candidate


def find_health_issue(
    root: Path,
    market: str,
    now: dt.datetime,
    expected_by: str,
    progress_stale_minutes: int,
) -> tuple[str | None, str]:
    health = _read_json(root / "runtime" / "health" / f"last_success_{market}.json")
    checkpoint = _read_json(root / "runtime" / "checkpoints" / f"analyze_market_{market}.json")
    checkpoint_time = _parse_time(checkpoint.get("updatedAt"))
    checkpoint_status = str(checkpoint.get("status") or "missing")

    if checkpoint_status == "running" and checkpoint_time:
        age_minutes = (now - checkpoint_time).total_seconds() / 60
        if age_minutes > progress_stale_minutes:
            return (
                "checkpoint_stalled",
                f"{market} 분석 체크포인트가 {age_minutes:.0f}분 동안 갱신되지 않았습니다. "
                f"status={checkpoint_status}, updatedAt={checkpoint_time.isoformat(timespec='seconds')}",
            )
    if checkpoint_status == "interrupted":
        return (
            "checkpoint_interrupted",
            f"{market} 분석이 중단 상태입니다. updatedAt={checkpoint.get('updatedAt') or 'unknown'}",
        )

    last_success = _parse_time(health.get("finishedAt"))
    expected_date = _expected_run_date(now, expected_by)
    if not last_success:
        return "success_missing", f"{market} 전체 분석·공개 게시 성공 기록이 없습니다."
    if last_success.date() < expected_date:
        return (
            "publication_stale",
            f"{market} 마지막 전체 분석·공개 게시 성공은 {last_success.isoformat(timespec='seconds')}입니다. "
            f"현재 기대되는 최근 실행일은 {expected_date.isoformat()}입니다.",
        )
    return None, f"{market} 전체 분석·공개 게시가 정상입니다. lastSuccess={last_success.isoformat(timespec='seconds')}"


def send_gmail(subject: str, body: str) -> None:
    user = os.getenv("MESUGAK_GMAIL_USER", "").strip()
    password = os.getenv("MESUGAK_GMAIL_APP_PASSWORD", "").replace(" ", "")
    recipient = os.getenv("MESUGAK_ALERT_EMAIL_TO", user).strip()
    if not user or not password or not recipient:
        raise RuntimeError(
            "Gmail alert settings are missing: MESUGAK_GMAIL_USER, "
            "MESUGAK_GMAIL_APP_PASSWORD, MESUGAK_ALERT_EMAIL_TO"
        )
    message = EmailMessage()
    message["From"] = user
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(message)


def _notify(root: Path, market: str, issue: str, detail: str, now: dt.datetime, force: bool = False) -> bool:
    state_path = root / "runtime" / "health" / f"alert_state_{market}.json"
    state = _read_json(state_path)
    last_sent = _parse_time(state.get("lastSentAt"))
    cooldown_hours = max(1, int(os.getenv("MESUGAK_ALERT_COOLDOWN_HOURS", "12")))
    duplicate = state.get("lastIssue") == issue
    cooling_down = last_sent and (now - last_sent).total_seconds() < cooldown_hours * 3600
    if not force and duplicate and cooling_down:
        print({"status": "alert_suppressed", "issue": issue, "lastSentAt": state.get("lastSentAt")})
        return False

    prefix = os.getenv("MESUGAK_ALERT_SUBJECT_PREFIX", "[MesuGak 학교 서버]").strip()
    send_gmail(f"{prefix} 갱신 이상: {market}", f"{detail}\n\n감지 시각: {now.isoformat(timespec='seconds')}")
    _write_json(
        state_path,
        {"lastIssue": issue, "lastSentAt": now.isoformat(timespec="seconds"), "healthy": False},
    )
    print({"status": "alert_sent", "issue": issue})
    return True


def mark_success(root: Path, market: str, now: dt.datetime) -> None:
    _write_json(
        root / "runtime" / "health" / f"last_success_{market}.json",
        {"market": market, "finishedAt": now.isoformat(timespec="seconds")},
    )


def check(root: Path, market: str, now: dt.datetime) -> int:
    issue, detail = find_health_issue(
        root,
        market,
        now,
        os.getenv("MESUGAK_MONITOR_EXPECTED_BY", "23:30"),
        max(5, int(os.getenv("MESUGAK_MONITOR_PROGRESS_STALE_MINUTES", "90"))),
    )
    state_path = root / "runtime" / "health" / f"alert_state_{market}.json"
    previous = _read_json(state_path)
    if issue:
        _notify(root, market, issue, detail, now)
        return 1
    if previous.get("healthy") is False:
        prefix = os.getenv("MESUGAK_ALERT_SUBJECT_PREFIX", "[MesuGak 학교 서버]").strip()
        send_gmail(f"{prefix} 갱신 복구: {market}", f"{detail}\n\n확인 시각: {now.isoformat(timespec='seconds')}")
    _write_json(state_path, {"lastIssue": None, "lastSentAt": None, "healthy": True})
    print({"status": "healthy", "detail": detail})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor MesuGak school-server refresh health")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--mark-success", action="store_true")
    action.add_argument("--notify-failure", action="store_true")
    action.add_argument("--send-test", action="store_true")
    parser.add_argument("--market", default="KR")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--detail", default="학교 서버 작업이 오류로 종료되었습니다.")
    return parser


def main() -> None:
    functions_dir = Path(__file__).resolve().parents[1]
    load_dotenv(os.getenv("MESUGAK_ENV_FILE") or str(functions_dir / ".env"))
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    market = str(args.market).upper().strip()
    now = _now()
    if args.mark_success:
        mark_success(root, market, now)
        print({"status": "success_marked", "market": market, "finishedAt": now.isoformat(timespec="seconds")})
        return
    if args.notify_failure:
        _notify(root, market, "pipeline_failure", args.detail, now, force=True)
        return
    if args.send_test:
        prefix = os.getenv("MESUGAK_ALERT_SUBJECT_PREFIX", "[MesuGak 학교 서버]").strip()
        send_gmail(
            f"{prefix} Gmail 알림 테스트",
            f"MesuGak 학교 서버의 Gmail 알림 설정이 정상입니다.\n\n확인 시각: {now.isoformat(timespec='seconds')}",
        )
        print({"status": "test_email_sent"})
        return
    raise SystemExit(check(root, market, now))


if __name__ == "__main__":
    main()
