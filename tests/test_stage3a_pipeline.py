import datetime
import numpy as np
import pandas as pd
from src.models.stage3a_pipeline import evaluate_fold,MODELS


def test_matched_samples_missing_targets_and_calendar_date_types():
    n=45;r=np.random.default_rng(7)
    data=pd.DataFrame({'signal_date':pd.Timestamp('2003-01-02'),'target_5d':r.normal(size=n)})
    scores=r.normal(size=(n,len(MODELS)));scores[0,:]=np.nan;data.loc[1,'target_5d']=np.nan
    cal=pd.DataFrame({'signal_date':[datetime.date(2003,1,2)],'td':[2510]})
    daily,q=evaluate_fold(data,scores,cal)
    assert daily.n_pairs.eq(43).all() and daily.td.eq(2510).all()
    assert q.groupby('model').n_pairs.sum().eq(43).all()
    assert np.isfinite(scores[1]).all() # Prediction survives missing future label.


def test_constant_predictions_have_explicit_undefined_ic():
    data=pd.DataFrame({'signal_date':pd.Timestamp('2003-01-02'),'target_5d':np.arange(40.)})
    scores=np.zeros((40,len(MODELS)))
    cal=pd.DataFrame({'signal_date':[datetime.date(2003,1,2)],'td':[2510]})
    d,q=evaluate_fold(data,scores,cal)
    assert d.ic.isna().all() and d.ic_reason.eq('constant_rank_vector').all()
    assert q.empty
