"""Cached, calendar-position Stage 2A construction, without outcome inputs."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
import duckdb
from .baseline import compute_features

ROOT=Path(__file__).resolve().parents[2]
FEATURES=('reversal_5','momentum_60_skip5','volatility_20','turnover_20','dollar_liquidity_20','volume_shock_20','gap_1','intraday_1')
FOLDER=ROOT/'data/interim/stage2a_features'


def setup(c):
    c.execute("SET threads=2; SET memory_limit='2GB'")
    (FOLDER/'temp').mkdir(parents=True,exist_ok=True)
    c.execute(f"SET temp_directory='{FOLDER/'temp'}'")
    c.execute(f'''CREATE TABLE calendar AS SELECT dlycaldt, row_number() OVER(ORDER BY dlycaldt)-1 td,
        lag(dlycaldt) OVER(ORDER BY dlycaldt) previous_date FROM
        (SELECT DISTINCT dlycaldt FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_parts/part_*.parquet'}'))''')
    c.execute(f'''CREATE TABLE event_terms AS SELECT permno,cal.dlycaldt exdate,count(*) event_count,
        bool_or(disdeclaredt>disexdt) chronology_conflict,
        bool_or(NOT coalesce((dispaymenttype='USD' AND disordinaryflg='Y'
            AND distype IN ('CD','SD','ROC','CG') AND disfacpr=0 AND disfacshr=0 AND disdivamt>=0
            AND coalesce(dispermno,0)=0) OR
            (dispaymenttype='SS' AND distype='FRS' AND disdetailtype IN ('STKSPL','STKDIV')
            AND abs(disfacpr-disfacshr)<=1e-6 AND disfacpr>-1 AND coalesce(dispermno,0)=0),false)) unsupported,
        sum(CASE WHEN dispaymenttype='USD' AND disordinaryflg='Y' THEN disdivamt ELSE 0 END) ordinary,
        sum(CASE WHEN dispaymenttype='USD' AND disordinaryflg='N' THEN disdivamt ELSE 0 END) nonordinary,
        product(1+disfacpr) factor,
        bool_or(NOT coalesce(dispaymenttype IN ('USD','SS') AND disfacpr IS NOT NULL
            AND (dispaymenttype='USD' OR (distype='FRS' AND disdetailtype IN ('STKSPL','STKDIV')))
            AND coalesce(dispermno,0)=0,false)) unverified_terms
        FROM read_parquet('{ROOT/'data/interim/stage2a_events/stkdistributions.parquet'}') e ASOF LEFT JOIN calendar cal ON e.disexdt::DATE<=cal.dlycaldt GROUP BY 1,2''')
    c.execute(f'''CREATE TABLE stored_delists AS SELECT DISTINCT permno,deldlydt::DATE dlycaldt
        FROM read_parquet('{ROOT/'data/interim/stage2a_events/stkdelists.parquet'}') WHERE deldlydt IS NOT NULL''')


def input_sql(path,bounded=False):
    restriction="WHERE d.dlycaldt BETWEEN DATE '2020-07-01' AND DATE '2021-04-30'" if bounded else ''
    return f'''WITH fields AS (
      SELECT d.permno,d.dlycaldt,d.eligible,d.dlyprc,d.dlyopen,d.dlyvol,d.dlycap,d.dlyprcflg,
        d.dlyprevprc,d.dlyprevprcflg,d.lag_prc,d.lag_date,d.dlyret,d.dlyretdurflg,
        d.dlyfacprc,d.dlyorddivamt,d.dlynonorddivamt,d.dlydelflg,cal.td,cal.previous_date,
        coalesce(e.event_count,0) event_count,coalesce(e.unsupported,false) unsupported,
        sd.permno IS NOT NULL stored_delist,
        coalesce((e.permno IS NULL AND d.dlyfacprc<>1) OR
          (NOT e.unsupported AND abs(e.factor-d.dlyfacprc)>1.000001e-6),false) event_terms_unverified,
        coalesce(e.chronology_conflict AND (e.unverified_terms
          OR abs(e.ordinary-d.dlyorddivamt)>1e-6 OR abs(e.nonordinary-d.dlynonorddivamt)>1e-6
          OR abs(e.factor-d.dlyfacprc)>1e-6
          OR NOT coalesce(d.dlyprc>0 AND d.dlyprevprc>0 AND
             abs((d.dlyprc*d.dlyfacprc+d.dlyorddivamt+d.dlynonorddivamt)/d.dlyprevprc-1-d.dlyret)<=1e-6,false)),false) timing_ambiguous
      FROM read_parquet('{path}') d JOIN calendar cal USING(dlycaldt)
      LEFT JOIN event_terms e ON d.permno=e.permno AND d.dlycaldt=e.exdate
      LEFT JOIN stored_delists sd ON d.permno=sd.permno AND d.dlycaldt=sd.dlycaldt {restriction}
    ), measured AS (
      SELECT *,coalesce(dlyprcflg='TR' AND isfinite(dlyprc) AND dlyprc>0,false) actual_close,
        coalesce(dlyprcflg='TR' AND isfinite(dlyprc) AND dlyprc>0 AND isfinite(dlyvol) AND dlyvol>=0,false) valid_dollar,
        coalesce(lag_date=previous_date AND dlyprevprcflg='TR' AND lag_prc>0 AND dlyprevprc>0
          AND abs(dlyprevprc-lag_prc)<=1e-6,false) adjacent_anchor,
        coalesce(dlyprc>0 AND dlyprevprc>0 AND isfinite(dlyret) AND dlyret>=-1 AND isfinite(dlyfacprc)
          AND dlyfacprc>0 AND isfinite(dlyorddivamt) AND isfinite(dlynonorddivamt)
          AND abs((dlyprc*dlyfacprc+dlyorddivamt+dlynonorddivamt)/dlyprevprc-1-dlyret)<=1e-6,false) return_identity
      FROM fields
    ) SELECT *,
      CASE WHEN actual_close AND adjacent_anchor AND return_identity AND dlydelflg='N'
        AND dlyretdurflg IN ('D1','D2','D3','D4','DU') AND NOT stored_delist AND NOT unsupported
        AND NOT timing_ambiguous AND NOT event_terms_unverified AND dlynonorddivamt=0 THEN dlyret END admitted_ret,
      CASE WHEN valid_dollar THEN dlyprc*dlyvol END dollar,
      CASE WHEN valid_dollar AND isfinite(dlycap) AND dlycap>0 THEN dlyprc*dlyvol/(1000*dlycap) END turnover,
      CASE WHEN actual_close AND isfinite(dlyopen) AND dlyopen>0 THEN dlyprc/dlyopen-1 END intraday,
      CASE WHEN actual_close AND isfinite(dlyopen) AND dlyopen>0 AND adjacent_anchor
        AND event_count=0 AND NOT stored_delist AND NOT timing_ambiguous AND dlydelflg='N'
        AND dlyfacprc=1 AND dlyorddivamt=0 AND dlynonorddivamt=0 THEN dlyopen/lag_prc-1 END gap
      FROM measured'''


def raw_sql(bounded=False):
    windows={'r5':(4,0),'mom':(59,5),'v20':(19,0),'l20':(19,0),'prior':(20,1)}
    definitions=', '.join(f"{name} AS (PARTITION BY permno ORDER BY td RANGE BETWEEN {lo} PRECEDING AND {'CURRENT ROW' if hi==0 else str(hi)+' PRECEDING'})" for name,(lo,hi) in windows.items())
    inner=['*']
    for name in ('r5','mom','v20'):
        inner += [f'count(admitted_ret) OVER {name} {name}_n',f'sum(timing_ambiguous::INT) OVER {name} {name}_amb',f'sum(event_terms_unverified::INT) OVER {name} {name}_unverified']
    inner += ['product(1+admitted_ret) OVER r5 r5_product','product(1+admitted_ret) OVER mom mom_product',
        'stddev_samp(admitted_ret) OVER v20 v20_std','count(dollar) OVER l20 dollar_n',
        'avg(dollar) OVER l20 dollar_mean','count(turnover) OVER l20 turnover_n','avg(turnover) OVER l20 turnover_mean',
        'count(dollar) OVER prior prior_n','avg(dollar) OVER prior prior_mean']
    raw={'reversal_5':('td>=4 AND r5_n=5','1-r5_product','r5_n','r5_amb'),
        'momentum_60_skip5':('td>=59 AND mom_n=55','mom_product-1','mom_n','mom_amb'),
        'volatility_20':('td>=19 AND v20_n=20','v20_std','v20_n','v20_amb'),
        'turnover_20':('td>=19 AND turnover_n>=15','ln(1+turnover_mean)','turnover_n','0'),
        'dollar_liquidity_20':('td>=19 AND dollar_n>=15','ln(1+dollar_mean)','dollar_n','0'),
        'volume_shock_20':('td>=20 AND prior_n>=15 AND dollar IS NOT NULL','ln(1+dollar)-ln(1+prior_mean)','prior_n','0'),
        'gap_1':('gap IS NOT NULL','gap','(gap IS NOT NULL)::INT','timing_ambiguous::INT'),
        'intraday_1':('intraday IS NOT NULL','intraday','(intraday IS NOT NULL)::INT','0')}
    cols=['permno','dlycaldt signal_date','dlycaldt max_input_date','event_count>0 distribution_event',
          'stored_delist OR dlydelflg<>\'N\' stored_delisting_event','timing_ambiguous source_timing_ambiguous','event_terms_unverified source_event_terms_unverified']
    for feature,(valid,value,n,amb) in raw.items():
        unverified={'reversal_5':'r5_unverified','momentum_60_skip5':'mom_unverified','volatility_20':'v20_unverified'}.get(feature,'0')
        minimum={'reversal_5':4,'momentum_60_skip5':59,'volatility_20':19,'turnover_20':19,'dollar_liquidity_20':19,'volume_shock_20':20,'gap_1':1,'intraday_1':0}[feature]
        cols += [f'CASE WHEN {valid} THEN {value} END {feature}_raw',f'{n} {feature}_n_valid',
          f"CASE WHEN {valid} THEN 'observed' WHEN {amb}>0 THEN 'timing_ambiguous' WHEN {unverified}>0 THEN 'unverified_event_terms' WHEN td<{minimum} THEN 'insufficient_calendar_history' ELSE 'insufficient_or_invalid_through_t_inputs' END {feature}_reason"]
    restriction=" AND dlycaldt>=DATE '2020-11-01'" if bounded else ''
    return 'WITH rolling AS (SELECT '+','.join(inner)+' FROM inputs WINDOW '+definitions+') SELECT '+','.join(cols)+' FROM rolling WHERE eligible'+restriction


def bounded():
    c=duckdb.connect();setup(c)
    path=ROOT/'data/interim/reconstruction_diagnostic_parts/part_00.parquet'
    c.execute('CREATE TABLE inputs AS '+input_sql(path,True))
    c.execute('CREATE TABLE raw AS '+raw_sql(True))
    assert c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM raw').fetchone()==(4971,4971)
    # Compare all eight raw values/n_valid with the pure approved fixture engine
    # on a deterministic first three eligible securities x last sample date.
    selected=c.execute('SELECT permno,max(signal_date) FROM raw GROUP BY 1 ORDER BY 1 LIMIT 3').fetchall()
    calendar=[r[0] for r in c.execute('SELECT dlycaldt FROM calendar ORDER BY td').fetchall()]
    checked=0
    for permno,t in selected:
        cur=c.execute('SELECT * FROM inputs WHERE permno=? ORDER BY dlycaldt',[permno])
        names=[r[0] for r in cur.description];rows={}
        for values in cur.fetchall():
            r=dict(zip(names,values));r.update(source_prev_date=r['lag_date'],volume_verified=True,cap_verified=True,
                event_verified=not r['unsupported'] and not r['timing_ambiguous'] and not r['event_terms_unverified'],event_known_date=r['dlycaldt'],
                event_type='ordinary_cash' if r['event_count'] else 'none')
            rows[r['dlycaldt']]=r
        expected=compute_features(calendar,rows,t)
        cur=c.execute('SELECT * FROM raw WHERE permno=? AND signal_date=?',[permno,t])
        observed=dict(zip([r[0] for r in cur.description],cur.fetchone()))
        for feature,e in expected.items():
            val=observed[feature+'_raw'];assert (val is None)==(e.raw is None),(feature,val,e)
            if val is not None:assert abs(val-e.raw)<=1e-10,(feature,val,e.raw)
            assert observed[feature+'_n_valid']==e.n_valid
            checked+=1
    out=ROOT/'results/tables/stage2a/bounded_feature_qa.csv'
    c.execute(f"COPY (SELECT '{checked} fixture comparisons passed' qa_check, count(*) observations FROM raw UNION ALL SELECT 'duplicate keys',count(*)-count(DISTINCT(permno,signal_date)) FROM raw) TO '{out}' (HEADER,DELIMITER ',')")
    print(json.dumps({'bounded_rows':4971,'raw_value_and_count_comparisons':checked,'qa_passed':True}))
    return c


def fingerprint():
    files=sorted((ROOT/'data/interim/reconstruction_diagnostic_parts').glob('part_*.parquet'))+[ROOT/'data/interim/stage2a_events/stkdistributions.parquet',ROOT/'data/interim/stage2a_events/stkdelists.parquet']
    sources={str(p.relative_to(ROOT)):{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in files}
    code=hashlib.sha256(b''.join((ROOT/name).read_bytes() for name in ('src/features/panel.py','src/features/baseline.py','src/features/returns.py'))).hexdigest()
    return {'sources':sources,'code_sha256':code,'specification':'RL-048 effective-date reconciliation; approved eight baseline definitions'}


def full():
    FOLDER.mkdir(exist_ok=True,parents=True);(FOLDER/'raw_parts').mkdir(exist_ok=True);(FOLDER/'parts').mkdir(exist_ok=True)
    fp=fingerprint();mp=FOLDER/'manifest.json'
    m=json.loads(mp.read_text()) if mp.exists() else {'fingerprint':fp,'raw_batches':{},'complete':False}
    if m['fingerprint']!=fp:raise RuntimeError('Feature-cache fingerprint changed; explicit rebuild required')
    c=duckdb.connect();setup(c)
    for part in range(32):
        dest=FOLDER/f'raw_parts/part_{part:02d}.parquet'
        if str(part) in m['raw_batches']:
            assert hashlib.sha256(dest.read_bytes()).hexdigest()==m['raw_batches'][str(part)]['sha256']
            print(f'raw batch {part+1}/32: verified resume',flush=True);continue
        c.execute('DROP TABLE IF EXISTS inputs')
        path=ROOT/f'data/interim/reconstruction_diagnostic_parts/part_{part:02d}.parquet'
        c.execute('CREATE TABLE inputs AS '+input_sql(path))
        duplicate=c.execute('SELECT count(*)-count(DISTINCT(permno,dlycaldt)) FROM inputs').fetchone()[0]
        if duplicate:raise RuntimeError('Duplicate source keys')
        c.execute('CREATE OR REPLACE TABLE raw_batch AS '+raw_sql())
        count=c.execute('SELECT count(*) FROM raw_batch').fetchone()[0]
        expected=c.execute('SELECT count(*) FROM inputs WHERE eligible').fetchone()[0];assert count==expected
        assert c.execute('SELECT count(*) FROM raw_batch WHERE max_input_date>signal_date').fetchone()[0]==0
        tmp=dest.with_suffix('.tmp.parquet');c.execute(f"COPY raw_batch TO '{tmp}' (FORMAT PARQUET,COMPRESSION ZSTD)");tmp.replace(dest)
        m['raw_batches'][str(part)]={'rows':count,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
        mp.write_text(json.dumps(m,indent=2)+'\n');print(f'raw batch {part+1}/32: {count:,} keys',flush=True)
    c.execute('DROP TABLE IF EXISTS inputs;DROP TABLE IF EXISTS raw_batch')
    c.execute(f"CREATE VIEW raw AS SELECT * FROM read_parquet('{FOLDER/'raw_parts/part_*.parquet'}')")
    count,unique=c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM raw').fetchone();assert count==unique==6699101
    # Only identifiers are projected from targets; no outcome status/value is used.
    target=ROOT/'data/interim/stage1g_targets/targets_5d.parquet'
    for left,right in [('raw',f"read_parquet('{target}')"),(f"read_parquet('{target}')",'raw')]:
        assert c.execute(f'SELECT count(*) FROM (SELECT permno,signal_date FROM {left} EXCEPT SELECT permno,signal_date FROM {right})').fetchone()[0]==0
    stats=[]
    for feature in FEATURES:
        v=feature+'_raw';name='stats_'+feature
        c.execute(f'''CREATE TABLE {name} AS WITH q AS (SELECT signal_date,count({v}) n,
            quantile_cont({v},.01) lo,quantile_cont({v},.99) hi FROM raw
            WHERE isfinite({v}) GROUP BY 1), clipped AS (SELECT r.signal_date,
            least(q.hi,greatest(q.lo,r.{v})) x FROM raw r JOIN q USING(signal_date) WHERE q.n>=30 AND isfinite(r.{v}))
            SELECT q.*,m.mu,m.sd FROM q LEFT JOIN (SELECT signal_date,avg(x) mu,stddev_pop(x) sd FROM clipped GROUP BY 1) m USING(signal_date)''')
        stats.append(f"SELECT '{feature}' feature,* FROM {name}")
        print(f'preprocessing statistics: {feature}',flush=True)
    c.execute(f"COPY ({' UNION ALL '.join(stats)}) TO '{FOLDER/'cross_section_stats.parquet'}' (FORMAT PARQUET)")
    select=['r.*'];joins=[]
    for i,feature in enumerate(FEATURES):
        alias='s'+str(i);v='r.'+feature+'_raw';clip=f'CASE WHEN {alias}.n>=30 AND isfinite({v}) THEN least({alias}.hi,greatest({alias}.lo,{v})) END'
        select += [f'{clip} {feature}_clipped',f'CASE WHEN {alias}.sd=0 AND {v} IS NOT NULL AND {alias}.n>=30 THEN 0 ELSE ({clip}-{alias}.mu)/nullif({alias}.sd,0) END {feature}_z',
            f'NOT coalesce(isfinite({v}),false) {feature}_raw_missing',f'coalesce({alias}.sd=0 AND {alias}.n>=30,false) {feature}_constant_cross_section',
            f"CASE WHEN {v} IS NULL THEN r.{feature}_reason WHEN coalesce({alias}.n,0)<30 THEN 'insufficient_cross_section' WHEN {alias}.sd=0 THEN 'constant_cross_section' ELSE 'observed' END {feature}_processed_reason"]
        joins.append(f'LEFT JOIN stats_{feature} {alias} USING(signal_date)')
    final=[]
    for part in range(32):
        dest=FOLDER/f'parts/part_{part:02d}.parquet';tmp=dest.with_suffix('.tmp.parquet')
        query='SELECT '+','.join(select)+f" FROM read_parquet('{FOLDER/f'raw_parts/part_{part:02d}.parquet'}') r "+' '.join(joins)
        c.execute(f"COPY ({query}) TO '{tmp}' (FORMAT PARQUET,COMPRESSION ZSTD)");tmp.replace(dest)
        final.append({'file':str(dest.relative_to(ROOT)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        print(f'processed batch {part+1}/32 complete',flush=True)
    m.update(rows=count,unique_keys=unique,complete=True,constructed_at_utc=datetime.now(timezone.utc).isoformat(),
        features=list(FEATURES),target_fields_read=['permno','signal_date'],outcome_fields_used=False,
        raw_scanned=False,network_queries=0,final_files=final,qa_passed=False,
        target_metadata_preservation='Frozen target relation unchanged; join after feature computation only.')
    mp.write_text(json.dumps(m,indent=2)+'\n')
    return c


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--full',action='store_true');args=p.parse_args()
    bounded()
    if args.full:full()

if __name__=='__main__':main()
