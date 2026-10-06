import numpy as np
import pytest
from scipy.stats import spearmanr
import statsmodels.api as sm
from statsmodels.stats.sandwich_covariance import cov_hac_simple
from src.evaluation.statistics import rank_ic,quintiles,hac_mean,phase


def test_average_tie_ic_and_missing_constants():
    x=[1,1,2,3,3,4];y=[4,3,3,2,1,1]
    assert rank_ic(x,y,minimum=3)[0]==pytest.approx(spearmanr(x,y).statistic)
    assert rank_ic([1]*30,range(30))[1]=='constant_rank_vector'
    assert rank_ic([1,np.nan],[2,3])[1]=='insufficient_pairs'


def test_quintiles_keep_ties_together_without_outcome_tiebreaking():
    x=np.array([1]*5+[2]*5+[3]*5+[4]*5+[5]*5)
    assert np.array_equal(quintiles(x),np.repeat(np.arange(1,6),5))
    assert np.array_equal(quintiles(np.ones(30)),np.repeat(3,30))


@pytest.mark.parametrize('lag',[4,20])
def test_calendar_hac_matches_statsmodels_complete_series(lag):
    rng=np.random.default_rng(42);x=rng.normal(size=300)
    fitted=sm.OLS(x,np.ones((len(x),1))).fit()
    actual=hac_mean(x,np.arange(len(x)),lag)
    assert actual['se']**2==pytest.approx(cov_hac_simple(fitted,nlags=lag,use_correction=True)[0,0],rel=1e-12)


def test_hac_does_not_compress_calendar_gaps_or_invent_zero_ics():
    x=np.array([.1,-.2,.3,-.1]);positions=[0,2,4,7]
    a=hac_mean(x,positions,1);b=hac_mean(x,range(4),1)
    assert a['mean']==pytest.approx(x.mean()) and a['se']!=pytest.approx(b['se'])
    extended=hac_mean([.1,np.nan,-.2,np.nan,.3,np.nan,np.nan,-.1],range(8),1)
    assert a==extended


def test_fixed_phases_calendar_anchor_and_degenerate_inference():
    assert np.array_equal(phase([0,13,14,15,19]),[0,3,4,0,4])
    assert hac_mean([.1]*8,range(8),4)['inference_status']=='degenerate_variance'
    with pytest.raises(ValueError):hac_mean([1,2],[0,0],4)


def test_hac_constant_roundoff_cannot_create_significance():
    for n in (3,7,10,31):
        result=hac_mean(np.full(n,.1),np.arange(n),4)
        assert result['inference_status']=='degenerate_variance'
        assert result['t_stat'] is None and result['se'] is None
