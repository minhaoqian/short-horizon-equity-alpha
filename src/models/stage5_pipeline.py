"""Single prespecified holdout opening; sequential frozen quarterly fits only."""
import json
import hashlib
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from src.features.panel import ROOT,FEATURES
from src.models.walk_forward import complete_mask,fit_moments,date_moments
from src.models.stage5_data import CACHE,OUT,START,END,TARGET,FEATURE,frozen_sources,extend_training
from src.evaluation.baseline import sha
from src.evaluation.statistics import rank_ic,quintiles

CANDIDATES=('raw_reversal','univariate_reversal_ridge','ridge')


def make_schedule(calendar):
    calendar=calendar.copy();calendar['signal_date']=pd.to_datetime(calendar.signal_date)
    assert calendar.signal_date.is_unique and calendar.td.is_unique
    valid=calendar.signal_date.between(START,END);rows=[]
    for k,(period,g) in enumerate(calendar[valid].groupby(calendar.loc[valid,'signal_date'].dt.to_period('Q')),1):
        i=int(calendar.index[calendar.signal_date==g.signal_date.iloc[0]][0]);cut=calendar.iloc[i-1];mature=calendar.iloc[i-7]
        rows.append(dict(fold_number=k,quarter=str(period),fit_information_cutoff=cut.signal_date,
            latest_calendar_mature_signal_date=mature.signal_date,
            evaluation_first_signal_date=g.signal_date.iloc[0],evaluation_last_signal_date=g.signal_date.iloc[-1]))
    schedule=pd.DataFrame(rows)
    assert len(schedule)==24 and schedule.iloc[0].evaluation_first_signal_date==pd.Timestamp(START)
    assert schedule.iloc[-1].evaluation_last_signal_date==pd.Timestamp(END)
    return schedule


def forecast(x,fit):
    """Input-only API; target/status cannot decide score availability."""
    x=np.asarray(x,float);valid=complete_mask(x)
    out=np.full((len(x),3),np.nan);out[:,0]=x[:,0]
    out[valid,1]=x[valid,0]*fit['reversal_beta']+fit['reversal_intercept']
    out[valid,2]=x[valid]@np.asarray(fit['beta'])+fit['intercept']
    assert np.isfinite(out[valid]).all() and np.isnan(out[~valid,1:]).all()
    return out,valid


def select_fit(fit):
    f={k:v for k,v in fit.items() if k not in ('uni_beta','uni_intercept')}
    f['reversal_beta']=float(fit['uni_beta'][0]);f['reversal_intercept']=float(fit['uni_intercept'][0])
    f['beta']=np.asarray(f['beta']).tolist()
    return f


def evaluate(data,calendar):
    daily=[];quant=[];paired=[]
    for day,g in data.groupby('signal_date',sort=True):
        y=g.target_5d.to_numpy(float);common=np.isfinite(g.ridge.to_numpy(float))&np.isfinite(y)
        common_keys=g.loc[common,'permno'].to_numpy();same={}
        for model in CANDIDATES:
            for scope in ('primary_available','matched_complete8'):
                x=g[model].to_numpy(float).copy()
                if scope=='matched_complete8':x[~common]=np.nan
                ic,reason,n=rank_ic(x,y)
                if scope=='matched_complete8':
                    assert np.array_equal(g.loc[np.isfinite(x)&np.isfinite(y),'permno'].to_numpy(),common_keys)
                    same[model]=ic
                daily.append(dict(signal_date=day,model=model,sample=scope,ic=ic,ic_reason=reason,
                    n_pairs=n,eligible=len(g),numeric_labels=int(np.isfinite(y).sum()),
                    predictions=int(np.isfinite(g[model]).sum())))
                if reason=='observed':
                    v=np.isfinite(x)&np.isfinite(y);b=quintiles(x[v]);yy=y[v]
                    for q in range(1,6):
                        vals=yy[b==q];quant.append(dict(signal_date=day,model=model,sample=scope,
                            quintile=q,n_pairs=len(vals),mean_target=float(vals.mean()) if len(vals) else np.nan))
        for benchmark in CANDIDATES[:2]:
            paired.append(dict(signal_date=day,benchmark=benchmark,ic=same['ridge']-same[benchmark],
                n_common_keys=len(common_keys),identical_security_keys=True))
    cal=calendar[['signal_date','td']].copy();cal.signal_date=pd.to_datetime(cal.signal_date)
    d=pd.DataFrame(daily).merge(cal,on='signal_date',validate='many_to_one')
    q=pd.DataFrame(quant,columns=['signal_date','model','sample','quintile','n_pairs','mean_target']);p=pd.DataFrame(paired).merge(cal,on='signal_date',validate='many_to_one')
    assert d.td.notna().all() and p.td.notna().all()
    for (m,s),a in d.groupby(['model','sample']):
        b=q[(q.model==m)&(q['sample']==s)]
        assert int(b.n_pairs.sum())==int(a.loc[a.ic.notna(),'n_pairs'].sum())
    return d,q,p


