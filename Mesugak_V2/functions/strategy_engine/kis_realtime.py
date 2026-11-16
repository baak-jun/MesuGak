"""KIS virtual-investment WebSocket framing and lightweight stream client."""

from __future__ import annotations

import base64
import asyncio
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .kis_paper import KISPaperClient
from .realtime_policy import TradeTick


TRADE_COLUMNS = [
    "MKSC_SHRN_ISCD", "STCK_CNTG_HOUR", "STCK_PRPR", "PRDY_VRSS_SIGN",
    "PRDY_VRSS", "PRDY_CTRT", "WGHN_AVRG_STCK_PRC", "STCK_OPRC",
    "STCK_HGPR", "STCK_LWPR", "ASKP1", "BIDP1", "CNTG_VOL", "ACML_VOL",
    "ACML_TR_PBMN", "SELN_CNTG_CSNU", "SHNU_CNTG_CSNU", "NTBY_CNTG_CSNU",
    "CTTR", "SELN_CNTG_SMTN", "SHNU_CNTG_SMTN", "CCLD_DVSN", "SHNU_RATE",
    "PRDY_VOL_VRSS_ACML_VOL_RATE", "OPRC_HOUR", "OPRC_VRSS_PRPR_SIGN",
    "OPRC_VRSS_PRPR", "HGPR_HOUR", "HGPR_VRSS_PRPR_SIGN", "HGPR_VRSS_PRPR",
    "LWPR_HOUR", "LWPR_VRSS_PRPR_SIGN", "LWPR_VRSS_PRPR", "BSOP_DATE",
    "NEW_MKOP_CLS_CODE", "TRHT_YN", "ASKP_RSQN1", "BIDP_RSQN1",
    "TOTAL_ASKP_RSQN", "TOTAL_BIDP_RSQN", "VOL_TNRT",
    "PRDY_SMNS_HOUR_ACML_VOL", "PRDY_SMNS_HOUR_ACML_VOL_RATE",
    "HOUR_CLS_CODE", "MRKT_TRTM_CLS_CODE", "VI_STND_PRC",
]

NOTICE_COLUMNS = [
    "CUST_ID", "ACNT_NO", "ODER_NO", "OODER_NO", "SELN_BYOV_CLS",
    "RCTF_CLS", "ODER_KIND", "ODER_COND", "STCK_SHRN_ISCD", "CNTG_QTY",
    "CNTG_UNPR", "STCK_CNTG_HOUR", "RFUS_YN", "CNTG_YN", "ACPT_YN",
    "BRNC_NO", "ODER_QTY", "ACNT_NAME", "ORD_COND_PRC", "ORD_EXG_GB",
    "POPUP_YN", "FILLER", "CRDT_CLS", "CRDT_LOAN_DATE", "CNTG_ISNM40",
    "ODER_PRC",
]


def _float(value: Any) -> float:
    try:
        return float(str(value or "0").replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def subscription_message(approval_key: str, tr_id: str, tr_key: str, *, tr_type: str = "1") -> str:
    if not approval_key or not tr_id or not tr_key:
        raise ValueError("KIS subscription requires approval_key, tr_id, and tr_key")
    return json.dumps(
        {
            "header": {
                "approval_key": approval_key,
                "custtype": "P",
                "tr_type": str(tr_type),
                "content-type": "utf-8",
            },
            "body": {"input": {"tr_id": str(tr_id), "tr_key": str(tr_key)}},
        },
        ensure_ascii=False,
    )


def _decrypt_aes_cbc(cipher_text: str, key: str, iv: str) -> str:
    raw = base64.b64decode(cipher_text)
    key_bytes = key.encode("utf-8")
    iv_bytes = iv.encode("utf-8")
    try:
        from Crypto.Cipher import AES  # type: ignore
        from Crypto.Util.Padding import unpad  # type: ignore

        return unpad(AES.new(key_bytes, AES.MODE_CBC, iv_bytes).decrypt(raw), AES.block_size).decode("utf-8")
    except ModuleNotFoundError:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        decryptor = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes)).decryptor()
        padded = decryptor.update(raw) + decryptor.finalize()
        padding = padded[-1]
        if padding < 1 or padding > 16 or padded[-padding:] != bytes([padding]) * padding:
            raise ValueError("Invalid KIS WebSocket padding")
        return padded[:-padding].decode("utf-8")


@dataclass
class _Subscription:
    tr_id: str
    tr_key: str
    columns: list[str]
    encrypted: bool = False
    key: str = ""
    iv: str = ""


class KISSubscriptionLimitError(RuntimeError):
    """The provider rejected the size or rate of the subscription set."""


