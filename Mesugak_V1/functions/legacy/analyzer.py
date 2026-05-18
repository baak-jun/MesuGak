import datetime
import time
from typing import Any, Callable, Dict, List, Optional, Set

import FinanceDataReader as fdr
import firebase_admin
import numpy as np
import pandas as pd
from firebase_admin import credentials, firestore


ANALYSIS_CHUNK_SIZE = 400

SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
NASDAQ100_WIKI_URL = "https://en.wikipedia.org/wiki/Nasdaq-100"


class Config:
    CRED_PATH = "./serviceAccountKey.json"

    @staticmethod
    def initialize_firebase():
        if not firebase_admin._apps:
            cred = credentials.Certificate(Config.CRED_PATH)
            firebase_admin.initialize_app(cred)
        return firestore.client()


class StockAnalyzer:
    def __init__(self, db):
        self.db = db

    def get_stock_data(self, code):
        """주가 데이터 수집 (최근 400일) - US close/adj close 충돌 대응 포함"""
        try:
            end_date = datetime.datetime.now()
            start_date = end_date - datetime.timedelta(days=400)

            df = fdr.DataReader(code, start_date, end_date)

            if df is None:
                print(f"[DATA_DEBUG] {code}: DataReader returned None")
                return None

            if df.empty:
                print(f"[DATA_DEBUG] {code}: empty dataframe")
                return None

            df = df.reset_index()
            df.columns = [str(c).lower() for c in df.columns]

            rename_map = {"index": "date", "adj close": "adj_close"}
            df.rename(columns=rename_map, inplace=True)

            if "date" not in df.columns:
                print(f"[DATA_DEBUG] {code}: missing date column -> cols={list(df.columns)}")
                return None

            if "close" not in df.columns and "adj_close" in df.columns:
                df["close"] = df["adj_close"]

            required_price_cols = ["open", "high", "low", "close"]
            missing_required = [c for c in required_price_cols if c not in df.columns]
            if missing_required:
                print(
                    f"[DATA_DEBUG] {code}: missing required columns -> "
                    f"{missing_required}, cols={list(df.columns)}"
                )
                return None

            numeric_cols = ["open", "high", "low", "close"]
            if "volume" in df.columns:
                numeric_cols.append("volume")

            for c in numeric_cols:
                df[c] = pd.to_numeric(df[c], errors="coerce")

            subset_cols = ["date", "open", "high", "low", "close"]
            if "volume" in df.columns:
                subset_cols.append("volume")

            before_dropna = len(df)
            df = df.dropna(subset=subset_cols)

            if df.empty:
                print(f"[DATA_DEBUG] {code}: empty after dropna (before={before_dropna})")
                return None

            if len(df) < 120:
                print(f"[DATA_DEBUG] {code}: too short ({len(df)} rows)")
                return None

            return df
        except Exception as e:
            print(f"[DATA_DEBUG] {code}: fetch failed -> {type(e).__name__}: {e}")
            return None

    def calculate_indicators(self, df):
        if df is None:
            return None

        df["MA20"] = df["close"].rolling(window=20).mean()
        df["StdDev"] = df["close"].rolling(window=20).std()
        df["Upper"] = df["MA20"] + (df["StdDev"] * 2)
        df["Lower"] = df["MA20"] - (df["StdDev"] * 2)

        df["MA20"] = df["MA20"].replace(0, np.nan)
        df["Bandwidth"] = (df["Upper"] - df["Lower"]) / df["MA20"]
        df["MinBW125"] = df["Bandwidth"].rolling(window=125, min_periods=20).min()

        df = df.fillna(0)
        df = df.replace([np.inf, -np.inf], 0)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        status, pattern = "일반 흐름", "normal"

        if last.get("volume", 0) == 0:
            status, pattern = "거래정지", "suspended"
        else:
            if last["MinBW125"] > 0 and last["Bandwidth"] <= (last["MinBW125"] * 1.15):
                status, pattern = "에너지 응축", "squeeze"

            recent_squeeze = (
                df["Bandwidth"].iloc[-5:-1] <= (df["MinBW125"].iloc[-5:-1] * 1.15)
            ).any()
            is_expanding = last["Bandwidth"] > prev["Bandwidth"]
            is_breakout = last["close"] > last["Upper"]

            if recent_squeeze and is_expanding and is_breakout:
                status, pattern = "매수 신호", "buy_signal"

        recent_df = df.tail(90).copy()
        history_list = []

        for _, row in recent_df.iterrows():
            d_str = row["date"].strftime("%Y-%m-%d")

            band_diff = row["Upper"] - row["Lower"]
            pct_b = (row["close"] - row["Lower"]) / band_diff if band_diff > 0 else 0.0

            history_item = {
                "date": d_str,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
                "upper": float(round(row["Upper"], 2)),
                "lower": float(round(row["Lower"], 2)),
                "ma20": float(round(row["MA20"], 2)),
                "bandwidth": float(round(row["Bandwidth"], 4)),
                "percentB": float(round(pct_b, 4)),
            }
            history_list.append(history_item)

        band_diff_last = last["Upper"] - last["Lower"]
        last_pct_b = (last["close"] - last["Lower"]) / band_diff_last if band_diff_last > 0 else 0.0

        return {
            "status": str(status),
            "type": str(pattern),
            "currentPrice": float(last["close"]),
            "volume": float(last.get("volume", 0)),
            "bandwidth": float(round(last["Bandwidth"], 4)),
            "percentB": float(round(last_pct_b, 4)),
            "lastDate": history_list[-1]["date"] if history_list else "",
            "history": history_list,
        }

    def _normalize_listing_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        if "Code" not in df.columns:
            for candidate in ["Symbol", "symbol", "Ticker", "ticker"]:
                if candidate in df.columns:
                    df["Code"] = df[candidate]
                    break

        if "Name" not in df.columns:
            for candidate in ["Name", "name", "Company", "company", "Security"]:
                if candidate in df.columns:
                    df["Name"] = df[candidate]
                    break

        if "Marcap" not in df.columns:
            for candidate in ["Marcap", "Market Cap", "MarketCap", "marketCap", "MarCap"]:
                if candidate in df.columns:
                    df["Marcap"] = pd.to_numeric(df[candidate], errors="coerce").fillna(0)
                    break
            else:
                df["Marcap"] = 0

        if "Code" not in df.columns or "Name" not in df.columns:
            return pd.DataFrame(columns=["Code", "Name", "Marcap"])

        df["Code"] = df["Code"].astype(str).str.strip()
        df["Name"] = df["Name"].fillna(df["Code"]).astype(str)
        df["Marcap"] = pd.to_numeric(df["Marcap"], errors="coerce").fillna(0)

        df = df[df["Code"] != ""]
        df = df.drop_duplicates(subset=["Code"], keep="first")
        return df[["Code", "Name", "Marcap"]]

    def _normalize_us_symbol_for_fdr(self, symbol: str) -> str:
        symbol = str(symbol).strip().upper()
        return symbol.replace(".", "-")

    def _load_sp500_symbols(self) -> Set[str]:
        tables = pd.read_html(SP500_WIKI_URL)
        if not tables:
            raise RuntimeError("S&P 500 constituent table not found")
        df = tables[0].copy()
        if "Symbol" not in df.columns:
            raise RuntimeError(f"S&P 500 table missing Symbol column: {list(df.columns)}")
        symbols = {
            self._normalize_us_symbol_for_fdr(x)
            for x in df["Symbol"].astype(str).tolist()
            if str(x).strip()
        }
        return symbols

    def _load_nasdaq100_symbols(self) -> Set[str]:
        tables = pd.read_html(NASDAQ100_WIKI_URL)
        for df in tables:
            cols = [str(c).strip() for c in df.columns]
            if "Ticker" in cols:
                symbols = {
                    self._normalize_us_symbol_for_fdr(x)
                    for x in df["Ticker"].astype(str).tolist()
                    if str(x).strip()
                }
                return symbols
        raise RuntimeError("Nasdaq-100 constituent table not found")

    def _load_major_us_universe(self) -> pd.DataFrame:
        sp500 = self._load_sp500_symbols()
        ndx100 = self._load_nasdaq100_symbols()
        wanted = sp500 | ndx100

        print(f"  ✅ [US] S&P 500 symbols: {len(sp500)}")
        print(f"  ✅ [US] Nasdaq-100 symbols: {len(ndx100)}")
        print(f"  ✅ [US] Combined unique symbols: {len(wanted)}")

        us_frames = []
        for exchange in ["NASDAQ", "NYSE", "AMEX"]:
            try:
                ex_df = fdr.StockListing(exchange)
                ex_df = self._normalize_listing_columns(ex_df)
                if ex_df.empty:
                    print(f"  ⚠️ [{exchange}] 상장 종목을 가져오지 못했습니다.")
                    continue
                ex_df["Code"] = ex_df["Code"].astype(str).map(self._normalize_us_symbol_for_fdr)
                ex_df = ex_df[ex_df["Code"].isin(wanted)]
                if ex_df.empty:
                    continue
                us_frames.append(ex_df)
                print(f"  ✅ [{exchange}] universe match {len(ex_df)}개")
            except Exception as ex:
                print(f"  ⚠️ [{exchange}] 종목 가져오기 실패: {ex}")

        if not us_frames:
            return pd.DataFrame(columns=["Code", "Name", "Marcap"])

        df = pd.concat(us_frames, ignore_index=True)
        df = df.drop_duplicates(subset=["Code"], keep="first")
        df["Marcap"] = 0  # 현재 FDR US listing에는 시총 컬럼이 없어서 의미상 유지
        df = df.sort_values(["Code"], ascending=[True])
        return df[["Code", "Name", "Marcap"]]

    def get_target_stocks(self, market="KR", kr_markets=None):
        market = str(market).upper().strip()
        print(f"📥 [{market}] 전 종목 리스트 다운로드 중...")
        try:
            if market == "KR":
                df = fdr.StockListing("KRX")

                if kr_markets:
                    wanted = {str(m).strip().upper() for m in kr_markets if str(m).strip()}
                    if wanted and "Market" in df.columns:
                        df["Market"] = df["Market"].astype(str).str.upper()
                        df = df[df["Market"].isin(wanted)]
                        print(f"  📌 [KR] 시장 필터 적용: {sorted(wanted)} -> {len(df)}개 종목")
                    elif wanted:
                        print("  ⚠️ [KR] Market 컬럼이 없어 시장 필터를 적용하지 못했습니다.")

                df = self._normalize_listing_columns(df)
                df = df.sort_values(["Marcap", "Code"], ascending=[False, True])
                return df.to_dict("records")

            if market == "US":
                df = self._load_major_us_universe()
                print(f"  ✅ [US] major universe total {len(df)}개")
                return df.to_dict("records")

            print(f"❌ 지원하지 않는 market 입니다: {market}")
            return []
        except Exception as e:
            print(f"❌ 종목 가져오기 실패: {e}")
            return []

    def sync_meta_data_snapshot(self, market: str, summary_all: List[Dict[str, Any]], previous_doc_count: int = 0) -> int:
        new_doc_count = 0

        for start in range(0, len(summary_all), ANALYSIS_CHUNK_SIZE):
            chunk = summary_all[start : start + ANALYSIS_CHUNK_SIZE]
            doc_name = f"meta_{market}_{new_doc_count}"
            print(f"  📝 목록(meta_data) 스냅샷 저장: {doc_name} ({len(chunk)}개)")
            self.db.collection("meta_data").document(doc_name).set(
                {
                    "list": chunk,
                    "market": market,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
            )
            new_doc_count += 1

        for idx in range(new_doc_count, int(previous_doc_count or 0)):
            doc_name = f"meta_{market}_{idx}"
            print(f"  🧹 이전 목록(meta_data) 정리: {doc_name}")
            self.db.collection("meta_data").document(doc_name).delete()

        return new_doc_count

    def run_market_analysis(
        self,
        market="KR",
        kr_markets=None,
        resume_state: Optional[Dict[str, Any]] = None,
        checkpoint_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        market = str(market).upper().strip()
        resume_state = resume_state or {}

        targets = self.get_target_stocks(market, kr_markets=kr_markets)
        total_count = len(targets)

        done_codes = {str(code) for code in (resume_state.get("done_codes", []) or [])}
        processed_codes = {
            str(code) for code in (resume_state.get("processed_codes", []) or [])
        }
        failed_codes = {
            str(code) for code in (resume_state.get("failed_codes", []) or [])
        }
        summary_all: List[Dict[str, Any]] = list(resume_state.get("summary_all", []) or [])
        meta_doc_count = int(resume_state.get("meta_doc_count", 0) or 0)

        print(f"🔥 [{market}] 총 {total_count}개 종목 분석 시작!\n")
        if done_codes:
            print(
                f"↪️ resume mode: done={len(done_codes)} "
                f"(processed={len(processed_codes)}, failed={len(failed_codes)})"
            )

        batch = self.db.batch()
        batch_count = 0
        failed_count = len(failed_codes)

        committed_codes_buffer: List[str] = []
        committed_summary_buffer: List[Dict[str, Any]] = []

        def flush_success_buffers():
            nonlocal batch, batch_count, summary_all, meta_doc_count
            nonlocal committed_codes_buffer, committed_summary_buffer

            if batch_count <= 0:
                return

            batch.commit()

            committed_codes = list(committed_codes_buffer)
            committed_summaries = list(committed_summary_buffer)

            if checkpoint_callback:
                checkpoint_callback(
                    {
                        "done_codes_to_add": committed_codes,
                        "processed_codes_to_add": committed_codes,
                        "summary_items_to_add": committed_summaries,
                        "status": "running",
                    }
                )

            summary_all.extend(committed_summaries)
            meta_doc_count = self.sync_meta_data_snapshot(
                market,
                summary_all,
                previous_doc_count=meta_doc_count,
            )

            if checkpoint_callback:
                checkpoint_callback(
                    {
                        "meta_doc_count": meta_doc_count,
                        "status": "running",
                    }
                )

            print(f"  💾 상세 데이터 중간 저장 완료 ({len(summary_all)}/{total_count})")
            batch = self.db.batch()
            batch_count = 0
            committed_codes_buffer = []
            committed_summary_buffer = []

        for idx, stock in enumerate(targets):
            code = str(stock["Code"])
            name = stock["Name"]
            marcap = float(stock.get("Marcap", 0) or 0)

            if code in done_codes:
                continue

            df = self.get_stock_data(code)
            res = self.calculate_indicators(df)

            if res:
                res["id"] = f"{market}_{code}"
                res["name"] = name
                res["market"] = market
                res["marcap"] = marcap
                res["updatedAt"] = firestore.SERVER_TIMESTAMP

                doc_ref = self.db.collection("stock_analysis").document(res["id"])
                batch.set(doc_ref, res)

                summary_item = {
                    "id": res["id"],
                    "name": name,
                    "type": res["type"],
                    "status": res["status"],
                    "currentPrice": res["currentPrice"],
                    "bandwidth": res["bandwidth"],
                    "percentB": res["percentB"],
                    "marcap": marcap,
                    "volume": res["volume"],
                    "market": market,
                }

                batch_count += 1
                committed_codes_buffer.append(code)
                committed_summary_buffer.append(summary_item)

                if res["type"] == "buy_signal":
                    print(f"  ✨ [매수신호] {name} ({code})")

                if batch_count >= ANALYSIS_CHUNK_SIZE:
                    flush_success_buffers()
            else:
                failed_count += 1
                done_codes.add(code)
                failed_codes.add(code)
                if checkpoint_callback:
                    checkpoint_callback(
                        {
                            "done_codes_to_add": [code],
                            "failed_codes_to_add": [code],
                            "status": "running",
                        }
                    )

            if (idx + 1) % 100 == 0:
                print(f"  ... {idx + 1}개 완료")

            time.sleep(0.01)

        if batch_count > 0:
            flush_success_buffers()
            print("  💾 상세 데이터 최종 저장 완료.")

        if checkpoint_callback:
            checkpoint_callback({"status": "running"})

        print(
            f"\n✅ [{market}] 분석 종료. "
            f"(성공 {len(summary_all)}개 / 실패 또는 스킵 {failed_count}개)"
        )
