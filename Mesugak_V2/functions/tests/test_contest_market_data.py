import json,gzip,sys,tempfile,unittest
from pathlib import Path
from datetime import date,timedelta
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from strategy_engine.contest_market_data import SOURCE,load_kis_candles,load_cached_score_history,load_cached_score_histories
from strategy_engine.realtime_scoring import valid_history, InsufficientHistoryError

class ContestMarketDataTests(unittest.TestCase):
    def test_short_history_is_preserved_and_same_day_retry_needs_no_api(self):
        today=date(2026,10,22)
        rows=[{'date':(today-timedelta(days=i)).isoformat(),'open':100,'high':102,'low':98,'close':101,'volume':1000} for i in range(1,21)]
        client=Mock();client.daily_candles.side_effect=[rows,[]]
        with tempfile.TemporaryDirectory() as directory:
            for _ in range(2):
                with self.assertRaises(InsufficientHistoryError) as caught:
                    load_kis_candles(client,Path(directory),'A',today)
                self.assertEqual(caught.exception.available,20)
            self.assertEqual(client.daily_candles.call_count,2)
            self.assertTrue((Path(directory)/'KR_A.json.gz').exists())

    def test_completed_yesterday_cache_is_usable_offline_but_stale_or_public_cache_is_not(self):
        today=date(2026,10,16)
        rows=[{'date':(today-timedelta(days=i)).isoformat(),'open':100,'high':102,'low':98,'close':101,'volume':1000} for i in range(1,181)]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'KR_A.json.gz'
            def write(source=SOURCE, checked='2026-10-15', history=rows):
                path.write_bytes(gzip.compress(json.dumps({'source':source,'cachedFor':checked,'history':history}).encode()))
            write()
            self.assertEqual(load_cached_score_history(Path(directory),'A',today).iloc[-1]['date'].date(),today-timedelta(days=1))
            write(history=rows[1:])
            with self.assertRaisesRegex(ValueError,'daily refresh'):
                load_cached_score_history(Path(directory),'A',today)
            write(source='PUBLIC')
            ready,missing=load_cached_score_histories(Path(directory),['A','MISSING'],today)
            self.assertFalse(ready)
            self.assertEqual(set(missing),{'A','MISSING'})

    def test_kis_pages_fill_yesterday_gap_and_live_history_excludes_today(self):
        today=date(2026,10,15)
        rows=[{'date':(today-timedelta(days=i)).isoformat(),'open':100,'high':102,'low':98,'close':101,'volume':1000} for i in range(200)]
        client=Mock()
        client.daily_candles.side_effect=[rows[:100],rows[100:]]
        with tempfile.TemporaryDirectory() as root:
            frame=load_kis_candles(client,Path(root),'005930',today)
            self.assertEqual(len(frame),180)
            history=valid_history(frame.to_dict('records'),today)
            self.assertEqual(history.iloc[-1]['date'].date(),today-timedelta(days=1))
            self.assertEqual(frame.iloc[-1]['date'].date(),today)
            again=load_kis_candles(client,Path(root),'005930',today)
            self.assertEqual(len(again),180)
            self.assertEqual(client.daily_candles.call_count,2)
            cached=json.loads(gzip.decompress((Path(root)/'KR_005930.json.gz').read_bytes()))
            self.assertEqual(cached['source'],SOURCE)

    def test_old_public_cache_is_never_accepted_as_kis_history(self):
        today=date(2026,10,15)
        client=Mock()
        client.daily_candles.return_value=[]
        with tempfile.TemporaryDirectory() as root:
            (Path(root)/'KR_005930.json.gz').write_bytes(gzip.compress(json.dumps({'cachedFor':today.isoformat(),'history':[{'date':'2026-10-13'}]}).encode()))
            with self.assertRaises(ValueError):
                load_kis_candles(client,Path(root),'005930',today)
            client.daily_candles.assert_called_once()
