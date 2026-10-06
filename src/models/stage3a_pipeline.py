"""Approved 68-quarter development Ridge pipeline, hard holdout exclusion."""
import json
import hashlib
import os
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb
from scipy.stats import rankdata
from sklearn.linear_model import Ridge
from src.features.panel import ROOT,FEATURES
from src.evaluation.baseline import summarize,sha
from src.evaluation.statistics import rank_ic,quintiles
from src.models.walk_forward import date_moments,fit_moments,predict
from src.models.stage3a_data import CACHE,OUT,prepare

MODELS=('ridge','equal_weight')+tuple('uni_'+f for f in FEATURES)+tuple('raw_'+f for f in FEATURES)


def verify_sources():
    p=CACHE/'source_manifest.json'
    if not p.exists():prepare()
    m=json.loads(p.read_text());assert m['qa_passed'] and m['maturity_violation_count']==0
    for v in m['input_fingerprints']:
        st=(ROOT/v['path']).stat();assert (st.st_size,st.st_mtime_ns)==(v['size'],v['mtime_ns']),'Changed licensed source'
    for v in m['outputs']:assert sha(ROOT/v['path'])==v['sha256'],'Corrupt prepared source'
    return m


def bounded_qa(c,moments):
    data=c.execute("""SELECT * FROM source WHERE signal_date BETWEEN DATE '1998-01-05' AND DATE '1998-01-16'
        AND complete_features AND numeric_label AND maturity_date<=DATE '1998-01-30' ORDER BY signal_date,permno""").fetchdf()
    x=data[[f+'_z' for f in FEATURES]].to_numpy(float);y=data.target_5d.to_numpy(float)
    mm=date_moments(x,y,data.signal_date,data.exit_date,data.maturity_date);fit=fit_moments(mm,'1998-01-30')
    count=data.signal_date.value_counts();w=np.array([1/(len(count)*count[t]) for t in data.signal_date])
    reference=Ridge(alpha=1.,fit_intercept=True,solver='svd').fit(x,y,sample_weight=w)
    error=float(np.max(np.abs(fit['beta']-reference.coef_)))
    assert error<1e-12 and abs(fit['intercept']-reference.intercept_)<1e-12
    # Check SQL moments against directly recomputed historical input moments.
    sql=moments[moments.signal_date.between(pd.Timestamp('1998-01-05'),pd.Timestamp('1998-01-16'))]
    sf=fit_moments(sql,'1998-01-30');np.testing.assert_allclose(sf['beta'],fit['beta'],atol=1e-12)
    first=fit_moments(moments,'2002-12-31')
    assert first['max_training_signal']<='2002-12-20' and first['max_training_exit']<='2002-12-31'
    future=moments.copy();future.loc[future.signal_date>=pd.Timestamp('2003-01-02'),'my']=1e9
    np.testing.assert_array_equal(first['beta'],fit_moments(future,'2002-12-31')['beta'])
    out={'bounded_rows':len(data),'bounded_dates':len(count),'independent_ridge_max_coefficient_error':error,
        'sql_moment_agreement':True,'future_label_perturbation_invariance':True,
        'first_training_rows':first['training_rows'],'first_training_dates':first['training_dates'],
        'first_training_max_signal':first['max_training_signal'],'first_training_max_exit':first['max_training_exit'],'qa_passed':True}
    pd.DataFrame([{'check':k,'value':json.dumps(v)} for k,v in out.items()]).to_csv(OUT/'bounded_historical_qa.csv',index=False)
    return out


