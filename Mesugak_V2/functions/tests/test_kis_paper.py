from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.kis_paper import KISPaperClient, KISPaperConfig  # noqa: E402


class BalanceClient(KISPaperClient):
    def __init__(self, response: dict):
        super().__init__(KISPaperConfig("key", "secret", "12345678", "01"))
        self.response = response

    def access_token(self) -> str:
        return "token"

    def _json(self, *_args, **_kwargs) -> dict:
        return self.response



class OrderClient(KISPaperClient):
    def __init__(self):
        super().__init__(KISPaperConfig("key", "secret", "12345678", "01"))
        self.calls: list[dict] = []

    def access_token(self) -> str:
        return "token"

    def _json(self, _path, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {"rt_cd": "0", "output": {"ODNO": "0000000001"}}
class KISPaperBalanceTests(unittest.TestCase):
    def test_rejects_non_paper_endpoint(self) -> None:
        with self.assertRaisesRegex(ValueError, "virtual-investment endpoint"):
            KISPaperConfig("key", "secret", "12345678", "01", "https://openapi.koreainvestment.com:9443")

    @patch.dict(
        "os.environ",
        {
            "KIS_PAPER_APP_KEY": "key",
            "KIS_PAPER_APP_SECRET": "secret",
            "KIS_PAPER_CANO": "12345678",
            "KIS_PAPER_ACNT_PRDT_CD": "01",
            "KIS_PAPER_BASE_URL": "https://openapi.koreainvestment.com:9443",
        },
        clear=False,
    )
    def test_environment_cannot_switch_to_real_endpoint(self) -> None:
        with self.assertRaisesRegex(ValueError, "virtual-investment endpoint"):
            KISPaperConfig.from_env()

    def test_balance_uses_one_equity_basis_for_cash_and_total_pnl(self) -> None:
        client = BalanceClient(
            {
                "rt_cd": "0",
                "output1": [{
                    "pdno": "005930", "prdt_name": "Samsung", "hldg_qty": "10",
                    "pchs_avg_pric": "100", "prpr": "120", "evlu_amt": "1200",
                    "pchs_amt": "1000", "evlu_pfls_amt": "200", "evlu_pfls_rt": "20",
                }],
                "output2": [{
                    "dnca_tot_amt": "9000", "scts_evlu_amt": "1200",
                    "pchs_amt_smtl_amt": "1000", "tot_evlu_amt": "5000",
                    "evlu_pfls_smtl_amt": "200",
                }],
            }
        )

        account, _ = client.fetch_balance(initial_cash=6000)

        self.assertEqual(account["cash"], 3800)
        self.assertEqual(account["totalEvalAmt"], 1200)
        self.assertEqual(account["totalEquity"], 5000)
        self.assertEqual(account["totalPnl"], -1000)
        self.assertEqual(account["unrealizedPnl"], 200)
        self.assertEqual(account["realizedPnl"], -1200)
        self.assertAlmostEqual(account["returnPct"], -16.6667, places=4)


    def test_submit_market_order_uses_market_order_code_and_zero_price(self) -> None:
        client = OrderClient()
        response = client.submit_market_order("BUY", "005930", 3)
        self.assertEqual(response["output"]["ODNO"], "0000000001")
        self.assertEqual(client.calls[0]["payload"]["ORD_DVSN"], "01")
        self.assertEqual(client.calls[0]["payload"]["ORD_UNPR"], "0")
if __name__ == "__main__":
    unittest.main()
