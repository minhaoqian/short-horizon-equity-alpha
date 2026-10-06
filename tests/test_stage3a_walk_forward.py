import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from src.models.walk_forward import date_moments,fit_moments,predict


def fixture():
    r=np.random.default_rng(34);x=r.normal(size=(72,8));x[:,4]=x[:,3]
    y=.02*x[:,0]-.03*x[:,7]+r.normal(0,.02,72)
    d=pd.to_datetime(np.repeat(['2002-01-02','2002-01-03','2003-01-02'],[20,12,40]))
    e=d+pd.Timedelta(days=8);m=e.copy()
    return x,y,d,e,m


def test_normalized_ridge_and_unpenalized_intercept_match_sklearn():
    x,y,d,e,m=fixture();cutoff='2002-12-31';fit=fit_moments(date_moments(x,y,d,e,m),cutoff)
    valid=d<pd.Timestamp('2003-01-01');a=x[valid];b=y[valid]
    counts=pd.Series(d[valid]).value_counts();w=np.array([1/(2*counts[t]) for t in d[valid]])
    expected=Ridge(alpha=1.,fit_intercept=True,solver='svd').fit(a,b,sample_weight=w)
    np.testing.assert_allclose(fit['beta'],expected.coef_,atol=1e-12)
    np.testing.assert_allclose(fit['intercept'],expected.intercept_,atol=1e-12)
    for j in range(8):
        univariate=Ridge(alpha=1.,solver='svd').fit(a[:,[j]],b,sample_weight=w)
        np.testing.assert_allclose(fit['uni_beta'][j],univariate.coef_[0],atol=1e-12)
    assert fit['training_rows']==32 and fit['training_dates']==2


def test_future_perturbation_does_not_change_fit_or_predictions():
    x,y,d,e,m=fixture();f=fit_moments(date_moments(x,y,d,e,m),'2002-12-31')
    xx=x.copy();yy=y.copy();future=d.year==2003;xx[future]=1e6;yy[future]=-1e12
    ff=fit_moments(date_moments(xx,yy,d,e,m),'2002-12-31')
    np.testing.assert_array_equal(f['beta'],ff['beta'])
    np.testing.assert_array_equal(predict(x[:3],f)[0],predict(x[:3],ff)[0])


def test_exit_and_ledger_maturity_both_required():
    x,y,d,e,m=fixture();m=np.array(m,dtype='datetime64[ns]');m[:20]=np.datetime64('2003-01-06')
    mm=date_moments(x,y,d,e,m)
    try:fit_moments(mm,'2002-12-31')
    except ValueError:pass
    else:raise AssertionError('Only one mature date: fitting must fail')


def test_no_imputation_predictions_preserve_keys_and_ignore_outcomes():
    x,y,d,e,m=fixture();f=fit_moments(date_moments(x,y,d,e,m),'2002-12-31')
    x[0,2]=np.nan;sc,v=predict(x,f)
    assert len(sc)==72 and np.isnan(sc[0]).all() and not v[0]
    assert np.isfinite(sc[1:]).all()
    assert sc.shape==(72,18)


def test_replication_does_not_change_normalized_penalty():
    x,y,d,e,m=fixture();fit=fit_moments(date_moments(x,y,d,e,m),'2002-12-31')
    twice=[np.concatenate([a,a]) for a in (x,y,d,e,m)]
    ff=fit_moments(date_moments(*twice),'2002-12-31')
    np.testing.assert_allclose(fit['beta'],ff['beta'],atol=1e-12)


def test_intercept_shift_does_not_change_penalized_slopes():
    x,y,d,e,m=fixture();a=fit_moments(date_moments(x,y,d,e,m),'2002-12-31')
    b=fit_moments(date_moments(x,y+2,d,e,m),'2002-12-31')
    np.testing.assert_allclose(a['beta'],b['beta'],atol=1e-12)
    np.testing.assert_allclose(b['intercept']-a['intercept'],2.,atol=1e-12)


def test_partial_date_maturity_reweights_available_rows_only():
    x,y,d,e,m=fixture();m=np.array(m,dtype='datetime64[ns]');m[:10]=np.datetime64('2003-01-06')
    fit=fit_moments(date_moments(x,y,d,e,m),'2002-12-31')
    assert fit['training_rows']==22 and fit['training_dates']==2
