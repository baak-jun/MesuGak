from __future__ import annotations

import sys
import unittest
import io
import tempfile
import json
import os
from urllib.error import HTTPError, URLError
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_engine.kis_paper import KISPaperClient, KISPaperConfig, KISOrderRejectedError  # noqa: E402


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
    def test_balance_and_discovery_get_priority_over_bulk_history(self):
        for path in ['/inquire-balance','/inquire-daily-ccld','/oauth2/Approval','/volume-rank']:
            now=[1000.0]
            with self.subTest(path=path), tempfile.TemporaryDirectory() as root, patch.dict(os.environ,{'KIS_PAPER_RATE_STATE':str(Path(root)/'rate.sqlite3'),'KIS_PAPER_REQUEST_INTERVAL_SECONDS':'2'}), \
                 patch('strategy_engine.kis_paper.time',side_effect=lambda:now[0]), patch('strategy_engine.kis_paper.clock.sleep',side_effect=lambda seconds:now.__setitem__(0,now[0]+seconds)):
                client=KISPaperClient(KISPaperConfig('dummy','secret','12345678','01'))
                client._shared_request_slot(path)
                self.assertEqual(now[0],1000)
                client._shared_request_slot('/inquire-daily-itemchartprice')
                self.assertGreaterEqual(now[0],1003)

    def test_contest_clients_share_api_spacing_and_orders_delay_bulk_candles(self):
        now=[1000.0]
        def sleep(seconds):
            now[0]+=seconds
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ,{'KIS_PAPER_RATE_STATE':str(Path(root)/'rate.sqlite3')}), \
             patch('strategy_engine.kis_paper.time',side_effect=lambda:now[0]), patch('strategy_engine.kis_paper.clock.sleep',side_effect=sleep):
            first=KISPaperClient(KISPaperConfig('shared-key','secret','12345678','01'))
            second=KISPaperClient(first.config)
            first._shared_request_slot('/inquire-daily-itemchartprice')
            self.assertEqual(now[0],1000)
            second._shared_request_slot('/order-cash')
            self.assertGreaterEqual(now[0],1002)
            first._shared_request_slot('/inquire-daily-itemchartprice')
            self.assertGreaterEqual(now[0],1005)

    @patch('strategy_engine.kis_paper.clock.sleep')
    @patch('strategy_engine.kis_paper.urlopen')
    def test_explicit_rate_rejection_retries_with_slower_spacing(self, opener, sleep):
        for code in ['EGW00201', 'EGW00215']:
            with self.subTest(code=code):
                rejection = HTTPError('https://example.invalid', 500, 'limited', {}, io.BytesIO(json.dumps({'msg_cd': code}).encode()))
                response = unittest.mock.MagicMock()
                response.__enter__.return_value.read.return_value = json.dumps({'rt_cd': '0'}).encode()
                opener.reset_mock()
                opener.side_effect = [rejection, response]
                client = KISPaperClient(KISPaperConfig('key', 'secret', '12345678', '01'))
                client.request_interval = 1.0
                self.assertEqual(client._json('/order', method='POST', payload={})['rt_cd'], '0')
                self.assertEqual(opener.call_count, 2)
                self.assertEqual(client.request_interval, 2.0)

    def test_different_site_and_contest_keys_never_share_default_token_cache(self):
        site = KISPaperClient(KISPaperConfig('site-key', 'secret', '12345678', '01'))
        contest = KISPaperClient(KISPaperConfig('contest-key', 'secret', '12345678', '01'))
        self.assertNotEqual(site._token_cache_path(), contest._token_cache_path())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'token.json'
            site = KISPaperClient(KISPaperConfig('site-key', 'secret', '12345678', '01', token_cache_path=str(path)))
            contest = KISPaperClient(KISPaperConfig('contest-key', 'secret', '12345678', '01', token_cache_path=str(path)))
            site._write_cached_token('example-token', {'expires_in': 3600})
            self.assertEqual(site._read_cached_token(), 'example-token')
            self.assertEqual(contest._read_cached_token(), '')

    @patch('strategy_engine.kis_paper.clock.sleep')
    @patch('strategy_engine.kis_paper.urlopen', side_effect=URLError('timed out'))
    def test_ambiguous_order_network_failure_is_never_retried(self, opener, sleep):
        client = KISPaperClient(KISPaperConfig('key', 'secret', '12345678', '01'))
        with self.assertRaisesRegex(RuntimeError, 'network error'):
            client._json('/order', method='POST', payload={})
        self.assertEqual(opener.call_count, 1)
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

    @patch.object(KISPaperClient, "_json_with_token_retry", return_value={"rt_cd": "0", "output": [{"code": "A"}]})
    def test_fluctuation_uses_one_character_rank_sort_code(self, request) -> None:
        client = KISPaperClient(KISPaperConfig("key", "secret", "12345678", "01"))

        rows = client.fluctuation(count=30)

        self.assertEqual(rows, [{"code": "A"}])
        self.assertEqual(request.call_args.kwargs["params"]["fid_rank_sort_cls_code"], "0")

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
        for side in ['BUY', 'SELL']:
            response = client.submit_market_order(side, "005930", 3)
            self.assertEqual(response["output"]["ODNO"], "0000000001")
            self.assertEqual(client.calls[-1]["payload"]["ORD_DVSN"], "01")
            self.assertEqual(client.calls[-1]["payload"]["ORD_UNPR"], "0")

    def test_explicit_broker_rejection_is_distinct_from_unknown_transport_failure(self):
        client = OrderClient()
        with patch.object(client, '_json_with_token_retry', return_value={'rt_cd': '1', 'msg1': '주문 가능 금액 초과'}):
            with self.assertRaises(KISOrderRejectedError):
                client.submit_market_order('BUY', '005930', 3)
if __name__ == "__main__":
    unittest.main()
