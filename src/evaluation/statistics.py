"""Prespecified tied-rank, quantile and calendar HAC diagnostics, no fitting."""
import numpy as np
from scipy.stats import rankdata


def rank_ic(x,y,minimum=30):
    x=np.asarray(x,float);y=np.asarray(y,float)
    keep=np.isfinite(x)&np.isfinite(y);x=x[keep];y=y[keep]
    if len(x)<minimum:return np.nan,'insufficient_pairs',len(x)
    rx=rankdata(x,method='average');ry=rankdata(y,method='average')
    if np.ptp(rx)==0 or np.ptp(ry)==0:return np.nan,'constant_rank_vector',len(x)
    return float(np.corrcoef(rx,ry)[0,1]),'observed',len(x)


def quintiles(x):
    x=np.asarray(x,float)
    if not np.all(np.isfinite(x)):raise ValueError('Quintile input must be finite')
    if len(x)==0:return np.array([],dtype=int)
    return np.minimum(5,1+np.floor(5*(rankdata(x,method='average')-.5)/len(x)).astype(int))


def phase(td):
    """Absolute development market index: first authorized date has index zero."""
    return np.asarray(td,dtype=int)%5


def hac_mean(values,positions,lag):
    """Original-calendar Bartlett score covariance, with explicit missing dates.

    Finite-sample correction M/(M-1); missing dates contribute no score terms,
    never become observed zero ICs. No significance-driven lag selection.
    """
    v=np.asarray(values,float);p=np.asarray(positions,int)
    if len(v)!=len(p) or len(set(p))!=len(p):raise ValueError('Unique aligned calendar positions required')
    if lag<0:raise ValueError('Nonnegative fixed lag required')
    keep=np.isfinite(v);v=v[keep];p=p[keep];m=len(v)
    result={'n_dates':m,'mean':float(np.mean(v)) if m else None,'lag':lag,
            'se':None,'t_stat':None,'ci_lower':None,'ci_upper':None,'inference_status':'insufficient_dates'}
    if m<2:return result
    if np.ptp(v)==0:
        result['inference_status']='degenerate_variance';return result
    residual={int(t):float(x-result['mean']) for t,x in zip(p,v)}
    meat=sum(u*u for u in residual.values())
    for h in range(1,lag+1):
        meat+=2*(1-h/(lag+1))*sum(u*residual.get(t-h,0.) for t,u in residual.items())
    variance=meat/(m*m)*m/(m-1)
    if not np.isfinite(variance) or variance<=0:
        result['inference_status']='degenerate_variance';return result
    se=float(np.sqrt(variance));critical=1.959963984540054
    result.update(se=se,t_stat=result['mean']/se,ci_lower=result['mean']-critical*se,
        ci_upper=result['mean']+critical*se,inference_status='observed')
    return result