def join_evaluation(prediction,labels):
    """Outcome join is key-based; outer joins may reorder rows in pandas."""
    assert len(labels)==len(prediction) and not labels.duplicated(['permno','signal_date']).any()
    assert not prediction.duplicated(['permno','signal_date']).any()
    joined=prediction.merge(labels,on=['permno','signal_date'],validate='one_to_one',how='outer',indicator=True)
    assert joined._merge.eq('both').all()
    return joined.drop(columns='_merge').sort_values(['signal_date','permno']).reset_index(drop=True)


def bounded_training_qa(c):
    # Entirely development-period fixture, no holdout outcomes or statistics.
    z=','.join('f.'+f+'_z' for f in FEATURES)
    complete=' AND '.join(f'isfinite(f.{f}_z)' for f in FEATURES)
    d=c.execute(f"""SELECT f.signal_date,l.exit_date,l.target_5d,{z} FROM f JOIN
        read_parquet('{TARGET}') l USING(permno,signal_date)
        WHERE f.signal_date BETWEEN DATE '2019-06-03' AND DATE '2019-06-14'
        AND l.exit_date<=DATE '2019-06-28' AND isfinite(l.target_5d) AND {complete}
        ORDER BY signal_date,permno""").fetchdf()
    x=d[[f+'_z' for f in FEATURES]].to_numpy(float);y=d.target_5d.to_numpy(float)
    fit=fit_moments(date_moments(x,y,d.signal_date,d.exit_date,d.exit_date),'2019-06-28')
    count=d.signal_date.value_counts();w=np.array([1/(len(count)*count[t]) for t in d.signal_date])
    comb=Ridge(alpha=1,fit_intercept=True,solver='svd').fit(x,y,sample_weight=w)
    uni=Ridge(alpha=1,fit_intercept=True,solver='svd').fit(x[:,[0]],y,sample_weight=w)
    np.testing.assert_allclose(fit['beta'],comb.coef_,atol=1e-12)
    np.testing.assert_allclose(fit['intercept'],comb.intercept_,atol=1e-12)
    np.testing.assert_allclose(fit['uni_beta'][0],uni.coef_[0],atol=1e-12)
    np.testing.assert_allclose(fit['uni_intercept'][0],uni.intercept_,atol=1e-12)
    return dict(development_fixture_rows=len(d),dates=len(count),independent_ridge_agreement=True,
                no_holdout_outcomes_in_fixture=True,qa_passed=True)


def atomic(frame,path):
    temporary=path.with_suffix('.tmp.parquet');frame.to_parquet(temporary,index=False);temporary.replace(path)


