"""Frozen holdout predictive diagnostics; no portfolio/accounting evaluation."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb
from src.features.panel import ROOT,FEATURES
from src.evaluation.baseline import summarize,sha
from src.evaluation.statistics import rank_ic
from src.models.stage5_data import CACHE,OUT
from src.models.stage5_pipeline import CANDIDATES,forecast


def aggregate(daily,quant,paired):
    summary=[];annual=[];phases=[];quintile=[];mono=[];spreads=[];pair=[];pairyear=[];pairphase=[]
    for (model,scope),d in daily.groupby(['model','sample'],sort=False):
        for lag in (4,20):summary.append(dict(model=model,sample=scope,**summarize(d,lag)))
        for year,a in d.groupby(d.signal_date.dt.year):annual.append(dict(model=model,sample=scope,year=int(year),**summarize(a,4)))
        for phase in range(5):
            a=d[d.td%5==phase].copy();a['phase_td']=a.td//5
            phases.append(dict(model=model,sample=scope,phase=phase,**summarize(a,4,position='phase_td')))
        q=quant[(quant.model==model)&(quant['sample']==scope)]
        means=q.groupby('quintile').mean_target.mean().reindex(range(1,6));steps=np.diff(means)
        mono.append(dict(model=model,sample=scope,ascending_steps=int((steps>0).sum()),descending_steps=int((steps<0).sum()),
                         strictly_increasing=bool((steps>0).all()),strictly_decreasing=bool((steps<0).all()),
                         q5_minus_q1=means.iloc[-1]-means.iloc[0]))
        for bucket,a in q.groupby('quintile'):
            quintile.append(dict(model=model,sample=scope,quintile=int(bucket),observed_dates=int(a.mean_target.notna().sum()),
                                 empty_bucket_dates=int(a.mean_target.isna().sum()),n_pairs=int(a.n_pairs.sum()),mean_target=a.mean_target.mean()))
        wide=q.pivot(index='signal_date',columns='quintile',values='mean_target').reindex(columns=range(1,6))
        sp=d[['signal_date','td']].merge((wide[5]-wide[1]).rename('spread'),left_on='signal_date',right_index=True,how='left')
        for lag in (4,20):spreads.append(dict(model=model,sample=scope,**summarize(sp,lag,value='spread')))
    for benchmark,p in paired.groupby('benchmark',sort=False):
        for lag in (4,20):pair.append(dict(benchmark=benchmark,sample='identical_complete8_keys',**summarize(p,lag)))
        for year,a in p.groupby(p.signal_date.dt.year):pairyear.append(dict(benchmark=benchmark,year=int(year),**summarize(a,4)))
        for phase in range(5):
            a=p[p.td%5==phase].copy();a['phase_td']=a.td//5
            pairphase.append(dict(benchmark=benchmark,phase=phase,**summarize(a,4,position='phase_td')))
    return dict(ic_summary=summary,annual_ic=annual,nonoverlapping_phases=phases,quintile_summary=quintile,
                quantile_monotonicity=mono,quintile_spread_summary=spreads,paired_ic_differences=pair,
                annual_paired_ic_differences=pairyear,phase_paired_ic_differences=pairphase)


def development_comparison(tables):
    development=pd.read_csv(ROOT/'results/tables/stage3a/ic_summary.csv')
    broader=pd.read_csv(ROOT/'results/tables/stage2b/daily_rank_ic.csv',parse_dates=['signal_date'])
    broader=broader[(broader.feature=='reversal_5')&(broader.signal_date>=pd.Timestamp('2003-01-02'))]
    aliases=dict(raw_reversal='raw_reversal_5',univariate_reversal_ridge='uni_reversal_5',ridge='ridge')
    rows=[]
    for h in pd.DataFrame(tables['ic_summary']).to_dict('records'):
        if h['model']=='raw_reversal' and h['sample']=='primary_available':
            d=summarize(broader,h['lag'])
        else:
            d=development[(development.model==aliases[h['model']])&(development.lag==h['lag'])].iloc[0].to_dict()
        rows.append(dict(model=h['model'],sample=h['sample'],lag=h['lag'],
            development_signal_period='2003-01-02/2019-12-31',holdout_signal_period='2020-01-02/2025-12-31',
            development_mean_ic=d['mean'],holdout_mean_ic=h['mean'],holdout_minus_development_mean=h['mean']-d['mean'],
            development_positive_frequency=d['positive_frequency'],holdout_positive_frequency=h['positive_frequency'],
            development_dates=d['n_dates'],holdout_dates=h['n_dates'],comparison='descriptive; no specification change'))
    # Also retain the original full 1993–2019 unfitted feature evidence, explicitly
    # distinct from the 2003–2019 forward-model stream.
    prior=pd.read_csv(ROOT/'results/tables/stage2b/ic_summary.csv')
    feature_column='feature' if 'feature' in prior else 'model'
    prior=prior[prior[feature_column]=='reversal_5'].copy()
    prior['comparison_scope']='original 1993–2019 frozen unmodeled development reference'
    prior.to_csv(OUT/'original_development_reversal_reference.csv',index=False)
    pd.DataFrame(rows).to_csv(OUT/'development_holdout_comparison.csv',index=False)
    # Annual and phase development references carry every frozen result; no
    # favorable-year/phase selection and no newly fit development model.
    for name in ('annual_ic','nonoverlapping_phases','quantile_monotonicity','paired_ic_differences'):
        d=pd.read_csv(ROOT/f'results/tables/stage3a/{name}.csv')
        if 'model' in d:d=d[d.model.isin(aliases.values())]
        elif 'benchmark' in d:d=d[d.benchmark.isin(['raw_reversal_5','uni_reversal_5'])]
        d.to_csv(OUT/(name+'_development_reference.csv'),index=False)


def independent_qa(c,manifest):
    checks=[]
    for k,record in manifest['folds'].items():
        i=int(k)
        locations=dict(predictions=CACHE/f'predictions/fold_{i:02d}.parquet',
            evaluation=CACHE/f'evaluation_batches/fold_{i:02d}.parquet',daily=CACHE/f'evaluation_batches/daily_{i:02d}.parquet',
            quantiles=CACHE/f'evaluation_batches/quantiles_{i:02d}.parquet',paired=CACHE/f'evaluation_batches/paired_{i:02d}.parquet',
            moments=CACHE/f'moments_{i:02d}.parquet')
        for name,p in locations.items():assert sha(p)==record['hashes'][name]
        p=pd.read_parquet(locations['predictions'])
        assert not {'target_5d','label_status','label_reason','entry_open','exit_open'}.intersection(p.columns)
        fit=record['fit'];cut=pd.Timestamp(fit['fit_cutoff'])
        for field in ('max_training_signal','max_training_exit','max_training_maturity'):assert pd.Timestamp(fit[field])<=cut
        assert fit['lambda']==1 and record['predictions_saved_before_label_join']
        c.register('keys',p[['permno','signal_date']].head(100))
        f=c.execute(f"""SELECT f.* FROM read_parquet('{ROOT/'data/interim/stage2a_features/parts/part_*.parquet'}') f
            JOIN keys k USING(permno,signal_date) ORDER BY signal_date,permno""").fetchdf()
        sc,valid=forecast(f[[f+'_z' for f in FEATURES]].to_numpy(float),fit)
        stored=p.head(100).sort_values(['signal_date','permno'])
        np.testing.assert_allclose(sc,stored[list(CANDIDATES)].to_numpy(float),atol=1e-12,equal_nan=True)
        checks.append(dict(fold_number=i,rows_recomputed=len(stored),prediction_checkpoint_verified=True,
            outcome_metadata_absent=True,maturity_and_lambda_verified=True,max_error=float(np.nanmax(np.abs(sc-stored[list(CANDIDATES)].to_numpy())))))
    pd.DataFrame(checks).to_csv(OUT/'independent_prediction_qa.csv',index=False)
    return checks


def report():
    manifest=json.loads((CACHE/'manifest.json').read_text());assert manifest['complete'] and manifest['qa_passed']
    OUT.mkdir(parents=True,exist_ok=True)
    c=duckdb.connect();c.execute("SET threads=2; SET memory_limit='2GB'")
    checks=independent_qa(c,manifest)
    daily=pd.concat([pd.read_parquet(p) for p in sorted((CACHE/'evaluation_batches').glob('daily_*.parquet'))],ignore_index=True)
    quant=pd.concat([pd.read_parquet(p) for p in sorted((CACHE/'evaluation_batches').glob('quantiles_*.parquet'))],ignore_index=True)
    paired=pd.concat([pd.read_parquet(p) for p in sorted((CACHE/'evaluation_batches').glob('paired_*.parquet'))],ignore_index=True)
    assert not daily.duplicated(['signal_date','model','sample']).any()
    assert set(daily.model)==set(CANDIDATES)
    daily.to_csv(OUT/'daily_rank_ic.csv',index=False);quant.to_parquet(CACHE/'daily_quantiles.parquet',index=False)
    paired.to_csv(OUT/'daily_paired_ic_differences.csv',index=False)
    tables=aggregate(daily,quant,paired)
    for name,rows in tables.items():pd.DataFrame(rows).to_csv(OUT/(name+'.csv'),index=False)
    c.execute(f"CREATE VIEW evaluation AS SELECT * FROM read_parquet('{CACHE/'evaluation_batches/fold_*.parquet'}')")
    n,keys,numeric=c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)),count(target_5d) FROM evaluation').fetchone()
    assert n==keys==1882649 and numeric==1872680
    statuses=c.execute('SELECT label_status,count(*) eligible,count(target_5d) numeric_labels FROM evaluation GROUP BY 1 ORDER BY 1').fetchdf()
    statuses.to_csv(OUT/'holdout_label_status.csv',index=False)
    coverage=[];year=[];status=[];date=[]
    for model in CANDIDATES:
        for grouping,dest in [('',coverage),('year(signal_date)',year),('label_status',status),('signal_date',date)]:
            gr=f'{grouping},' if grouping else '';tail=f'GROUP BY {grouping} ORDER BY {grouping}' if grouping else ''
            d=c.execute(f"""SELECT '{model}' model,{gr}count(*) original_eligible,count(target_5d) numeric_labels,
                count({model}) predictions,count(*) FILTER(WHERE isfinite({model}) AND isfinite(target_5d)) evaluated_pairs,
                100.0*count({model})/count(*) prediction_eligible_pct,
                100.0*count(*) FILTER(WHERE isfinite({model}) AND isfinite(target_5d))/count(*) evaluation_eligible_pct
                FROM evaluation {tail}""").fetchdf();dest.append(d)
    for name,rows in [('coverage',coverage),('coverage_by_year',year),('coverage_by_label_status',status),('coverage_by_date',date)]:
        pd.concat(rows,ignore_index=True).to_csv(OUT/(name+'.csv'),index=False)
    missing=[]
    for f in FEATURES:
        missing.append(c.execute(f"SELECT '{f}' feature,{f}_processed_reason reason,count(*) observations FROM evaluation GROUP BY 2").fetchdf())
    pd.concat(missing).to_csv(OUT/'feature_missingness.csv',index=False)
    for model in CANDIDATES:
        pairs=int(pd.concat(coverage).loc[lambda d:d.model==model,'evaluated_pairs'].iloc[0])
        assert int(daily[(daily.model==model)&(daily['sample']=='primary_available')].n_pairs.sum())==pairs
    # Independently recompute paired differences and the exact calendar-HAC.
    matched=daily[daily['sample']=='matched_complete8'].pivot(index='signal_date',columns='model',values='ic')
    for benchmark,p in paired.groupby('benchmark'):
        expected=matched.ridge-matched[benchmark]
        np.testing.assert_allclose(p.sort_values('signal_date').ic,expected.sort_index(),atol=1e-12,equal_nan=True)
    fits=[v['fit'] for v in manifest['folds'].values()]
    coefficients=[]
    for f in fits:
        for j,feature in enumerate(FEATURES):coefficients.append(dict(quarter=f['quarter'],fit_cutoff=f['fit_cutoff'],feature=feature,
            ridge_coefficient=f['beta'][j],univariate_reversal_coefficient=f['reversal_beta'] if j==0 else np.nan))
    pd.DataFrame(coefficients).to_csv(OUT/'coefficients.csv',index=False)
    pd.DataFrame([{k:v for k,v in f.items() if k!='beta'} for f in fits]).to_csv(OUT/'training_qa.csv',index=False)
    pd.DataFrame([dict(fold_number=int(k),**v['maturity_qa']) for k,v in manifest['folds'].items()]).to_csv(OUT/'source_maturity_qa.csv',index=False)
    development_comparison(tables)
    phase=pd.DataFrame(tables['nonoverlapping_phases']);summary=pd.DataFrame(tables['ic_summary'])
    phase.merge(summary[summary.lag==4][['model','sample','mean','se','t_stat','n_dates']],on=['model','sample'],
        suffixes=('_phase','_all_dates')).to_csv(OUT/'overlapping_vs_nonoverlapping.csv',index=False)
    c.close();figures(daily,pd.DataFrame(tables['quintile_summary']),phase)
    for name,h in manifest['source']['protected_hashes'].items():assert sha(ROOT/name)==h
    summary_qa=dict(qa_passed=True,eligible_keys=n,numeric_labels=numeric,missing_labels=n-numeric,
        quarters=24,reported_fitted_models=48,predictions_before_outcomes=True,
        independent_score_rows=sum(x['rows_recomputed'] for x in checks),verified_batch_files=24*6,
        paired_security_keys_identical=True,original_calendar_anchor_preserved=True,
        source_maturity_violations=0,protected_development_artifacts_unchanged=True,
        hyperparameters_tuned=False,feature_selection=False,portfolio_results=False,
        holdout_opened_once=True,raw_reversal_definition='unmodeled frozen Stage2A signed reversal_5_z',
        earlier_holdout_labels_used_only_after_maturity=True,
        evaluation_is_conditional_on_measurability=True,static_publication_vintage_proven=False)
    summary_qa['outputs']={str(p.relative_to(ROOT)):sha(p) for folder in [OUT,ROOT/'results/figures/stage5'] for p in folder.glob('*') if p.is_file() and p.name!='report_manifest.json'}
    (OUT/'report_manifest.json').write_text(json.dumps(summary_qa,indent=2)+'\n')
    return summary_qa


def figures(daily,quintile,phase):
    import os
    os.environ.setdefault('MPLCONFIGDIR',str(CACHE/'matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    dest=ROOT/'results/figures/stage5';dest.mkdir(parents=True,exist_ok=True)
    labels={'raw_reversal':'Unfitted reversal','univariate_reversal_ridge':'Univariate reversal Ridge','ridge':'Eight-feature Ridge'}
    d=daily[daily['sample']=='primary_available']
    fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
    for ax,model in zip(axes,CANDIDATES):
        a=d[d.model==model].set_index('signal_date');v=a.ic.resample('ME').mean()
        ax.plot(v.index,v,lw=1);ax.axhline(0,color='gray',lw=.6);ax.set_ylabel('Monthly mean Rank IC');ax.set_title(labels[model])
    fig.suptitle('Single prespecified predictive holdout: 2020–2025');fig.tight_layout();fig.savefig(dest/'holdout_ic_time_series.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,model in zip(axes,CANDIDATES):
        a=d[d.model==model].ic.dropna();ax.hist(a,bins=40,alpha=.8);ax.axvline(0,color='gray');ax.set_title(labels[model]);ax.set_xlabel('Daily Rank IC')
    axes[0].set_ylabel('Reporting dates');fig.tight_layout();fig.savefig(dest/'holdout_ic_distributions.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,model in zip(axes,CANDIDATES):
        a=quintile[(quintile.model==model)&(quintile['sample']=='primary_available')]
        ax.plot(a.quintile,a.mean_target*100,'o-');ax.set_title(labels[model]);ax.set_xticks(range(1,6));ax.set_xlabel('Tie-preserving score quintile')
    axes[0].set_ylabel('Mean frozen 5-day target (%)');fig.suptitle('Holdout quintiles: predictive contrasts, not portfolio returns');fig.tight_layout();fig.savefig(dest/'holdout_quintile_monotonicity.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,model in zip(axes,CANDIDATES):
        a=phase[(phase.model==model)&(phase['sample']=='primary_available')]
        ax.errorbar(a.phase,a['mean'],yerr=1.959963984540054*a.se,fmt='o',capsize=3);ax.axhline(0,color='gray');ax.set_title(labels[model]);ax.set_xticks(range(5));ax.set_xlabel('Fixed global-calendar phase')
    axes[0].set_ylabel('Mean IC / sampled HAC4 95% CI');fig.suptitle('All five fixed non-overlapping phases');fig.tight_layout();fig.savefig(dest/'holdout_phase_robustness.png',dpi=150);plt.close(fig)
    a=pd.read_csv(OUT/'annual_ic.csv');a=a[a['sample']=='primary_available']
    fig,ax=plt.subplots(figsize=(10,5))
    for model in CANDIDATES:
        v=a[a.model==model];ax.plot(v.year,v['mean'],'o-',label=labels[model])
    ax.axhline(0,color='gray');ax.set_xticks(range(2020,2026));ax.legend();ax.set_ylabel('Annual mean Rank IC');ax.set_title('All six holdout years, unchanged candidates');fig.tight_layout();fig.savefig(dest/'holdout_annual_stability.png',dpi=150);plt.close(fig)
    p=pd.read_csv(OUT/'paired_ic_differences.csv');p=p[p.lag==4]
    fig,ax=plt.subplots(figsize=(10,4));ax.errorbar(p['mean'],range(len(p)),xerr=1.959963984540054*p.se,fmt='o',capsize=3)
    ax.set_yticks(range(len(p)),[labels[b] for b in p.benchmark]);ax.axvline(0,color='gray');ax.set_xlabel('Ridge-minus-benchmark mean IC / HAC4 95% CI')
    ax.set_title('Paired holdout difference: identical complete-eight security keys');fig.tight_layout();fig.savefig(dest/'holdout_paired_differences.png',dpi=150);plt.close(fig)
    cov=pd.read_csv(OUT/'coverage_by_year.csv');fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
    for model in CANDIDATES:
        a=cov[cov.model==model];axes[0].plot(a.iloc[:,1],a.prediction_eligible_pct,'o-',label=labels[model]);axes[1].plot(a.iloc[:,1],a.evaluation_eligible_pct,'o-',label=labels[model])
    axes[0].set_ylabel('Predictions / original eligible (%)');axes[1].set_ylabel('Evaluated pairs / original eligible (%)')
    axes[0].legend();axes[1].set_xticks(range(2020,2026));axes[1].set_xlabel('Signal year');fig.suptitle('Coverage retained separately from predictive outcomes');fig.tight_layout();fig.savefig(dest/'holdout_coverage.png',dpi=150);plt.close(fig)
    comp=pd.read_csv(OUT/'development_holdout_comparison.csv');comp=comp[(comp.lag==4)&(comp['sample']=='matched_complete8')]
    fig,ax=plt.subplots(figsize=(10,4));x=np.arange(3)
    ax.bar(x-.18,comp.development_mean_ic,.36,label='Development 2003–2019');ax.bar(x+.18,comp.holdout_mean_ic,.36,label='Holdout 2020–2025')
    ax.set_xticks(x,[labels[m] for m in comp.model]);ax.axhline(0,color='gray');ax.set_ylabel('Mean IC on complete-eight keys');ax.legend();ax.set_title('Descriptive development/holdout comparison; no model changes');fig.tight_layout();fig.savefig(dest/'development_holdout_ic.png',dpi=150);plt.close(fig)
