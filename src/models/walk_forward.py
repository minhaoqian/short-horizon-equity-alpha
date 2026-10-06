"""Approved Stage 3A normalized, equal-date Ridge; no tuning or imputation."""
import numpy as np
import pandas as pd

LAMBDA=1.


def complete_mask(x):
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or x.shape[1]!=8:raise ValueError('Exactly eight frozen features required')
    return np.isfinite(x).all(axis=1)


def date_moments(x,y,dates,exit_dates,maturity_dates):
    """Date sufficient statistics; no future dates enter a fitted cutoff."""
    x=np.asarray(x,float);y=np.asarray(y,float)
    frame=pd.DataFrame({'date':pd.to_datetime(dates),'exit':pd.to_datetime(exit_dates),'maturity':pd.to_datetime(maturity_dates)})
    valid=complete_mask(x)&np.isfinite(y)&frame.maturity.notna().to_numpy()
    rows=[]
    for (date,exit_date,maturity_date),ids in frame[valid].groupby(['date','exit','maturity']).groups.items():
        ids=np.asarray(list(ids));a=x[ids];b=y[ids];row={'signal_date':date,'exit_date':frame.loc[ids,'exit'].max(),
            'maturity_date':frame.loc[ids,'maturity'].max(),'n':len(ids),'my':b.mean()}
        for j in range(8):
            row[f'm{j}']=a[:,j].mean();row[f'xy{j}']=(a[:,j]*b).mean()
            for k in range(j,8):row[f'xx{j}_{k}']=(a[:,j]*a[:,k]).mean()
        rows.append(row)
    return pd.DataFrame(rows)


def fit_moments(moments,cutoff):
    cutoff=pd.Timestamp(cutoff)
    m=moments[(pd.to_datetime(moments.signal_date)<=cutoff)&(pd.to_datetime(moments.exit_date)<=cutoff)&
              (pd.to_datetime(moments.maturity_date)<=cutoff)]
    columns=[col for col in m.columns if col.startswith(('m','xy','xx')) and col!='maturity_date']
    if not m.signal_date.is_unique:
        numeric=m[columns].multiply(m.n,axis=0)
        weighted=numeric.groupby(m.signal_date).sum()
        grouped=m.groupby('signal_date').agg(n=('n','sum'),exit_date=('exit_date','max'),maturity_date=('maturity_date','max'))
        m=grouped.join(weighted.div(grouped.n,axis=0)).reset_index()
    if len(m)<2:raise ValueError('Insufficient mature training history')
    mx=m[[f'm{j}' for j in range(8)]].mean().to_numpy(float);my=float(m.my.mean())
    exy=m[[f'xy{j}' for j in range(8)]].mean().to_numpy(float)
    exx=np.zeros((8,8))
    for j in range(8):
        for k in range(j,8):exx[j,k]=exx[k,j]=m[f'xx{j}_{k}'].mean()
    cov=exx-np.outer(mx,mx);rhs=exy-mx*my
    beta=np.linalg.solve(cov+LAMBDA*np.eye(8),rhs);intercept=my-mx@beta
    uni=rhs/(np.diag(cov)+LAMBDA);ub=my-mx*uni
    residual=np.max(np.abs((cov+np.eye(8))@beta-rhs))
    assert residual<1e-10 and np.isfinite(beta).all() and np.isfinite(intercept)
    return {'beta':beta,'intercept':intercept,'uni_beta':uni,'uni_intercept':ub,
        'training_rows':int(m.n.sum()),'training_dates':len(m),'weight_sum':1.,'lambda':LAMBDA,
        'max_training_signal':str(pd.Timestamp(m.signal_date.max()).date()),
        'max_training_exit':str(pd.Timestamp(m.exit_date.max()).date()),
        'max_training_maturity':str(pd.Timestamp(m.maturity_date.max()).date()),
        'normal_equation_residual':float(residual),'penalized_condition_number':float(np.linalg.cond(cov+np.eye(8))),
        'unpenalized_condition_number':float(np.linalg.cond(cov)),
        'thin_training_dates':int((m.n<30).sum())}


def predict(x,fit):
    """Only frozen inputs and already fitted coefficients; no target/status API."""
    x=np.asarray(x,float);valid=complete_mask(x)
    scores=np.full((len(x),18),np.nan)
    a=x[valid]
    scores[valid,0]=a@fit['beta']+fit['intercept']
    scores[valid,1]=a.mean(axis=1)
    scores[valid,2:10]=a*fit['uni_beta']+fit['uni_intercept']
    scores[valid,10:18]=a
    assert np.isfinite(scores[valid]).all() and np.isnan(scores[~valid]).all()
    return scores,valid
