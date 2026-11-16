import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pandas as pd
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1]/'jobs')]
from jobs import contest_market_scan as scan


class ScanResumeTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(scan,'PublicDataClient',return_value=object())
        p.start();self.addCleanup(p.stop)

    def test_universe_outage_uses_identities_but_keeps_original_date(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'runtime/checkpoints/contest_candidates_KR.json'
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'runDate':'2026-10-28','summaries':[{'code':'005930','name':'A','confidenceScore':99}]}))
            with patch.object(scan,'load_market_universe',side_effect=TimeoutError):
                rows,status=scan.contest_universe(root,datetime(2026,10,29).date())
                self.assertEqual(rows[0].code,'005930')
                self.assertFalse(hasattr(rows[0],'confidenceScore'))
                self.assertEqual(status['asOf'],'2026-10-28')
                self.assertEqual(status['source'],'outage_cache')
                with self.assertRaises(RuntimeError):scan.contest_universe(root,datetime(2026,11,10).date())

    def test_same_day_universe_does_not_repeat_public_request(self):
        with tempfile.TemporaryDirectory() as d, patch.object(scan,'load_market_universe',return_value=[SimpleNamespace(code='A',name='A',marcap=1)]) as api:
            scan.contest_universe(Path(d),datetime(2026,10,29).date())
            scan.contest_universe(Path(d),datetime(2026,10,29).date())
            self.assertEqual(api.call_count,1)

    def test_prepared_scores_require_matching_date_code_and_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cache=root/'runtime/kis-history/KR_A.json.gz'
            cache.parent.mkdir(parents=True);cache.write_bytes(b'completed history')
            day=datetime(2026,10,22).date()
            payload={'sessionDate':day.isoformat(),'scoringRevision':scan.scoring_revision(),
                     'summaries':[{'code':'A','historyDigest':scan.cache_digest(root,'A'),'confidenceScore':58}]}
            self.assertIn('A',scan.reusable_prepared(root,payload,day,{'A'}))
            self.assertEqual(scan.reusable_prepared(root,payload,datetime(2026,10,23).date(),{'A'}),{})
            self.assertEqual(scan.reusable_prepared(root,payload,day,set()),{})
            cache.write_bytes(b'corrected history')
            self.assertEqual(scan.reusable_prepared(root,payload,day,{'A'}),{})

    def test_morning_uses_prepared_results_without_api_or_recalculation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);day=datetime.now(scan.KST).date().isoformat()
            rows=[]
            for code in ['A','B']:
                cache=root/f'runtime/kis-history/KR_{code}.json.gz';cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(code.encode())
                rows.append({'code':code,'confidenceScore':58,'scoreBasis':'completed_daily_candles','kisCheckedSession':day,'historyDigest':scan.cache_digest(root,code)})
            p=root/'runtime/checkpoints/contest-prepared-KR.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'sessionDate':day,'scoringRevision':scan.scoring_revision(),'summaries':rows}))
            result,events=self.exercise(d,'23:59:59')
            self.assertEqual(events,[])
            self.assertEqual(result['preparedReuseCount'],2)
            self.assertEqual(result['successCount'],2)

    def test_evening_includes_today_close_and_preserves_active_candidates(self):
        class Evening(datetime):
            @classmethod
            def now(cls,tz=None):return cls(2026,10,23,18,tzinfo=tz)
        with tempfile.TemporaryDirectory() as d, ExitStack() as s:
            root=Path(d);active=root/'runtime/checkpoints/contest_candidates_KR.json'
            active.parent.mkdir(parents=True);active.write_text('{"summaries":[]}')
            frame=pd.DataFrame([{'date':'2026-10-22','close':100},{'date':'2026-10-23','close':110}])
            def fetch(client,directory,code,day,**kwargs):
                directory.mkdir(parents=True,exist_ok=True);(directory/f'KR_{code}.json.gz').write_bytes(b'closed Friday history')
                return frame
            s.enter_context(patch.object(scan,'datetime',Evening))
            s.enter_context(patch.object(scan,'load_market_universe',return_value=[SimpleNamespace(code='A',name='A',marcap=1)]))
            s.enter_context(patch.object(scan.KISPaperConfig,'from_env',return_value=None))
            s.enter_context(patch.object(scan,'KISPaperClient',return_value=SimpleNamespace(request_interval=2)))
            s.enter_context(patch.object(scan,'load_kis_candles',side_effect=fetch))
            valid=s.enter_context(patch.object(scan,'valid_history',side_effect=lambda rows,day:pd.DataFrame(rows)))
            s.enter_context(patch.object(scan,'analyze_stock',side_effect=lambda frame,identity:{'code':'A','currentPrice':float(frame.iloc[-1]['close'])}))
            s.enter_context(patch.object(scan,'to_summary',side_effect=lambda x:x))
            result=scan.run(SimpleNamespace(root=d,until='23:50',warm_only=True))
            data=json.loads((root/'runtime/checkpoints/contest-prepared-KR.json').read_text())
            self.assertEqual(data['sessionDate'],'2026-10-26')
            self.assertEqual(valid.call_args.args[1].isoformat(),'2026-10-26')
            self.assertEqual(data['summaries'][0]['currentPrice'],110)
            self.assertEqual(active.read_text(),'{"summaries":[]}')
            self.assertEqual(result['successCount'],1)

    def exercise(self, directory, until, rest_error=None):
        events = []
        rows = [SimpleNamespace(code=c, name=c, marcap=m) for c,m in [('A',2),('B',1)]]
        def cached(directory, code, day):
            events.append('cache:'+code)
            if code == 'A': raise ValueError('missing')
            return SimpleNamespace(to_dict=lambda orient: [])
        def rest(*args, **kwargs):
            events.append('rest:'+args[2])
            if rest_error: raise rest_error
            return SimpleNamespace(to_dict=lambda orient: [])
        with ExitStack() as s:
            s.enter_context(patch.object(scan,'load_market_universe',return_value=rows))
            s.enter_context(patch.object(scan,'load_cached_score_history',side_effect=cached))
            s.enter_context(patch.object(scan,'load_kis_candles',side_effect=rest))
            s.enter_context(patch.object(scan,'valid_history',side_effect=lambda rows,day: rows))
            s.enter_context(patch.object(scan,'analyze_stock',side_effect=lambda frame,identity:{'code':identity.code,'confidenceScore':58}))
            s.enter_context(patch.object(scan,'to_summary',side_effect=lambda payload:payload))
            s.enter_context(patch.object(scan.KISPaperConfig,'from_env',return_value=None))
            s.enter_context(patch.object(scan,'KISPaperClient',return_value=SimpleNamespace(request_interval=2)))
            result=scan.run(SimpleNamespace(root=directory,until=until,warm_only=False))
        return result,events

    def test_expected_short_history_is_classified_and_not_retried_same_day(self):
        with tempfile.TemporaryDirectory() as d:
            result,events=self.exercise(d,'23:59:59',scan.InsufficientHistoryError(20))
            self.assertEqual(result['dataUnavailableCount'],1)
            self.assertEqual(result['errorCount'],0)
            self.assertEqual(result['failedCodes'][0]['availableCandles'],20)
            again,events=self.exercise(d,'23:59:59',scan.InsufficientHistoryError(20))
            self.assertEqual(events,[])
            self.assertEqual(again['dataUnavailableCount'],1)

    def test_all_disk_hits_precede_rest_and_same_day_resume_skips_completed(self):
        with tempfile.TemporaryDirectory() as d:
            result,events=self.exercise(d,'23:59:59')
            self.assertEqual(events,['cache:A','cache:B','rest:A'])
            self.assertEqual(result['successCount'],2)
            again,events=self.exercise(d,'23:59:59')
            self.assertEqual(events,[])
            self.assertEqual(again['successCount'],2)

    def test_deadline_keeps_cache_results_and_unknown_score_is_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            result,events=self.exercise(d,'00:00')
            self.assertEqual(events,['cache:A','cache:B'])
            self.assertEqual(result['status'],'interrupted')
            self.assertEqual(result['remainingCount'],1)
            data=json.loads((Path(d)/'runtime/checkpoints/contest_candidates_KR.json').read_text())
            pending=next(r for r in data['summaries'] if r['code']=='A')
            self.assertTrue(pending['scorePending'])
            self.assertIsNone(pending['confidenceScore'])
            self.assertTrue(list((Path(d)/'runtime/scan-audit').glob('*.json')))


if __name__=='__main__': unittest.main()
