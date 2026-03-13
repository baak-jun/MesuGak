import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


def _env_first(*keys: str) -> Optional[str]:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


class KoreaStockTrader:
    def __init__(self, mode: str = "mock"):
        self.real_conf = {
            "appkey": _env_first("REAL_APP_KEY", "KIS_REAL_APP_KEY"),
            "appsecret": _env_first("REAL_APP_SECRET", "KIS_REAL_APP_SECRET"),
            "acc_no": _env_first("REAL_ACC_NO", "KIS_REAL_ACC_NO"),
        }
        self.mock_conf = {
            "appkey": _env_first("MOCK_APP_KEY", "KIS_MOCK_APP_KEY", "VITE_KIS_APP_KEY"),
            "appsecret": _env_first("MOCK_APP_SECRET", "KIS_MOCK_APP_SECRET", "VITE_KIS_APP_SECRET"),
            "acc_no": _env_first("MOCK_ACC_NO", "KIS_MOCK_ACC_NO"),
        }
        self.url_real = "https://openapi.koreainvestment.com:9443"
        self.url_mock = "https://openapivts.koreainvestment.com:29443"

        self.access_token = None
        self.mode = ""
        self.appkey = None
        self.appsecret = None
        self.acc_no = None
        self.acc_code = None
        self.acc_prod = None

        self.set_mode(mode)

    def set_mode(self, mode: str):
        mode = (mode or "mock").lower()
        if mode == "real":
            self.conf = self.real_conf
            self.base_url = self.url_real
            self.tr_id_buy = "TTTC0802U"
            self.tr_id_sell = "TTTC0801U"
            self.tr_id_balance = "TTTC8434R"
        else:
            self.conf = self.mock_conf
            self.base_url = self.url_mock
            self.tr_id_buy = "VTTC0802U"
            self.tr_id_sell = "VTTC0801U"
            self.tr_id_balance = "VTTC8434R"
            mode = "mock"

        self.mode = mode
        self.appkey = self.conf["appkey"]
        self.appsecret = self.conf["appsecret"]
        self.acc_no = self.conf["acc_no"]
        self._validate_config()
        self._parse_account()
        print(f"[KIS] mode={self.mode}")

    def _validate_config(self):
        missing = []
        if not self.appkey:
            missing.append("APP_KEY")
        if not self.appsecret:
            missing.append("APP_SECRET")
        if not self.acc_no:
            missing.append("ACC_NO")
        if missing:
            prefix = "REAL" if self.mode == "real" else "MOCK"
            raise ValueError(f"Missing {prefix} settings: {', '.join(missing)}")

    def _parse_account(self):
        if "-" not in self.acc_no:
            raise ValueError("Invalid ACC_NO format. Expected: 12345678-01")
        self.acc_code, self.acc_prod = self.acc_no.split("-", 1)

    def get_current_mode(self):
        return self.mode

    def auth(self):
        url = f"{self.base_url}/oauth2/tokenP"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
        }
        res = requests.post(url, json=body, timeout=10)
        res.raise_for_status()
        data = res.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"Token missing in response: {data}")
        self.access_token = token
        print(f"[KIS] token issued ({self.mode})")

    def get_header(self, tr_id: str):
        if self.access_token is None:
            self.auth()
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
            "tr_id": tr_id,
        }

    def get_current_price(self, code: str):
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self.get_header("FHKST01010100")
        params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": code}
        try:
            res = requests.get(f"{self.base_url}{path}", headers=headers, params=params, timeout=10)
            if res.status_code != 200:
                print(f"[KIS][PRICE][{code}] http={res.status_code} body={res.text}")
                return None
            data = res.json()
            price = data.get("output", {}).get("stck_prpr")
            return int(price) if price else None
        except Exception as exc:
            print(f"[KIS][PRICE][{code}] error: {exc}")
            return None

    def _order(self, code: str, qty: int, tr_id: str, side: str):
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        headers = self.get_header(tr_id)
        body = {
            "CANO": self.acc_code,
            "ACNT_PRDT_CD": self.acc_prod,
            "PDNO": code,
            "ORD_DVSN": "01",
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0",
        }
        try:
            res = requests.post(f"{self.base_url}{path}", headers=headers, json=body, timeout=10)
            if res.status_code != 200:
                print(f"[KIS][{side}] http={res.status_code} body={res.text}")
                return False
            data = res.json()
            if data.get("rt_cd") == "0":
                order_no = data.get("output", {}).get("ODNO", "N/A")
                print(f"[KIS][{side}] success code={code} qty={qty} order_no={order_no}")
                return True
            print(f"[KIS][{side}] failed: {data.get('msg1')} ({data})")
            return False
        except Exception as exc:
            print(f"[KIS][{side}] error: {exc}")
            return False

    def buy_market_order(self, code: str, qty: int):
        return self._order(code, qty, self.tr_id_buy, "BUY")

    def sell_market_order(self, code: str, qty: int):
        return self._order(code, qty, self.tr_id_sell, "SELL")

    def get_balance(self):
        path = "/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = self.get_header(self.tr_id_balance)
        params = {
            "CANO": self.acc_code,
            "ACNT_PRDT_CD": self.acc_prod,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        try:
            res = requests.get(f"{self.base_url}{path}", headers=headers, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            output = []
            for item in data.get("output1", []):
                qty = int(item.get("hldg_qty", 0))
                if qty <= 0:
                    continue
                output.append(
                    {
                        "pdno": item.get("pdno"),
                        "prdt_name": item.get("prdt_name"),
                        "hldg_qty": qty,
                        "pchs_amt": float(item.get("pchs_amt", 0)),
                        "evlu_amt": float(item.get("evlu_amt", 0)),
                        "fltt_rt": float(item.get("evlu_pfls_rt", 0)),
                    }
                )
            return output
        except Exception as exc:
            print(f"[KIS][BALANCE] error: {exc}")
            return []
