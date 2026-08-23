import os
import time
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Dict

logger = logging.getLogger(__name__)

class KisApiClient:
    def __init__(self, app_key: str = None, app_secret: str = None, is_mock: bool = False):
        self.app_key = app_key or os.environ.get("KIS_APP_KEY") or os.environ.get("KIS_REAL_APP_KEY") or os.environ.get("REAL_APP_KEY")
        self.app_secret = app_secret or os.environ.get("KIS_APP_SECRET") or os.environ.get("KIS_REAL_APP_SECRET") or os.environ.get("REAL_APP_SECRET")
        self.is_mock = is_mock
        self.base_url = "https://openapivts.koreainvestment.com:29443" if is_mock else "https://openapi.koreainvestment.com:9443"
        self._access_token = None
        self._token_expires_at = 0

        if not self.app_key or not self.app_secret:
            logger.warning("KIS_APP_KEY or KIS_APP_SECRET is not set. API calls will fail.")

    def _get_token(self) -> str:
        if time.time() < self._token_expires_at and self._access_token:
            return self._access_token

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        res = requests.post(url, headers=headers, json=body)
        res.raise_for_status()
        data = res.json()
        self._access_token = data.get("access_token")
        self._token_expires_at = time.time() + int(data.get("expires_in", 86400)) - 60
        return self._access_token

    def _call_api(self, tr_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Rate limit: 20 per second. Sleep 0.06s to be safe.
        time.sleep(0.06)
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        if tr_id == "FHKST01010100":
            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._get_token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        return res.json()

    def get_ohlcv(self, code: str, start: str, end: str) -> pd.DataFrame:
        """
        Get OHLCV using FHKST03010100. Handles multiple calls if range > 100 days.
        """
        start_dt = datetime.strptime(start, "%Y%m%d")
        end_dt = datetime.strptime(end, "%Y%m%d")
        
        all_items = []
        current_end = end_dt
        
        while current_end >= start_dt:
            # Fetch 100 business days (roughly 140 calendar days)
            current_start = current_end - timedelta(days=140)
            if current_start < start_dt:
                current_start = start_dt
                
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": current_start.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": current_end.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0"
            }
            data = self._call_api("FHKST03010100", params)
            items = data.get("output2", [])
            if not items:
                break
                
            # Filter out empty rows
            valid_items = [item for item in items if item and str(item.get("stck_bsop_date")).strip()]
            all_items.extend(valid_items)
            
            if len(valid_items) < 1:
                break
                
            # Next end date is one day before the earliest date in current batch
            earliest_date_str = valid_items[-1].get("stck_bsop_date")
            if not earliest_date_str:
                break
            earliest_date = datetime.strptime(earliest_date_str, "%Y%m%d")
            current_end = earliest_date - timedelta(days=1)
            
        if not all_items:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_items)
        df = df.drop_duplicates(subset=["stck_bsop_date"])
        df["Date"] = pd.to_datetime(df["stck_bsop_date"])
        df["Open"] = pd.to_numeric(df["stck_oprc"])
        df["High"] = pd.to_numeric(df["stck_hgpr"])
        df["Low"] = pd.to_numeric(df["stck_lwpr"])
        df["Close"] = pd.to_numeric(df["stck_clpr"])
        df["Volume"] = pd.to_numeric(df["acml_vol"])
        
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
        df = df.sort_values("Date").reset_index(drop=True)
        
        # Filter exactly within the requested range
        df = df[(df["Date"] >= start_dt) & (df["Date"] <= end_dt)]
        return df

    def get_fundamentals(self, code: str) -> Dict[str, Any]:
        """
        Get fundamentals using FHKST01010100 (inquire-price)
        KIS API might not provide ROE, DebtRatio, or OpProfit through basic price check.
        We extract PER, PBR, EPS, BPS if available.
        """
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code
        }
        data = self._call_api("FHKST01010100", params)
        out = data.get("output", {})
        
        def _num(val): 
            try:
                return float(val) if val else None
            except (ValueError, TypeError):
                return None

        return {
            "source": "KIS_OPEN_API",
            "asOf": datetime.now().strftime("%Y-%m-%d"),
            "per": _num(out.get("per")),
            "pbr": _num(out.get("pbr")),
            "eps": _num(out.get("eps")),
            "bps": _num(out.get("bps")),
            # ROE, DebtRatio, OperatingProfit not exposed in basic KIS endpoint.
            "roe": None,
            "debtRatio": None,
            "operatingProfit": None,
            "operatingProfitGrowth": None,
        }

def get_kis_client() -> KisApiClient:
    return KisApiClient()
