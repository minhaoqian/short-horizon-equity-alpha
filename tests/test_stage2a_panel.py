from datetime import date,timedelta
from math import prod
import duckdb
import pandas as pd
from src.features.panel import raw_sql


def panel(missing=None):
    c=duckdb.connect()
    start=date(2020,1,1)
    frame=pd.DataFrame([dict(permno=1,dlycaldt=start+timedelta(days=i),td=i,eligible=True,
        event_count=0,event_terms_unverified=False,stored_delist=False,dlydelflg='N',timing_ambiguous=False,
        admitted_ret=.001*i,dollar=100.+i,turnover=.001,intraday=.02,gap=.01)
        for i in range(70) if i!=missing])
    c.register('fixture',frame);c.execute('CREATE TABLE inputs AS SELECT * FROM fixture')
    return c


def test_production_range_windows_and_skipped_momentum():
    c=panel(missing=67)
    names=[r[0] for r in c.execute('DESCRIBE ('+raw_sql()+')').fetchall()]
    r=dict(zip(names,c.execute(raw_sql()+' AND td=69').fetchone()))
    assert r['reversal_5_raw'] is None and r['reversal_5_n_valid']==4
    assert r['volatility_20_raw'] is None and r['volatility_20_n_valid']==19
    assert r['momentum_60_skip5_n_valid']==55
    assert abs(r['momentum_60_skip5_raw']-(prod(1+.001*i for i in range(10,65))-1))<1e-12
    assert r['dollar_liquidity_20_n_valid']==19
    assert r['dollar_liquidity_20_raw'] is not None


def test_timing_ambiguity_only_affects_relevant_feature_intervals():
    c=panel()
    c.execute('UPDATE inputs SET admitted_ret=NULL,timing_ambiguous=true,gap=NULL WHERE td=68')
    cur=c.execute(raw_sql()+' AND td=69');r=dict(zip([x[0] for x in cur.description],cur.fetchone()))
    assert r['reversal_5_reason']=='timing_ambiguous'
    assert r['volatility_20_reason']=='timing_ambiguous'
    assert r['momentum_60_skip5_reason']=='observed'
    assert r['intraday_1_reason']=='observed'
    assert r['turnover_20_reason']=='observed'


def test_production_future_rows_do_not_change_past_features():
    c=panel()
    before=c.execute(raw_sql()+' AND td=64').fetchone()
    c.execute("UPDATE inputs SET admitted_ret=-1,dollar=1e12,eligible=false WHERE td>64")
    assert c.execute(raw_sql()+' AND td=64').fetchone()==before
