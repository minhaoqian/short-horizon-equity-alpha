"""Resumable Stage 1G extraction. No connection unless explicitly executed.

Call run(connection) with an existing WRDS connection, or use the CLI with
--execute in a WRDS-capable environment. Licensed outputs stay gitignored.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/interim/stage1g_extraction'
COLUMNS = {
    'stkdelists': 'permno delistingdt deldlydt delamtdt deldtprc deldtprcflg delactiontype delstatustype delreasontype delpaymenttype deldistype delret delretmisstype delnextdt delnextprc delnextprcflg deldivamt delpermno delpermco'.split(),
    'stkdistributions': 'permno disexdt disseqnbr disordinaryflg dispaymenttype distype disdetailtype disdivamt disfacpr disfacshr dispaydt dispermno dispermco'.split(),
    'stkdlysecuritydata': 'permno dlycaldt dlyprevdt dlyretmissflg'.split(),
}


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def jobs():
    p=sorted(pd.read_parquet(OUT/'distribution_windows.parquet',columns=['permno']).permno.unique().tolist())
    d=pd.read_parquet(OUT/'daily_missing_field_dates.parquet',columns=['permno','dlycaldt']).sort_values(['permno','dlycaldt'])
    assert len(p)==3064 and len(d)==7900 and not d.duplicated().any()
    result=[('stkdelists',0,'SELECT '+', '.join(COLUMNS['stkdelists'])+' FROM crsp.stkdelists',{},None)]
    for start in range(0,len(p),500):
        values=p[start:start+500];params={f'p{i}':int(v) for i,v in enumerate(values)}
        sql='SELECT '+', '.join(COLUMNS['stkdistributions'])+' FROM crsp.stkdistributions WHERE permno IN ('+', '.join(f'%(p{i})s' for i in range(len(values)))+')'
        result.append(('stkdistributions',start//500,sql,params,set(values)))
    for start in range(0,len(d),2000):
        rows=list(d.iloc[start:start+2000].itertuples(index=False,name=None));params={}
        for i,(permno,dt) in enumerate(rows): params[f'p{i}']=int(permno);params[f'd{i}']=pd.Timestamp(dt).date()
        values=', '.join(f'(%(p{i})s::integer, %(d{i})s::date)' for i in range(len(rows)))
        sql='WITH keys(permno,dt) AS (VALUES '+values+') SELECT '+', '.join('d.'+x for x in COLUMNS['stkdlysecuritydata'])+' FROM crsp.stkdlysecuritydata d WHERE EXISTS (SELECT 1 FROM keys k WHERE k.permno=d.permno AND k.dt=d.dlycaldt)'
        result.append(('stkdlysecuritydata',start//2000,sql,params,{(int(p),pd.Timestamp(dt).date()) for p,dt in rows}))
    return result


def validate(table,df,scope):
    assert list(df.columns)==COLUMNS[table],f'Unexpected columns: {list(df.columns)}'
    assert df.permno.notna().all(),'Null security keys'
    for col in df.columns:
        if col.endswith('dt'): df[col]=pd.to_datetime(df[col],errors='raise')
    if table=='stkdistributions':
        assert set(df.permno).issubset(scope),'Unexpected security'
        assert df[['permno','disexdt','disseqnbr']].notna().all().all()
        assert not df.duplicated(['permno','disexdt','disseqnbr']).any(),'Duplicate distribution keys'
    if table=='stkdlysecuritydata':
        assert df.dlycaldt.notna().all() and not df.duplicated(['permno','dlycaldt']).any()
        actual={(int(p),pd.Timestamp(dt).date()) for p,dt in df[['permno','dlycaldt']].itertuples(index=False,name=None)}
        assert actual.issubset(scope),'Unrequested daily key'
        assert actual==scope,f'Missing {len(scope-actual)} requested existing daily keys; investigate rather than fill'
    return {'rows':len(df),'distinct_permnos':int(df.permno.nunique()),
      'dates':{col:{'min':str(df[col].min()),'max':str(df[col].max())} for col in df if col.endswith('dt')}}


def save_json(path,value):
    tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(value,indent=2,default=str)+'\n');tmp.replace(path)


def run(connection):
    """Execute only on explicit authorization; supplied connection is not closed."""
    work=jobs()
    selectors={name:digest(OUT/name) for name in ['distribution_windows.parquet','daily_missing_field_dates.parquet']}
    plan={'version':1,'selector_sha256':selectors,'columns':COLUMNS,'strategy':'full delists; distributions PERMNO-only; daily exact keys',
      'distribution_batch_permnos':500,'daily_batch_keys':2000,'expected_queries':len(work)}
    path=OUT/'download_manifest.json'
    if path.exists():
        m=json.loads(path.read_text());assert m['plan']==plan,'Plan/selectors changed; use a separate output directory'
    else:
        m={'plan':plan,'created_at_utc':datetime.now(timezone.utc).isoformat(),'batches':{},'complete':False}
    folder=OUT/'download_batches';folder.mkdir(exist_ok=True)
    save_json(path,m)
    failed_sources=set()
    m['errors']={}
    m['connection_verified']=True
    m.setdefault('wrds_observation_queries_executed',0)
    m.pop('last_error',None)
    save_json(path,m)
    for table,index,sql,params,scope in work:
        if table in failed_sources:
            continue
        key=f'{table}_{index:03d}';file=folder/f'{key}.parquet'
        if key in m['batches']:
            assert file.exists() and digest(file)==m['batches'][key]['sha256'],'Completed batch missing or changed'
            df=pd.read_parquet(file);validate(table,df,scope)
            print(f'{key}: resumed {len(df)} validated rows',flush=True)
            continue
        # Only SELECT statements; no server temp tables, count queries or writes.
        try:
            print(f'{key}: querying',flush=True)
            m['wrds_observation_queries_executed']+=1
            save_json(path,m)
            df=connection.raw_sql(sql,params=params)
            stats=validate(table,df,scope)
            tmp=file.with_suffix('.parquet.tmp');df.to_parquet(tmp,index=False);tmp.replace(file)
            m['batches'][key]={**stats,'file':str(file.relative_to(OUT)),'sha256':digest(file),'completed_at_utc':datetime.now(timezone.utc).isoformat()}
            m.pop('last_error',None);save_json(path,m)
            print(f'{key}: completed {len(df)} rows',flush=True)
        except Exception as exc:
            # Avoid persisting exception text that could contain connection secrets.
            m['last_error']={'batch':key,'exception_type':type(exc).__name__};save_json(path,m)
            failed_sources.add(table)
            # DB driver message omits SQLAlchemy's connection URL/parameters.
            message=str(getattr(exc,'orig',exc))
            m['errors'][table]={'batch':key,'exception_type':type(exc).__name__,'message':message}
            save_json(path,m)
            print(f'{key}: FAILED {type(exc).__name__}: {message}',flush=True)
    m['outputs']={}
    for table in COLUMNS:
        if table in failed_sources:
            continue
        frames=[pd.read_parquet(folder/f'{t}_{i:03d}.parquet') for t,i,*_ in work if t==table]
        df=pd.concat(frames,ignore_index=True)
        scope=set().union(*(s for t,i,sql,p,s in work if t==table and s is not None)) if table!='stkdelists' else None
        stats=validate(table,df,scope)
        file=OUT/f'{table}.parquet';tmp=file.with_suffix('.parquet.tmp');df.to_parquet(tmp,index=False);tmp.replace(file)
        m['outputs'][table]={**stats,'file':file.name,'sha256':digest(file)}
    m['complete']=not failed_sources;m['completed_at_utc']=datetime.now(timezone.utc).isoformat();save_json(path,m)
    m['source_status']={table:{'status':'FAILED' if table in failed_sources else 'COMPLETE',
      'completed_batches':sum(key.startswith(table+'_') for key in m['batches']),
      'downloaded_rows':sum(v['rows'] for key,v in m['batches'].items() if key.startswith(table+'_'))} for table in COLUMNS}
    if 'stkdlysecuritydata' in m['outputs']:
        m['daily_matched_keys']=m['outputs']['stkdlysecuritydata']['rows']
        m['daily_coverage_status']='PASSED: all requested existing keys matched'
    save_json(path,m)
    return m


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Connect to WRDS and execute the extraction; default is local plan only')
    parser.add_argument('--wrds-username',help='WRDS username for matching the existing home-directory pgpass entry')
    args=parser.parse_args()
    if not args.execute:
        work=jobs()
        print(json.dumps({'queries':len(work),'by_table':{t:sum(j[0]==t for j in work) for t in COLUMNS},'wrds_query_executed':False},indent=2))
        return
    import wrds
    connection=wrds.Connection(wrds_connect_args={'sslmode':'require','connect_timeout':30,'application_name':'Stage1G'},
        **({'wrds_username':args.wrds_username} if args.wrds_username else {}))
    try:
        check=connection.raw_sql("SELECT table_schema,table_name FROM information_schema.tables WHERE table_schema='crsp' AND table_name='stkdelists'")
        assert len(check)==1,'WRDS metadata check did not find crsp.stkdelists'
        print('WRDS connection active; metadata check passed',flush=True)
        run(connection)
    finally: connection.close()


if __name__=='__main__': main()