def evaluate_fold(data,scores,calendar):
    daily=[];quant=[]
    date_groups=data.groupby('signal_date',sort=True).indices
    for date,ids in date_groups.items():
        ids=np.asarray(ids);y=data.target_5d.iloc[ids].to_numpy(float)
        eligible=len(ids);numeric=int(np.isfinite(y).sum())
        for j,model in enumerate(MODELS):
            sc=scores[ids,j];ic,reason,n=rank_ic(sc,y)
            daily.append({'signal_date':date,'model':model,'ic':ic,'ic_reason':reason,'n_pairs':n,
                          'eligible':eligible,'numeric_labels':numeric})
            if reason=='observed':
                v=np.isfinite(sc)&np.isfinite(y);buckets=quintiles(sc[v]);yy=y[v]
                for q in range(1,6):
                    ys=yy[buckets==q]
                    quant.append({'signal_date':date,'model':model,'quintile':q,'n_pairs':len(ys),
                        'mean_target':float(ys.mean()) if len(ys) else np.nan})
    calendar=calendar.copy();calendar['signal_date']=pd.to_datetime(calendar.signal_date)
    d=pd.DataFrame(daily).merge(calendar,on='signal_date',how='left');q=pd.DataFrame(quant,columns=['signal_date','model','quintile','n_pairs','mean_target'])
    assert d.td.notna().all()
    assert d.groupby('model').n_pairs.sum().nunique()==1
    for model in MODELS:
        a=d[d.model==model];b=q[q.model==model]
        assert int(b.n_pairs.sum())==int(a.loc[a.ic.notna(),'n_pairs'].sum())
    return d,q


