import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from src.models.walk_forward import fit_moments,date_moments
from src.models.stage5_pipeline import forecast,select_fit,make_schedule,evaluate,CANDIDATES


def fixture():
    rng=np.random.default_rng(15);x=rng.normal(size=(100,8));x[:,5]=x[:,4]
    y=.02*x[:,0]-.01*x[:,7]+rng.normal(0,.02,100)
    d=pd.to_datetime(np.repeat(['2019-06-03','2019-06-04','2020-01-02'],[20,30,50]))
    e=d+pd.Timedelta(days=9)
    return x,y,d,e


def test_same_normalized_primary_and_univariate_models():
    x,y,d,e=fixture();fit=select_fit(fit_moments(date_moments(x,y,d,e,e),'2019-12-31'))
    keep=d.year<2020;a=x[keep];b=y[keep]
    counts=pd.Series(d[keep]).value_counts();w=np.array([1/(len(counts)*counts[t]) for t in d[keep]])
    ridge=Ridge(alpha=1,solver='svd').fit(a,b,sample_weight=w)
    uni=Ridge(alpha=1,solver='svd').fit(a[:,[0]],b,sample_weight=w)
    p,valid=forecast(x,fit)
    np.testing.assert_allclose(p[:,2],ridge.predict(x),atol=1e-12)
    np.testing.assert_allclose(p[:,1],uni.predict(x[:,[0]]),atol=1e-12)
    np.testing.assert_array_equal(p[:,0],x[:,0]);assert valid.all()


def test_future_label_and_feature_perturbation_cannot_change_cutoff_fit():
    x,y,d,e=fixture();a=select_fit(fit_moments(date_moments(x,y,d,e,e),'2019-12-31'))
    xx=x.copy();yy=y.copy();future=d.year==2020;xx[future]=1e7;yy[future]=-1e9
    b=select_fit(fit_moments(date_moments(xx,yy,d,e,e),'2019-12-31'))
    np.testing.assert_array_equal(forecast(x[:30],a)[0],forecast(x[:30],b)[0])


def test_later_holdout_labels_enter_only_after_maturity():
    x,y,d,e=fixture();m=date_moments(x,y,d,e,e)
    a=fit_moments(m,'2019-12-31');b=fit_moments(m,'2020-01-10');c=fit_moments(m,'2020-01-13')
    assert a['training_rows']==b['training_rows']==50
    assert c['training_rows']==100 and c['max_training_maturity']=='2020-01-11'


def test_quarter_schedule_and_global_six_day_purge():
    dates=pd.bdate_range('1993-01-04','2025-12-31').difference(pd.to_datetime(['2020-01-01']))
    cal=pd.DataFrame({'signal_date':dates,'td':range(len(dates))});s=make_schedule(cal)
    assert len(s)==24 and s.quarter.iloc[0]=='2020Q1' and s.quarter.iloc[-1]=='2025Q4'
    assert s.fit_information_cutoff.iloc[0]==pd.Timestamp('2019-12-31')
    for r in s.itertuples():
        first=int(cal.index[cal.signal_date==r.evaluation_first_signal_date][0])
        assert cal.signal_date.iloc[first-7]==r.latest_calendar_mature_signal_date
        assert r.fit_information_cutoff<r.evaluation_first_signal_date


def test_no_target_status_api_and_missing_inputs_preserved():
    x,y,d,e=fixture();fit=select_fit(fit_moments(date_moments(x,y,d,e,e),'2019-12-31'))
    x[0,4]=np.nan;x[1,0]=np.nan;p,v=forecast(x,fit)
    assert len(p)==100 and np.isfinite(p[0,0]) and np.isnan(p[0,1:]).all()
    assert np.isnan(p[1]).all() and not v[:2].any()
    with pytest.raises(TypeError):forecast(x,fit,label_status=['observed']*100)


def test_paired_keys_ties_quintiles_and_missing_labels():
    n=50;x=np.repeat(np.arange(10),5).astype(float);y=np.linspace(-.1,.1,n)
    d=pd.DataFrame(dict(permno=np.arange(n),signal_date=pd.Timestamp('2020-01-02'),target_5d=y,
                        raw_reversal=x,univariate_reversal_ridge=x,ridge=x))
    d.loc[:4,'ridge']=np.nan;d.loc[:4,'univariate_reversal_ridge']=np.nan
    d.loc[5,'target_5d']=np.nan
    cal=pd.DataFrame(dict(signal_date=[pd.Timestamp('2020-01-02')],td=[6796]))
    daily,q,p=evaluate(d,cal)
    matched=daily[daily['sample']=='matched_complete8']
    assert matched.n_pairs.eq(44).all() and p.n_common_keys.eq(44).all()
    assert p.ic.eq(0).all() and p.identical_security_keys.all()
    assert daily[(daily.model=='raw_reversal')&(daily['sample']=='primary_available')].n_pairs.iloc[0]==49
    # All ties stay intact under the shared quintile helper; aggregate counts reconcile.
    for (model,scope),a in q.groupby(['model','sample']):
        assert a.n_pairs.sum()==daily[(daily.model==model)&(daily['sample']==scope)].n_pairs.iloc[0]


def test_undefined_constant_is_not_silently_ranked():
    d=pd.DataFrame(dict(permno=range(40),signal_date=pd.Timestamp('2020-01-02'),target_5d=range(40),
                        raw_reversal=1.,univariate_reversal_ridge=1.,ridge=1.))
    daily,q,p=evaluate(d,pd.DataFrame(dict(signal_date=[pd.Timestamp('2020-01-02')],td=[6796])))
    assert daily.ic.isna().all() and daily.ic_reason.eq('constant_rank_vector').all()
    assert q.empty and p.ic.isna().all()


def test_outcome_join_reordering_does_not_change_keyed_predictions():
    from src.models.stage5_pipeline import join_evaluation
    p=pd.DataFrame(dict(permno=[2,1,2,1],signal_date=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-03','2020-01-02']),ridge=[.2,.1,.3,.4]))
    l=p[['permno','signal_date']].sample(frac=1,random_state=12).copy();l['target_5d']=[4,3,2,1]
    joined=join_evaluation(p,l);expected=p.sort_values(['signal_date','permno']).reset_index(drop=True)
    pd.testing.assert_frame_equal(joined[p.columns],expected)
    assert joined.set_index(['permno','signal_date']).target_5d.to_dict()==l.set_index(['permno','signal_date']).target_5d.to_dict()
    assert 'target_5d' not in p
