from copy import deepcopy
from math import log1p, prod, sqrt
from statistics import mean, stdev
import pytest
from src.features.baseline import compute_features
from src.features.returns import admitted_return
from src.features.preprocessing import preprocess
from src.features.qa import synthetic_fixture


@pytest.fixture
def fixture():
    cal,rows=synthetic_fixture()
    return cal,rows,75


def test_momentum_exact_positions_and_excluded_latest_five(fixture):
    cal,rows,t=fixture
    original=compute_features(cal,rows,cal[t])['momentum_60_skip5']
    assert original.positions == tuple(cal[t-59:t-4])
    assert original.n_valid == 55
    assert original.raw == pytest.approx(prod(1+rows[d]['dlyret'] for d in cal[t-59:t-4])-1)
    modified=deepcopy(rows)
    for d in cal[t-4:t+1]:
        modified[d].update(dlyret=100,dlyprc=9999,event_verified=False)
    assert compute_features(cal,modified,cal[t])['momentum_60_skip5'] == original


def test_reversal_compounding_and_volatility_sample_sd(fixture):
    cal,rows,t=fixture
    f=compute_features(cal,rows,cal[t])
    rs=[rows[d]['dlyret'] for d in cal[t-4:t+1]]
    assert f['reversal_5'].positions == tuple(cal[t-4:t+1])
    assert f['reversal_5'].raw == pytest.approx(-(prod(1+r for r in rs)-1))
    assert abs(f['reversal_5'].raw + sum(rs)) > 1e-8
    v=[rows[d]['dlyret'] for d in cal[t-19:t+1]]
    assert f['volatility_20'].raw == pytest.approx(stdev(v))
    assert f['volatility_20'].n_valid == 20
    assert f['volatility_20'].raw != pytest.approx(sqrt(mean((x-mean(v))**2 for x in v)))


@pytest.mark.parametrize('name,start,stop',[
 ('reversal_5',-4,0),('momentum_60_skip5',-59,-5),('volatility_20',-19,0),
 ('turnover_20',-19,0),('dollar_liquidity_20',-19,0),('volume_shock_20',-20,0)])
def test_missing_rows_preserve_calendar_positions(fixture,name,start,stop):
    cal,rows,t=fixture
    baseline=compute_features(cal,rows,cal[t])[name]
    del rows[cal[t+start+2]]
    observed=compute_features(cal,rows,cal[t])[name]
    assert observed.positions == baseline.positions == tuple(cal[t+start:t+stop+1])
    if name in ('reversal_5','momentum_60_skip5','volatility_20'):
        assert observed.missing and observed.reason == 'insufficient_valid_observations'
    else:
        assert observed.n_valid < baseline.n_valid


def test_units_and_liquidity_minimum_and_zero_volume(fixture):
    cal,rows,t=fixture
    for d in cal[t-20:t+1]:
        rows[d].update(dlyprc=100,dlyvol=1000,dlycap=1000)
    f=compute_features(cal,rows,cal[t])
    assert f['turnover_20'].raw == pytest.approx(log1p(100_000/1_000_000))
    assert f['dollar_liquidity_20'].raw == pytest.approx(log1p(100_000))
    for d in cal[t-19:t-14]:
        rows[d]['dlyvol']=None
    f=compute_features(cal,rows,cal[t])
    assert f['turnover_20'].n_valid == f['dollar_liquidity_20'].n_valid == 15
    assert not f['turnover_20'].missing
    rows[cal[t-14]]['dlyvol']=None
    f=compute_features(cal,rows,cal[t])
    assert f['turnover_20'].missing and f['dollar_liquidity_20'].missing
    for d in cal[t-20:t+1]:
        rows[d]['dlyvol']=0
    assert compute_features(cal,rows,cal[t])['turnover_20'].raw == 0
    rows[cal[t]]['dlycap']=0
    assert compute_features(cal,rows,cal[t])['turnover_20'].n_valid == 19


def test_volume_shock_denominator_excludes_current_and_minimum(fixture):
    cal,rows,t=fixture
    for d in cal[t-20:t+1]:
        rows[d].update(dlyprc=100,dlyvol=1000)
    rows[cal[t]]['dlyvol']=2000
    f=compute_features(cal,rows,cal[t])['volume_shock_20']
    assert f.raw == pytest.approx(log1p(200_000)-log1p(100_000))
    assert f.n_valid == 20
    for d in cal[t-20:t-15]:
        rows[d]['dlyvol']=None
    assert not compute_features(cal,rows,cal[t])['volume_shock_20'].missing
    rows[cal[t-15]]['dlyvol']=None
    assert compute_features(cal,rows,cal[t])['volume_shock_20'].missing


def test_gap_exact_observed_prior_close_and_clean_identity(fixture):
    cal,rows,t=fixture
    f=compute_features(cal,rows,cal[t])
    assert f['gap_1'].raw == pytest.approx(rows[cal[t]]['dlyopen']/rows[cal[t-1]]['dlyprc']-1)
    assert (1+f['gap_1'].raw)*(1+f['intraday_1'].raw) == pytest.approx(rows[cal[t]]['dlyprc']/rows[cal[t-1]]['dlyprc'])
    del rows[cal[t-1]]
    assert compute_features(cal,rows,cal[t])['gap_1'].missing


@pytest.mark.parametrize('update',[{'dlyfacprc':2},{'dlyorddivamt':1},{'dlynonorddivamt':1},
    {'dlyopen':0},{'dlyprc':-1},{'dlyprcflg':'BA'},{'event_verified':False}])