def run():
    source_manifest=verify_sources();OUT.mkdir(parents=True,exist_ok=True)
    schedule=pd.read_csv(OUT/'walk_forward_schedule_proposed.csv',parse_dates=['fit_information_cutoff',
        'latest_calendar_mature_signal_date','evaluation_first_signal_date','evaluation_last_signal_date'])
    assert len(schedule)==68 and schedule.evaluation_first_signal_date.iloc[0]==pd.Timestamp('2003-01-02')
    assert schedule.evaluation_last_signal_date.iloc[-1]==pd.Timestamp('2019-12-31')
    c=duckdb.connect();c.execute("SET threads=2; SET memory_limit='2GB'")
    c.execute(f"SET temp_directory='{CACHE/'temp'}'")
    c.execute(f"CREATE VIEW source AS SELECT * FROM read_parquet('{CACHE/'development.parquet'}')")
    moments=pd.read_parquet(CACHE/'training_moments.parquet')
    calendar=pd.read_parquet(CACHE/'calendar.parquet');calendar['signal_date']=pd.to_datetime(calendar.signal_date)
    bounded=bounded_qa(c,moments);print('Bounded historical QA passed',json.dumps(bounded),flush=True)
    fingerprint=hashlib.sha256(json.dumps({'source':source_manifest,'code':sha(__file__),
        'ridge_code':sha(Path(__file__).with_name('walk_forward.py')),
        'evaluation_code':sha(ROOT/'src/evaluation/statistics.py'),
        'schedule':sha(OUT/'walk_forward_schedule_proposed.csv')},sort_keys=True).encode()).hexdigest()
    mp=CACHE/'manifest.json';manifest=json.loads(mp.read_text()) if mp.exists() else {'fingerprint':fingerprint,'folds':{}}
    assert manifest['fingerprint']==fingerprint,'Source/code fingerprint changed: archive incompatible cache explicitly'
    parts=CACHE/'predictions';parts.mkdir(exist_ok=True)
    agg=CACHE/'aggregate_batches';agg.mkdir(exist_ok=True)
    if not (CACHE/'evaluation_parts').exists():
        c.register('schedule',schedule)
        c.execute(f"""COPY (SELECT s.*,q.fold_number FROM source s JOIN schedule q ON
            s.signal_date BETWEEN q.evaluation_first_signal_date AND q.evaluation_last_signal_date)
            TO '{CACHE/'evaluation_parts'}' (FORMAT PARQUET,PARTITION_BY(fold_number))""")
    expected=c.execute("SELECT count(*) FROM source WHERE signal_date>=DATE '2003-01-02'").fetchone()[0]
    fits=[];all_daily=[];all_quant=[]
    for block in schedule.to_dict('records'):
        k=int(block['fold_number']);paths={'predictions':parts/f'fold_{k:02d}.parquet',
            'daily':agg/f'daily_{k:02d}.parquet','quantiles':agg/f'quantile_{k:02d}.parquet'}
        saved=manifest['folds'].get(str(k))
        if saved:
            for name,p in paths.items():assert sha(p)==saved['hashes'][name],'Corrupt forward cache'
            fits.append(saved['fit']);all_daily.append(pd.read_parquet(paths['daily']));all_quant.append(pd.read_parquet(paths['quantiles']))
            print(f'Quarter {k}/68: verified cached outputs',flush=True);continue
        fit=fit_moments(moments,block['fit_information_cutoff'])
        assert pd.Timestamp(fit['max_training_signal'])<=block['latest_calendar_mature_signal_date']
        assert pd.Timestamp(fit['max_training_exit'])<=block['fit_information_cutoff']
        assert pd.Timestamp(fit['max_training_maturity'])<=block['fit_information_cutoff']
        data=c.execute(f"SELECT * FROM read_parquet('{CACHE/'evaluation_parts'/('fold_number='+str(k))/'*.parquet'}') ORDER BY signal_date,permno").fetchdf()
        assert data.signal_date.between(block['evaluation_first_signal_date'],block['evaluation_last_signal_date']).all()
        x=data[[f+'_z' for f in FEATURES]].to_numpy(float);scores,valid=predict(x,fit)
        assert np.array_equal(valid,data.complete_features.to_numpy(bool))
        # Prediction function never receives target/status. Keep all original keys.
        prediction=data[['permno','signal_date','entry_date','exit_date','target_5d','label_status','label_reason']+
                        [f+'_processed_reason' for f in FEATURES]].copy()
        prediction['prediction_status']=np.where(valid,'observed','missing_required_feature')
        prediction['missing_feature_mask']=np.sum((~np.isfinite(x))*(1<<np.arange(8)),axis=1)
        prediction['fold_number']=k
        for j,model in enumerate(MODELS):prediction[model]=scores[:,j]
        d,q=evaluate_fold(data,scores,calendar)
        for name,frame in [('predictions',prediction),('daily',d),('quantiles',q)]:
            tmp=paths[name].with_suffix('.tmp.parquet');frame.to_parquet(tmp,index=False);tmp.replace(paths[name])
        stored={key:(v.tolist() if isinstance(v,np.ndarray) else v) for key,v in fit.items()}
        stored.update(fold_number=k,fit_cutoff=str(block['fit_information_cutoff'].date()))
        manifest['folds'][str(k)]={'fit':stored,'hashes':{name:sha(p) for name,p in paths.items()},'prediction_rows':len(data)}
        mp.write_text(json.dumps(manifest,indent=2)+'\n');fits.append(stored);all_daily.append(d);all_quant.append(q)
        print(f"Quarter {k}/68: {len(data):,} keys, {valid.sum():,} scores; {fit['training_rows']:,} mature training rows",flush=True)
    c.execute(f"CREATE VIEW predictions AS SELECT * FROM read_parquet('{parts/'fold_*.parquet'}')")
    rows,keys,nscores,nlabels,npairs=c.execute('''SELECT count(*),count(DISTINCT(permno,signal_date)),count(ridge),count(target_5d),
        count(*) FILTER(WHERE isfinite(ridge) AND isfinite(target_5d)) FROM predictions''').fetchone()
    assert rows==keys==expected
    assert c.execute('''SELECT count(*) FROM (SELECT permno,signal_date FROM source WHERE signal_date>=DATE '2003-01-02'
        EXCEPT SELECT permno,signal_date FROM predictions)''').fetchone()[0]==0
    assert c.execute('''SELECT count(*) FROM (SELECT permno,signal_date FROM predictions EXCEPT
        SELECT permno,signal_date FROM source WHERE signal_date>=DATE '2003-01-02')''').fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM predictions WHERE signal_date>=DATE '2020-01-02'").fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM predictions WHERE (prediction_status='observed') IS DISTINCT FROM (ridge IS NOT NULL)").fetchone()[0]==0
    for grouping,name in [('signal_date','coverage_by_date.csv'),('year(signal_date)','coverage_by_year.csv'),('label_status','coverage_by_status.csv'),
                          ('year(signal_date),label_status','coverage_by_year_status.csv')]:
        c.execute(f"""COPY (SELECT {grouping},count(*) eligible,count(ridge) complete_feature_predictions,count(target_5d) numeric_labels,
            count(*) FILTER(WHERE isfinite(ridge) AND isfinite(target_5d)) evaluated_pairs,
            100.0*count(ridge)/count(*) prediction_eligible_pct FROM predictions GROUP BY {grouping} ORDER BY {grouping})
            TO '{OUT/name}' (HEADER,DELIMITER ',')""")
    missing=[]
    for f in FEATURES:
        missing.append(c.execute(f"SELECT '{f}' feature,{f}_processed_reason reason,count(*) observations FROM source WHERE signal_date>=DATE '2003-01-02' GROUP BY 2").fetchdf())
    pd.concat(missing).to_csv(OUT/'feature_missingness.csv',index=False)
    for model in MODELS:
        assert sum(int(d.loc[d.model==model,'n_pairs'].sum()) for d in all_daily)==npairs
    report={'evaluation_eligible':rows,'unique_keys':keys,'numeric_labels':nlabels,'complete_feature_predictions':nscores,
        'evaluable_pairs':npairs,'quarters_completed':len(fits),'ridge_model_fits':len(fits)*9,
        'missing_prediction_rows':rows-nscores,'prediction_eligible_pct':100*nscores/rows,
        'pair_eligible_pct':100*npairs/rows,'bounded_qa_passed':True,'maturity_qa_passed':True,
        'holdout_signals_accessed':False,'frozen_definitions_changed':False,'hyperparameter_selection':False,
        'objective_metric_difference':'intentional raw-return SSE vs Rank IC','qa_passed':True}
    daily=pd.concat(all_daily,ignore_index=True);quant=pd.concat(all_quant,ignore_index=True)
    report.update(reports(daily,quant,fits))
    c.close();manifest.update(report,complete=True,source_manifest=source_manifest)
    mp.write_text(json.dumps(manifest,indent=2)+'\n')
    pd.DataFrame([{'check':k,'value':json.dumps(v)} for k,v in report.items()]).to_csv(OUT/'evaluation_qa.csv',index=False)
    print(json.dumps(report,indent=2),flush=True);figures()