def run():
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    source=frozen_sources()
    code=[Path(__file__),Path(__file__).with_name('stage5_data.py'),Path(__file__).with_name('walk_forward.py'),
          ROOT/'src/evaluation/statistics.py']
    token=hashlib.sha256(json.dumps(dict(inputs=source['input_fingerprints'],code={str(p):sha(p) for p in code}),sort_keys=True).encode()).hexdigest()
    path=CACHE/'manifest.json'
    manifest=json.loads(path.read_text()) if path.exists() else dict(fingerprint=token,folds={},
        status='HOLDOUT_OPENING_AUTHORIZED',one_prespecified_evaluation=True)
    assert manifest['fingerprint']==token,'Changed holdout algorithm/source: stop for integrity review, do not create another holdout run'
    if manifest.get('complete'):return manifest  # No automatic second evaluation.
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    c=duckdb.connect();c.execute("SET threads=2; SET memory_limit='2GB'")
    temp=CACHE/'temp';temp.mkdir(exist_ok=True);c.execute(f"SET temp_directory='{temp}'")
    c.execute(f"""CREATE TABLE f AS SELECT permno,signal_date,max_input_date,
        {','.join(f+'_z,'+f+'_processed_reason' for f in FEATURES)} FROM read_parquet('{FEATURE}')
        WHERE signal_date BETWEEN DATE '1993-01-04' AND DATE '{END}'""")
    assert c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM f').fetchone()==(6699101,6699101)
    assert c.execute('SELECT count(*) FROM f WHERE max_input_date>signal_date').fetchone()[0]==0
    c.execute(f"""CREATE TABLE calendar AS SELECT dlycaldt signal_date,row_number() OVER(ORDER BY dlycaldt)-1 td
        FROM (SELECT DISTINCT dlycaldt FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_parts/part_00.parquet'}')
        WHERE dlycaldt BETWEEN DATE '1993-01-04' AND DATE '{END}')""")
    calendar=c.execute('SELECT * FROM calendar ORDER BY td').fetchdf();schedule=make_schedule(calendar)
    mismatch=c.execute(f"""SELECT count(*) FROM (SELECT DISTINCT signal_date,signal_td FROM
        read_parquet('{ROOT/'data/interim/target_boundary_audit_parts/part_*.parquet'}')
        WHERE signal_date BETWEEN DATE '{START}' AND DATE '{END}') a JOIN calendar b USING(signal_date)
        WHERE a.signal_td<>b.td+1""").fetchone()[0]
    assert mismatch==0,'Absolute calendar/phase anchor changed'
    schedule.to_csv(OUT/'walk_forward_schedule.csv',index=False)
    bounded=bounded_training_qa(c)
    pd.DataFrame([bounded]).to_csv(OUT/'bounded_training_qa.csv',index=False)
    expected=c.execute(f"SELECT count(*) FROM f WHERE signal_date BETWEEN DATE '{START}' AND DATE '{END}'").fetchone()[0]
    assert expected==6699101-4816452
    moments=pd.read_parquet(ROOT/'data/interim/stage3a/training_moments.parquet')
    preds=CACHE/'predictions';preds.mkdir(exist_ok=True);batches=CACHE/'evaluation_batches';batches.mkdir(exist_ok=True)
    for block in schedule.to_dict('records'):
        k=int(block['fold_number']);first=block['evaluation_first_signal_date'];last=block['evaluation_last_signal_date'];cut=block['fit_information_cutoff']
        files=dict(predictions=preds/f'fold_{k:02d}.parquet',evaluation=batches/f'fold_{k:02d}.parquet',
                   daily=batches/f'daily_{k:02d}.parquet',quantiles=batches/f'quantiles_{k:02d}.parquet',paired=batches/f'paired_{k:02d}.parquet',
                   moments=CACHE/f'moments_{k:02d}.parquet')
        saved=manifest['folds'].get(str(k))
        if saved:
            for name,p in files.items():assert sha(p)==saved['hashes'][name],'Corrupted saved holdout batch'
            moments=pd.read_parquet(files['moments']);print(f'Quarter {k}/24 checksum-verified resume',flush=True);continue
        new,maturity=extend_training(c,cut,moments.signal_date.max())
        moments=pd.concat([moments,new],ignore_index=True);assert moments.signal_date.is_unique
        fit=select_fit(fit_moments(moments,cut))
        assert pd.Timestamp(fit['max_training_signal'])<=block['latest_calendar_mature_signal_date']
        assert pd.Timestamp(fit['max_training_exit'])<=cut and pd.Timestamp(fit['max_training_maturity'])<=cut
        # Predictor read contains no future label, label status, target components,
        # forecast horizon outcome or Stage4 execution/accounting field.
        data=c.execute(f"SELECT * FROM f WHERE signal_date BETWEEN DATE '{first.date()}' AND DATE '{last.date()}' ORDER BY signal_date,permno").fetchdf()
        assert not data.duplicated(['permno','signal_date']).any()
        x=data[[f+'_z' for f in FEATURES]].to_numpy(float);scores,valid=forecast(x,fit)
        prediction=data[['permno','signal_date']+[f+'_processed_reason' for f in FEATURES]].copy()
        prediction['fold_number']=k;prediction['complete_features']=valid
        prediction['missing_feature_mask']=np.sum((~np.isfinite(x))*(1<<np.arange(8)),axis=1)
        for j,model in enumerate(CANDIDATES):prediction[model]=scores[:,j]
        if files['predictions'].exists():
            pd.testing.assert_frame_equal(pd.read_parquet(files['predictions']),prediction)
        else:atomic(prediction,files['predictions'])
        prediction_hash=sha(files['predictions'])
        # Only AFTER durable prediction checkpoint is the quarter's future target
        # joined. The prediction file itself never receives outcome metadata.
        labels=c.execute(f"SELECT * FROM read_parquet('{TARGET}') WHERE signal_date BETWEEN DATE '{first.date()}' AND DATE '{last.date()}' ORDER BY signal_date,permno").fetchdf()
        evaluation=join_evaluation(prediction,labels)
        numeric=np.isfinite(evaluation.target_5d)
        assert np.array_equal(numeric,evaluation.label_status.isin(['measurable_ordinary_event_adjusted','measurable_cash_only_delisting']))
        assert sha(files['predictions'])==prediction_hash
        # Independent bounded stored-score check in every quarter, after join,
        # proving outcome metadata cannot alter already saved forecasts.
        np.testing.assert_allclose(evaluation[list(CANDIDATES)].to_numpy(),scores,atol=0,equal_nan=True)
        daily,quant,paired=evaluate(evaluation,calendar)
        for name,frame in [('evaluation',evaluation),('daily',daily),('quantiles',quant),('paired',paired),('moments',moments)]:atomic(frame,files[name])
        fit.update(fold_number=k,quarter=block['quarter'],fit_cutoff=str(cut.date()))
        manifest['folds'][str(k)]=dict(fit=fit,maturity_qa=maturity,rows=len(prediction),
            predictions_saved_before_label_join=True,hashes={name:sha(p) for name,p in files.items()})
        path.write_text(json.dumps(manifest,indent=2)+'\n')
        print(f'Quarter {k}/24 {block["quarter"]}: {len(prediction):,} keys; {valid.sum():,} complete-input forecasts; {fit["training_rows"]:,} past mature training rows',flush=True)
    c.execute(f"CREATE VIEW predictions AS SELECT * FROM read_parquet('{preds/'fold_*.parquet'}')")
    rows,keys=c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM predictions').fetchone()
    assert rows==keys==expected
    assert c.execute(f"SELECT count(*) FROM (SELECT permno,signal_date FROM f WHERE signal_date BETWEEN DATE '{START}' AND DATE '{END}' EXCEPT SELECT permno,signal_date FROM predictions)").fetchone()[0]==0
    c.close()
    for name,sha256 in source['protected_hashes'].items():assert sha(ROOT/name)==sha256,'Frozen development artifact changed: '+name
    manifest.update(complete=True,status='PREDICTIONS_AND_EVALUATION_COMPLETE',source=source,bounded_qa=bounded,
        eligible_keys=rows,unique_keys=keys,quarterly_refits=24,reported_ridge_candidates=2,
        prediction_outcome_metadata_used=False,hyperparameter_selection=False,feature_selection=False,
        stage4_reopened=False,portfolio_results_computed=False,raw_scanned=False,wrds_queries=0,qa_passed=True)
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