def test_gap_rejects_events_or_invalid_prices(fixture,update):
    cal,rows,t=fixture
    rows[cal[t]].update(update)
    assert compute_features(cal,rows,cal[t])['gap_1'].missing
    if 'dlyopen' in update or 'dlyprc' in update or 'dlyprcflg' in update:
        assert compute_features(cal,rows,cal[t])['intraday_1'].missing


def test_return_admission_and_split_safety(fixture):
    cal,rows,t=fixture
    r=rows[cal[t]]; prev=rows[cal[t-1]]
    r.update(dlyprc=prev['dlyprc']/2,dlyfacprc=2,dlyret=0,event_type='pure_split')
    assert admitted_return(r,prev,cal[t],cal[t-1])[0] == 0
    r['dlyvol']=2000; prev['dlyvol']=1000
    assert r['dlyprc']*r['dlyvol'] == prev['dlyprc']*prev['dlyvol']
    for field,value,reason in [('dlyretdurflg','P2','multiperiod_or_unknown_return'),
        ('dlydelflg','Y','delisting_or_unknown_storage_flag'),
        ('event_known_date',cal[t+1],'event_not_verified_by_close')]:
        updated={**r,field:value}
        assert admitted_return(updated,prev,cal[t],cal[t-1])[1] == reason
    assert admitted_return({**r,'source_prev_date':cal[t-2]},prev,cal[t],cal[t-1])[0] is None


def test_future_and_target_fields_do_not_affect_features(fixture):
    cal,rows,t=fixture
    expected=compute_features(cal,rows,cal[t])
    for d,row in rows.items():
        row.update(label_status='missing',target_5d=999,future_eligible=False)
        if d > cal[t]:
            row.update(dlyprc=999999,dlyvol=999999,event_known_date=cal[0],event_verified=False)
    assert compute_features(cal,rows,cal[t]) == expected
    assert compute_features(cal[:t+1],rows,cal[t]) == expected
    assert compute_features(cal,rows,cal[10])['momentum_60_skip5'].reason == 'insufficient_calendar_history'


def records(date,values):
    return [dict(permno=i,signal_date=date,feature='test',raw=x,
        reason='missing_security_row' if x is None else 'observed',label_status='unresolved') for i,x in enumerate(values)]


def test_preprocessing_quantiles_population_sd_and_raw_preservation():
    raw=list(range(99))+[10000]
    data=records('day1',raw)+records('day2',[7]*30)+records('day3',[1]*29)
    output=preprocess(data)
    day1=[x for x in output if x['signal_date']=='day1']
    assert [r['raw'] for r in day1] == raw
    assert day1[0]['clip_lower'] == pytest.approx(.99)
    assert day1[0]['clip_upper'] == pytest.approx(197.02)
    clipped=[r['clipped'] for r in day1]
    mu=mean(clipped); sd=sqrt(mean((x-mu)**2 for x in clipped))
    assert day1[-1]['standardized'] == pytest.approx((197.02-mu)/sd)
    assert mean(r['standardized'] for r in day1) == pytest.approx(0,abs=1e-12)
    assert mean(r['standardized']**2 for r in day1) == pytest.approx(1)
    assert all(r['standardized']==0 and r['constant_cross_section'] for r in output if r['signal_date']=='day2')
    assert all(r['processed_missing'] and r['processed_reason']=='insufficient_cross_section' for r in output if r['signal_date']=='day3')
    assert preprocess(records('day1',raw)) == day1


def test_preprocessing_missingness_target_independence_and_no_fill():
    data=records('day1',list(range(30))+[None,float('inf')])
    output=preprocess(data)
    for row in output[-2:]:
        assert row['raw_missing'] and row['processed_missing'] and row['clipped'] is None
    assert output[-2]['raw_reason'] == 'missing_security_row'
    for row in data:
        row['label_status']='measurable';row['target_5d']=999
    again=preprocess(data)
    assert [(x['clipped'],x['standardized'],x['processed_reason']) for x in again] == [(x['clipped'],x['standardized'],x['processed_reason']) for x in output]
    assert len(again)==len(data)
    with pytest.raises(ValueError):
        preprocess(data+[data[0]])


def test_cash_admission_reconstruction_and_nonordinary_rejection(fixture):
    cal,rows,t=fixture
    prev=rows[cal[t-1]]
    cash=1.0
    row={**rows[cal[t]],'event_type':'ordinary_cash','dlyorddivamt':cash}
    row['dlyret']=(row['dlyprc']+cash)/prev['dlyprc']-1
    assert admitted_return(row,prev,cal[t],cal[t-1])[0] == row['dlyret']
    assert admitted_return({**row,'dlyret':0.9},prev,cal[t],cal[t-1])[1] == 'return_reconstruction_mismatch'
    assert admitted_return({**row,'event_type':'received_security'},prev,cal[t],cal[t-1])[0] is None
    assert admitted_return({**row,'dlynonorddivamt':1},prev,cal[t],cal[t-1])[0] is None


def test_nonfinite_preprocessing_has_explicit_invalid_reason():
    output=preprocess(records('day',list(range(30))+[float('inf')]))
    assert output[-1]['processed_reason'] == output[-1]['raw_reason'] == 'nonfinite_or_invalid_raw'
    assert output[-1]['processed_missing']