def reports(daily,quant,fits):
    # Public daily aggregate metrics only; security-level predictions stay local.
    daily.to_parquet(CACHE/'daily_ic.parquet',index=False);quant.to_parquet(CACHE/'daily_quantiles.parquet',index=False)
    summary=[];annual=[];quarterly=[];phases=[];qs=[];spreads=[];monotonic=[]
    for model,d in daily.groupby('model',sort=False):
        for lag in (4,20):summary.append({'model':model,**summarize(d,lag)})
        for year,a in d.groupby(d.signal_date.dt.year):annual.append({'model':model,'year':year,**summarize(a,4)})
        for period,a in d.groupby(d.signal_date.dt.to_period('Q')):quarterly.append({'model':model,'quarter':str(period),**summarize(a,4)})
        for p in range(5):
            a=d[d.td%5==p].copy();a['phase_td']=a.td//5
            phases.append({'model':model,'phase':p,**summarize(a,4,position='phase_td')})
        q=quant[quant.model==model]
        means=q.groupby('quintile').mean_target.mean().reindex(range(1,6));dif=np.diff(means)
        monotonic.append({'model':model,'ascending_steps':int((dif>0).sum()),'descending_steps':int((dif<0).sum()),
            'strictly_increasing':bool((dif>0).all()),'strictly_decreasing':bool((dif<0).all()),'q5_minus_q1':means.iloc[-1]-means.iloc[0]})
        for bucket,a in q.groupby('quintile'):
            qs.append({'model':model,'quintile':bucket,'observed_dates':int(a.mean_target.notna().sum()),
                'empty_bucket_dates':int(a.mean_target.isna().sum()),'n_pairs':int(a.n_pairs.sum()),'mean_target':a.mean_target.mean()})
        p=q.pivot(index='signal_date',columns='quintile',values='mean_target').reindex(columns=range(1,6))
        sp=d[['signal_date','td']].merge((p[5]-p[1]).rename('spread'),left_on='signal_date',right_index=True,how='left')
        for lag in (4,20):spreads.append({'model':model,**summarize(sp,lag,value='spread')})
    for name,rows in [('ic_summary.csv',summary),('annual_ic.csv',annual),('quarterly_ic.csv',quarterly),
        ('nonoverlapping_phases.csv',phases),('quintile_summary.csv',qs),('quantile_monotonicity.csv',monotonic),('quintile_spread_summary.csv',spreads)]:
        pd.DataFrame(rows).to_csv(OUT/name,index=False)
    ip=daily.pivot(index='signal_date',columns='model',values='ic')
    td=daily[['signal_date','td']].drop_duplicates().set_index('signal_date').td
    paired=[];pairannual=[];pairphases=[]
    for model in MODELS[1:]:
        delta=(ip.ridge-ip[model]).rename('ic');p=delta.to_frame().join(td).reset_index()
        for lag in (4,20):paired.append({'benchmark':model,**summarize(p,lag)})
        for year,a in p.groupby(p.signal_date.dt.year):pairannual.append({'benchmark':model,'year':year,**summarize(a,4)})
        for phase in range(5):
            a=p[p.td%5==phase].copy();a['phase_td']=a.td//5
            pairphases.append({'benchmark':model,'phase':phase,**summarize(a,4,position='phase_td')})
    pd.DataFrame(paired).to_csv(OUT/'paired_ic_differences.csv',index=False)
    pd.DataFrame(pairannual).to_csv(OUT/'annual_paired_ic_differences.csv',index=False)
    pd.DataFrame(pairphases).to_csv(OUT/'phase_paired_ic_differences.csv',index=False)
    ip.corr().to_csv(OUT/'ic_correlations.csv')
    # All quarters and coefficients, not a selected winner.
    coeff=[];training=[]
    for fit in fits:
        for j,f in enumerate(FEATURES):coeff.append({'fold_number':fit['fold_number'],'fit_cutoff':fit['fit_cutoff'],
            'feature':f,'ridge_coefficient':fit['beta'][j],'univariate_coefficient':fit['uni_beta'][j]})
        training.append({k:v for k,v in fit.items() if k not in ('beta','uni_beta','uni_intercept')})
    pd.DataFrame(coeff).to_csv(OUT/'coefficients.csv',index=False);pd.DataFrame(training).to_csv(OUT/'training_qa.csv',index=False)
    # Stage2B pairwise reference restricted to same 2003–2019 dates, no new scope.
    broader=pd.read_csv(ROOT/'results/tables/stage2b/daily_rank_ic.csv',parse_dates=['signal_date'])
    broader[broader.signal_date>=pd.Timestamp('2003-01-02')].groupby('feature').agg(
        broader_evaluable_pairs=('n_pairs','sum'),broader_valid_dates=('ic','count')).to_csv(OUT/'broader_feature_coverage_reference.csv')
    return {'matched_score_pair_counts':True,'quantile_pair_counts_reconciled':True,
        'nominal_paired_tests_reported':len(paired),'maximum_normal_equation_error':max(f['normal_equation_residual'] for f in fits)}