class KISFrameParser:
    """Decode KIS system/data frames without pandas or broker side effects."""

    def __init__(self):
        self.subscriptions: dict[tuple[str, str], _Subscription] = {}

    def register(self, tr_id: str, tr_key: str) -> None:
        columns = NOTICE_COLUMNS if tr_id == "H0STCNI9" else TRADE_COLUMNS
        self.subscriptions[(str(tr_id), str(tr_key))] = _Subscription(str(tr_id), str(tr_key), columns)

    def parse(self, raw: str | bytes) -> dict[str, Any] | None:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        if not text:
            return None
        if text[0] in {"0", "1"}:
            parts = text.split("|", 3)
            if len(parts) < 4:
                return None
            tr_id, count_text, payload = parts[1], parts[2], parts[3]
            if not count_text.isdigit() or not 1 <= int(count_text) <= 100:
                return None
            count = int(count_text)
            subscriptions = [value for (registered_id, _), value in self.subscriptions.items() if registered_id == tr_id]
            subscription = subscriptions[0] if subscriptions else None
            if subscription is None:
                return {"kind": "unknown_data", "trId": tr_id}
            if text[0] == "1":
                if not subscription.key or not subscription.iv:
                    raise RuntimeError("KIS encrypted frame arrived before its subscription key")
                payload = _decrypt_aes_cbc(payload, subscription.key, subscription.iv)
            values = payload.split("^")
            width = len(subscription.columns)
            if len(values) < count * width:
                return None
            messages = []
            for index in range(count):
                row = dict(zip(subscription.columns, values[index * width:(index + 1) * width]))
                tr_key = subscription.tr_key if tr_id == "H0STCNI9" else row["MKSC_SHRN_ISCD"]
                if (tr_id, tr_key) not in self.subscriptions:
                    continue
                messages.append({"kind": "fill_notice" if tr_id == "H0STCNI9" else "trade", "trId": tr_id, "trKey": tr_key, "row": row})
            if len(messages) == 1:
                return messages[0]
            return {"kind": "batch", "messages": messages}

        try:
            envelope = json.loads(text)
        except json.JSONDecodeError:
            return {"kind": "unknown_system", "payload": text}
        header = envelope.get("header") or {}
        body = envelope.get("body") or {}
        tr_id = str(header.get("tr_id") or "")
        tr_key = str(header.get("tr_key") or "")
        if tr_id == "PINGPONG":
            return {"kind": "pingpong", "trId": tr_id, "trKey": tr_key}
        subscription = self.subscriptions.get((tr_id, tr_key))
        output = body.get("output") or {}
        if subscription is not None:
            subscription.encrypted = str(header.get("encrypt") or "N").upper() == "Y"
            subscription.key = str(output.get("key") or "")
            subscription.iv = str(output.get("iv") or "")
        return {
            "kind": "system",
            "trId": tr_id,
            "trKey": tr_key,
            "ok": str(body.get("rt_cd") or "") == "0",
            "message": body.get("msg1"),
            "messageCode": body.get("msg_cd"),
            "encrypted": subscription.encrypted if subscription else False,
        }

    @staticmethod
    def trade_tick(message: dict[str, Any], *, timestamp: float | None = None) -> TradeTick | None:
        if message.get("kind") != "trade":
            return None
        row = message.get("row") or {}
        code = str(row.get("MKSC_SHRN_ISCD") or message.get("trKey") or "").strip()
        price = _float(row.get("STCK_PRPR"))
        if not code or price <= 0:
            return None
        event_time = timestamp
        if event_time is None:
            clock = str(row.get('STCK_CNTG_HOUR') or '')
            day = str(row.get('BSOP_DATE') or datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y%m%d'))
            try:
                event_time = datetime.strptime(day + clock, '%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo('Asia/Seoul')).timestamp()
            except ValueError:
                return None  # Unknown event age must not create a live trading signal.
        return TradeTick(
            code=code,
            timestamp=float(event_time),
            price=price,
            cumulative_volume=_float(row.get("ACML_VOL")),
            ask_price=_float(row.get("ASKP1")),
            bid_price=_float(row.get("BIDP1")),
            ask_quantity=_float(row.get("ASKP_RSQN1")),
            bid_quantity=_float(row.get("BIDP_RSQN1")),
            day_open=_float(row.get("STCK_OPRC")),
            day_high=_float(row.get("STCK_HGPR")),
            day_low=_float(row.get("STCK_LWPR")),
        )

    @staticmethod
    def fill_notice(message: dict[str, Any]) -> dict[str, Any] | None:
        if message.get("kind") != "fill_notice":
            return None
        row = message.get("row") or {}
        code = str(row.get("STCK_SHRN_ISCD") or "").strip()
        order_no = str(row.get("ODER_NO") or "").strip()
        if not code or not order_no:
            return None
        return {
            "code": code,
            "brokerOrderNo": order_no,
            "filled": str(row.get("CNTG_YN") or "") == "2",
            "accepted": str(row.get("ACPT_YN") or "") in {"1", "2", "Y"},
            "rejected": str(row.get("RFUS_YN") or "") in {"1", "Y"},
            "quantity": int(_float(row.get("CNTG_QTY"))),
            "price": _float(row.get("CNTG_UNPR")),
            "noticeTime": row.get("STCK_CNTG_HOUR"),
            "raw": row,
        }


class KISWebSocketStream:
    """Reconnectable stream with a bounded, periodically refreshed watch set."""

    def __init__(self, client: KISPaperClient, codes: list[str], *, include_fill_notice: bool = False):
        self.client = client
        self.codes = list(dict.fromkeys(str(code) for code in codes if code))
        self.include_fill_notice = include_fill_notice

    async def run(
        self,
        on_message: Callable[[dict[str, Any]], Awaitable[None]],
        *,
        refresh: Callable[[], Awaitable[list[str]] | list[str]] | None = None,
        refresh_seconds: float = 60.0,
    ) -> None:
        try:
            import websockets
        except ModuleNotFoundError as exc:
            raise RuntimeError("websockets is required for KIS realtime paper trading") from exc

        approval_key = await asyncio.to_thread(self.client.websocket_approval_key)
        parser = KISFrameParser()
        subscriptions = [("H0STCNT0", code) for code in self.codes]
        if self.include_fill_notice:
            if not self.client.config.hts_id:
                raise RuntimeError("KIS_PAPER_HTS_ID is required for fill notifications")
            subscriptions.insert(0, ("H0STCNI9", self.client.config.hts_id))
        if len(subscriptions) > 40:
            raise RuntimeError(f"KIS WebSocket subscription limit exceeded: {len(subscriptions)}")
        async with websockets.connect(
            self.client.websocket_url(),
            ping_interval=None,
            max_size=4 * 1024 * 1024,
        ) as socket:
            for tr_id, tr_key in subscriptions:
                parser.register(tr_id, tr_key)

            async def refresh_subscriptions() -> None:
                if refresh is None:
                    return
                active_codes = set(self.codes)
                while True:
                    await asyncio.sleep(max(5.0, float(refresh_seconds)))
                    result = refresh()
                    if hasattr(result, "__await__"):
                        result = await result  # type: ignore[assignment]
                    next_codes = list(dict.fromkeys(str(code) for code in (result or []) if code))
                    maximum_codes = 39 if self.include_fill_notice else 40
                    next_codes = next_codes[:maximum_codes]
                    next_set = set(next_codes)
                    for code in sorted(active_codes - next_set):
                        await socket.send(subscription_message(approval_key, "H0STCNT0", code, tr_type="2"))
                        await asyncio.sleep(0.5)
                        parser.subscriptions.pop(("H0STCNT0", code), None)
                    for code in next_codes:
                        if code in active_codes:
                            continue
                        parser.register("H0STCNT0", code)
                        await socket.send(subscription_message(approval_key, "H0STCNT0", code))
                        await asyncio.sleep(0.5)
                    active_codes = next_set
                    self.codes = next_codes

            async def receive() -> None:
                async for raw in socket:
                    message = parser.parse(raw)
                    if message is None:
                        continue
                    if message.get("kind") == "pingpong":
                        await socket.send(raw)
                        continue
                    if message.get("kind") == "system" and not message.get("ok"):
                        detail = str(message.get("message") or "subscription rejected")
                        if any(word in detail.upper() for word in ["LIMIT", "MAX", "초과", "유량"]):
                            raise KISSubscriptionLimitError(detail)
                        raise RuntimeError(f"KIS subscription rejected: {detail}")
                    for item in message.get("messages", [message]):
                        await on_message(item)
            receive_task = asyncio.create_task(receive())
            tasks = [receive_task]
            try:
                for tr_id, tr_key in subscriptions:
                    await socket.send(subscription_message(approval_key, tr_id, tr_key))
                    await asyncio.sleep(0.5)
                    if receive_task.done():
                        receive_task.result()
                        return
                if refresh is not None:
                    tasks.append(asyncio.create_task(refresh_subscriptions()))
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
            finally:
                for task in tasks:
                    task.cancel()
                for task in tasks:
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
