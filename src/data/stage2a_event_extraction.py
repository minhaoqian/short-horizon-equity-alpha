"""Global outcome-independent Stage 2A event cache; exactly one authorized login."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import argparse
import shutil

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/interim/stage2a_events'
COLUMNS=['permno','disexdt','disseqnbr','disordinaryflg','dispaymenttype','distype',
    'disdetailtype','disdivamt','disfacpr','disfacshr','dispaydt','dispermno','dispermco','disdeclaredt']
BATCHES=[('1993-01-01','2002-01-01'),('2002-01-01','2011-01-01'),
    ('2011-01-01','2020-01-01'),('2020-01-01','2026-01-01')]
SQL='SELECT '+','.join(COLUMNS)+' FROM crsp.stkdistributions WHERE disexdt >= %(lo)s AND disexdt < %(hi)s'


def save(value):
    path=OUT/'manifest.json';tmp=path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(value,indent=2,default=str)+'\n');tmp.replace(path)


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight():
    OUT.mkdir(exist_ok=True)
    old=ROOT/'data/interim/stage1g_extraction'
    m=json.loads((old/'download_manifest.json').read_text())
    info=m['outputs']['stkdelists']
    source=old/info['file']
    assert m['complete'] and m['extraction_qa']['passed']
    assert checksum(source)==info['sha256']
    shutil.copyfile(source,OUT/'stkdelists.parquet')
    existing=OUT/'manifest.json'
    plan={'table':'crsp.stkdistributions','columns':COLUMNS,'batches':BATCHES,
        'predicate':'DisExDt only; all PERMNOs, event types, amounts and payment dates',
        'target_or_exception_selection':False}
    if existing.exists():
        m=json.loads(existing.read_text())
        assert json.dumps(m['plan'],sort_keys=True)==json.dumps(plan,sort_keys=True)
    else:
        m={'plan':plan,'complete':False,'batches':{},'login_attempts':0}
    m['delists']={'reused_complete_table':True,'file':'stkdelists.parquet',
        'sha256':checksum(OUT/'stkdelists.parquet'),'rows':29833}
    return m


def extract(connection,m):
    import pandas as pd
    for i,(lo,hi) in enumerate(BATCHES):
        path=OUT/f'distributions_batch_{i:02d}.parquet'
        if str(i) in m['batches']:
            assert checksum(path)==m['batches'][str(i)]['sha256']
            print(f'Batch {i+1}/4 checksum-verified resume',flush=True)
            continue
        print(f'Query distribution batch {i+1}/4: {lo} <= ex-date < {hi}',flush=True)
        frame=connection.raw_sql(SQL,params={'lo':lo,'hi':hi})
        assert list(frame.columns)==COLUMNS
        assert not frame[['permno','disexdt','disseqnbr']].isna().any().any()
        assert not frame.duplicated(['permno','disexdt','disseqnbr']).any()
        dates=pd.to_datetime(frame.disexdt)
        assert ((dates>=lo)&(dates<hi)).all()
        for col in ('disexdt','dispaydt','disdeclaredt'):
            frame[col]=pd.to_datetime(frame[col])
        temporary=path.with_suffix('.parquet.tmp')
        frame.to_parquet(temporary,index=False);temporary.replace(path)
        m['batches'][str(i)]={'rows':len(frame),'sha256':checksum(path),'lo':lo,'hi':hi}
        save(m)
        print(f'Batch {i+1}/4 complete: {len(frame):,} rows',flush=True)
    frame=pd.concat([pd.read_parquet(OUT/f'distributions_batch_{i:02d}.parquet') for i in range(4)],ignore_index=True)
    assert not frame.duplicated(['permno','disexdt','disseqnbr']).any()
    assert len(frame)==sum(v['rows'] for v in m['batches'].values())
    path=OUT/'stkdistributions.parquet'
    frame.to_parquet(path,index=False)
    m.update(complete=True,completed_at_utc=datetime.now(timezone.utc).isoformat(),
        rows=len(frame),distinct_permnos=int(frame.permno.nunique()),
        distribution_sha256=checksum(path),qa_passed=True,wrds_data_queries=len(BATCHES))
    save(m)
    print(f'Global distribution extract QA passed: {len(frame):,} rows',flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true')
    parser.add_argument('--wrds-username',help='Existing authorized WRDS username; password remains outside repository')
    args=parser.parse_args()
    m=preflight()
    if not args.execute:
        print(json.dumps(m['plan'],indent=2));return
    if m['complete']:
        assert checksum(OUT/'stkdistributions.parquet')==m['distribution_sha256']
        print('Complete cache verified; no login/query needed');return
    if m.get('authentication_failed'):
        raise RuntimeError('Prior authentication failed; stop for explicit human review, not automatic retry')
    if not args.wrds_username:
        parser.error('--wrds-username is required before one noninteractive login')
    import wrds
    from src.data.stage1g_wrds_extraction import single_login
    m['login_attempts']+=1;save(m)
    try:
        print('Initiating exactly one WRDS login; approve Duo if prompted',flush=True)
        db=single_login(wrds,args.wrds_username)
    except Exception as exc:
        driver=getattr(exc,'orig',exc)
        m['authentication_failed']=True;m['authentication_exception_class']=type(exc).__name__
        save(m)
        print('AUTHENTICATION FAILED; NO RETRY: '+type(exc).__module__+'.'+type(exc).__name__,flush=True)
        print(type(driver).__module__+'.'+type(driver).__name__+': '+str(driver),flush=True)
        raise SystemExit(1)
    try:
        print('Login succeeded; extracting on this connection only',flush=True)
        extract(db,m)
    except Exception as exc:
        driver=getattr(exc,'orig',exc)
        m['data_query_or_qa_failed']=type(exc).__name__;save(m)
        print('STOP; no reconnect/retry: '+type(exc).__name__+': '+str(driver),flush=True)
    finally:
        db.close();print('WRDS connection closed',flush=True)


if __name__=='__main__':main()