def figures():
    os.environ.setdefault('MPLCONFIGDIR',str(CACHE/'matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    dest=ROOT/'results/figures/stage3a';dest.mkdir(parents=True,exist_ok=True)
    daily=pd.read_parquet(CACHE/'daily_ic.parquet');selected=MODELS[:10]
    fig,axes=plt.subplots(5,2,figsize=(13,13),sharex=True)
    for ax,model in zip(axes.flat,selected):
        v=daily[daily.model==model].set_index('signal_date').ic.resample('ME').mean()
        ax.plot(v.index,v.values,lw=.8);ax.axhline(0,color='gray',lw=.5);ax.set_title(model);ax.set_ylabel('Monthly mean Rank IC')
    fig.suptitle('Stage3A forward development 2003–2019: fixed Ridge and all learned benchmarks');fig.tight_layout();fig.savefig(dest/'forward_ic_time_series.png',dpi=150);plt.close(fig)
    q=pd.read_csv(OUT/'quintile_summary.csv');fig,axes=plt.subplots(5,2,figsize=(13,13))
    for ax,model in zip(axes.flat,selected):
        a=q[q.model==model];ax.plot(a.quintile,100*a.mean_target,'o-');ax.set_title(model);ax.set_xticks(range(1,6));ax.set_ylabel('Mean frozen 5D target (%)')
    fig.suptitle('Forward conditional quintile means; not portfolio returns');fig.tight_layout();fig.savefig(dest/'quintile_monotonicity.png',dpi=150);plt.close(fig)
    coeff=pd.read_csv(OUT/'coefficients.csv',parse_dates=['fit_cutoff']);fig,axes=plt.subplots(4,2,figsize=(12,10))
    for ax,f in zip(axes.flat,FEATURES):
        a=coeff[coeff.feature==f];ax.plot(a.fit_cutoff,a.ridge_coefficient,label='Combination');ax.plot(a.fit_cutoff,a.univariate_coefficient,label='Univariate',ls='--');ax.axhline(0,color='gray',lw=.5);ax.set_title(f)
    axes.flat[0].legend();fig.suptitle('Quarterly coefficients: past mature training only');fig.tight_layout();fig.savefig(dest/'coefficient_paths.png',dpi=150);plt.close(fig)
    pair=pd.read_csv(OUT/'paired_ic_differences.csv');a=pair[pair.lag==4].iloc[::-1];fig,ax=plt.subplots(figsize=(10,8))
    ax.errorbar(a['mean'],np.arange(len(a)),xerr=1.959963984540054*a.se,fmt='o',capsize=3);ax.set_yticks(np.arange(len(a)),a.benchmark);ax.axvline(0,color='gray');ax.set_xlabel('Mean paired Rank-IC difference / nominal HAC4 95% CI');ax.set_title('Ridge minus every prespecified benchmark; same keys/dates');fig.tight_layout();fig.savefig(dest/'paired_ic_differences.png',dpi=150);plt.close(fig)
    p=pd.read_csv(OUT/'nonoverlapping_phases.csv');fig,axes=plt.subplots(5,2,figsize=(13,13))
    for ax,model in zip(axes.flat,selected):
        a=p[p.model==model];ax.errorbar(a.phase,a['mean'],yerr=1.959963984540054*a.se,fmt='o',capsize=3);ax.axhline(0,color='gray',lw=.5);ax.set_title(model);ax.set_xticks(range(5));ax.set_xlabel('Fixed calendar phase')
    fig.suptitle('All five nonoverlap phases, sampled HAC4 intervals');fig.tight_layout();fig.savefig(dest/'nonoverlapping_phases.png',dpi=150);plt.close(fig)
    a=pd.read_csv(OUT/'coverage_by_year.csv');fig,ax=plt.subplots(figsize=(10,4));ax.plot(a.iloc[:,0],a.prediction_eligible_pct,'o-');ax.set_ylim(90,100);ax.set_xlabel('Signal year');ax.set_ylabel('Complete-feature predictions / eligible (%)');ax.set_title('Outcome-independent prediction coverage; original denominator');fig.tight_layout();fig.savefig(dest/'prediction_coverage.png',dpi=150);plt.close(fig)
    ip=pd.read_csv(OUT/'ic_correlations.csv',index_col=0).loc[list(selected),list(selected)];fig,ax=plt.subplots(figsize=(11,9));im=ax.imshow(ip.to_numpy(),vmin=-1,vmax=1,cmap='RdBu_r');ax.set_xticks(range(10),selected,rotation=60,ha='right');ax.set_yticks(range(10),selected);fig.colorbar(im,ax=ax);ax.set_title('Forward IC correlations: Ridge and all learned benchmarks');fig.tight_layout();fig.savefig(dest/'ic_correlations.png',dpi=150);plt.close(fig)

if __name__=='__main__':run()
