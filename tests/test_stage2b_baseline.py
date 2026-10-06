import duckdb
import numpy as np
import pandas as pd
from src.evaluation.baseline import development_projection,ranked_pairs
from src.evaluation.statistics import rank_ic,quintiles


def test_holdout_excluded_cross_boundary_retained(tmp_path):
    f=pd.DataFrame({'permno':[1,2,3],'signal_date':pd.to_datetime(['2019-12-31','2020-01-02','1993-01-22']),
        'reversal_5_z':[.2,1e99,-.4]})
    t=f[['permno','signal_date']].copy();t['entry_date']=t.signal_date+pd.Timedelta(days=1)
    t['exit_date']=t.signal_date+pd.Timedelta(days=9);t['target_5d']=[.3,1e99,-.5]
    t['label_status']='measurable_ordinary_event_adjusted';t['label_reason']='observed'
    fp=tmp_path/'f.parquet';tp=tmp_path/'t.parquet';f.to_parquet(fp);t.to_parquet(tp)
    c=duckdb.connect();development_projection(c,fp,tp)
    assert c.execute('SELECT count(*) FROM f').fetchone()[0]==2
    assert c.execute("SELECT exit_date FROM labels WHERE signal_date=DATE '2019-12-31'").fetchone()[0].year==2020
    assert c.execute('SELECT max(abs(target_5d)) FROM labels').fetchone()[0]==.5
    c.close()


def test_sql_average_ranks_quintiles_and_missing_pairs():
    rng=np.random.default_rng(18);x=np.round(rng.normal(size=65),1);y=rng.normal(size=65)
    x[-1]=np.nan;y[-2]=np.nan
    frame=pd.DataFrame({'permno':range(65),'signal_date':pd.Timestamp('2010-02-01'),
                        'reversal_5_z':x,'target_5d':y})
    c=duckdb.connect();c.register('joined',frame);ranked_pairs(c,'reversal_5')
    n,ic=c.execute('SELECT n_pairs,ic FROM metrics').fetchone();expected,_,en=rank_ic(x,y)
    assert n==en==63 and abs(ic-expected)<1e-12
    got=c.execute('SELECT x,least(5,1+floor(5*(rx-.5)/n)) q FROM pairs ORDER BY permno').fetchdf()
    np.testing.assert_array_equal(got.q,quintiles(got.x))
    assert not got.groupby('x').q.nunique().gt(1).any()
    c.close()


def test_cash_delisting_numeric_labels_not_filtered():
    frame=pd.DataFrame({'permno':range(40),'signal_date':pd.Timestamp('2010-02-01'),
        'reversal_5_z':np.arange(40.),'target_5d':np.arange(40.)/100,
        'label_status':['measurable_cash_only_delisting']+['measurable_ordinary_event_adjusted']*39})
    c=duckdb.connect();c.register('joined',frame);ranked_pairs(c,'reversal_5')
    n,ic=c.execute('SELECT n_pairs,ic FROM metrics').fetchone()
    assert n==40 and abs(ic-1.)<1e-12
    c.close()
