"""Read-only cloud inventory; never print credentials or document contents."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from strategy_engine.repositories import init_firestore, resolve_cred_path
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession


def main():
    credentials = service_account.Credentials.from_service_account_file(
        str(resolve_cred_path()), scopes=['https://www.googleapis.com/auth/cloud-platform'])
    session = AuthorizedSession(credentials)
    project = credentials.project_id
    print(json.dumps({'project': project, 'serviceAccount': credentials.service_account_email}), flush=True)
    now = datetime.now(timezone.utc)
    for metric in ['storage/data_and_index_storage_bytes', 'storage/pitr_storage_bytes',
                   'storage/backups_storage_bytes']:
        response = session.get(f'https://monitoring.googleapis.com/v3/projects/{project}/timeSeries', params={
            'filter': f'metric.type="firestore.googleapis.com/{metric}"',
            'interval.startTime': (now - timedelta(days=2)).isoformat(),
            'interval.endTime': now.isoformat(), 'pageSize': 10}, timeout=30)
        data = response.json()
        print(json.dumps({'metric': metric, 'http': response.status_code, 'error': data.get('error', {}).get('message'),
                          'series': [{'resource': s.get('resource'), 'latest': s.get('points', [])[:1]}
                                     for s in data.get('timeSeries', [])]}, ensure_ascii=False), flush=True)
    for name, url in [
        ('functions', f'https://cloudfunctions.googleapis.com/v1/projects/{project}/locations/-/functions'),
        ('billing', f'https://cloudbilling.googleapis.com/v1/projects/{project}/billingInfo'),
        ('database', f'https://firestore.googleapis.com/v1/projects/{project}/databases/(default)')]:
        response = session.get(url, timeout=30)
        data = response.json()
        print(json.dumps({'resource': name, 'http': response.status_code,
            'functions': [{'name': x.get('name'), 'status': x.get('status')} for x in data.get('functions', [])],
            'billingEnabled': data.get('billingEnabled'), 'databaseType': data.get('type'),
            'freeTier': data.get('freeTier'), 'pitr': data.get('pointInTimeRecoveryEnablement')}), flush=True)
    db = init_firestore()
    for name in ['strategy_candidates', 'stock_analysis', 'strategy_runs', 'meta_data', 'public_analysis_meta']:
        count = db.collection(name).count().get()[0][0].value
        print(json.dumps({'collection': name, 'count': count}), flush=True)


if __name__ == '__main__':
    main()
