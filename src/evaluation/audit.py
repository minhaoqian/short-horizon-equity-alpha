"""Development-only post-evaluation reconciliation and descriptive reporting."""
import json
import numpy as np
import pandas as pd
import duckdb
from scipy.stats import spearmanr
from src.features.panel import ROOT,FEATURES
from src.evaluation.statistics import rank_ic


def run():
    out=ROOT/'results/tables/stage2b';cache=ROOT/'data/interim/stage2b'
    daily=pd.read_csv(out/'daily_rank_ic.csv',parse_dates=['signal_date'])
    quant=pd.read_csv(out/'daily_quintiles.csv',parse_dates=['signal_date'])
    cov=pd.read_csv(out/'development_coverage.csv')
    checks=[];buckets=[];annual_q=[];monotonic=[]
    undefined=daily[daily.ic.isna()].copy()
    undefined['attribution']=np.select([undefined.eligible.eq(0),undefined.numeric_labels.eq(0),undefined.n_pairs.eq(0)],
        ['no_eligible_signals','no_numeric_labels_under_frozen_policy','no_finite_feature_numeric_pairs'],default='insufficient_or_constant_pairs')
    undefined.to_csv(out/'undefined_ic_attribution.csv',index=False)
    for feature in FEATURES:
        d=daily[daily.feature==feature];q=quant[quant.feature==feature]
        valid=d[d.ic_reason=='observed']
        assert valid.ic.notna().all() and d.loc[d.ic_reason!='observed','ic'].isna().all()
        row=cov.feature==feature
        cov.loc[row,'evaluated_pairs']=int(valid.n_pairs.sum())
        cov.loc[row,'pairs_on_undefined_ic_dates']=int(d.loc[d.ic.isna(),'n_pairs'].sum())
        cov.loc[row,'valid_ic_dates']=len(valid)
        cov.loc[row,'undefined_ic_dates']=int(d.ic.isna().sum())
        cov.loc[row,'evaluated_eligible_pct']=100*valid.n_pairs.sum()/cov.loc[row,'eligible'].iloc[0]
        for bucket in range(1,6):
            v=q[q.quintile==bucket]
            buckets.append({'feature':feature,'quintile':bucket,'valid_ic_dates':len(valid),
                'observed_bucket_dates':len(v),'empty_bucket_dates':len(valid)-len(v),
                'min_bucket_size':int(v.n_pairs.min()),'max_bucket_size':int(v.n_pairs.max())})
        means=q.groupby('quintile').mean_target.mean().reindex(range(1,6))
        diff=np.diff(means)
        monotonic.append({'feature':feature,'ordered_bucket_spearman':spearmanr(np.arange(1,6),means).statistic,
            'ascending_steps':int((diff>0).sum()),'descending_steps':int((diff<0).sum()),
            'strictly_increasing':bool((diff>0).all()),'strictly_decreasing':bool((diff<0).all()),
            'q5_minus_q1':means.iloc[-1]-means.iloc[0]})
        for (year,bucket),a in q.groupby([q.signal_date.dt.year,'quintile']):
            annual_q.append({'feature':feature,'year':year,'quintile':bucket,'n_dates':len(a),
                'n_pairs':int(a.n_pairs.sum()),'mean_target':a.mean_target.mean()})
        assert not q.duplicated(['signal_date','quintile']).any()
        bydate=q.groupby('signal_date').n_pairs.sum()
        assert (bydate.sort_index().values==valid.set_index('signal_date').sort_index().n_pairs.values).all()
        checks.append({'check':'quintile_and_valid_ic_pairs','feature':feature,'passed':True,'max_error':0.})
    for column in ('evaluated_pairs','pairs_on_undefined_ic_dates','valid_ic_dates','undefined_ic_dates'):
        cov[column]=cov[column].astype('int64')
    cov.to_csv(out/'development_coverage.csv',index=False)
    pd.DataFrame(buckets).to_csv(out/'quintile_bucket_qa.csv',index=False)
    pd.DataFrame(annual_q).to_csv(out/'annual_quintiles.csv',index=False)
    pd.DataFrame(monotonic).to_csv(out/'quantile_monotonicity_summary.csv',index=False)
    summary=pd.read_csv(out/'ic_summary.csv');phase=pd.read_csv(out/'nonoverlapping_phases.csv')
    phase.groupby('feature')['mean'].agg(['min','max']).to_csv(out/'phase_mean_ranges.csv')
    annual=pd.read_csv(out/'annual_ic.csv')
    annual.groupby('feature')['mean'].agg(min='min',max='max',positive_years=lambda x:int((x>0).sum()),years='count').to_csv(out/'annual_stability_summary.csv')
    ref=summary[summary.lag==4][['feature','mean','se','t_stat','ci_lower','ci_upper','n_dates']]
    phase.merge(ref,on='feature',suffixes=('_sampled','_all_dates')).to_csv(out/'overlapping_vs_nonoverlapping.csv',index=False)
    c=duckdb.connect();c.execute('SET threads=2')
    # Two whole-cross-section missing-label dates are explained by the already
    # frozen unavailable open of 1994-11-07, not filled or calendar-compressed.
    endpoint=c.execute(f"""SELECT signal_date,label_status,label_reason,count(*) observations
        FROM read_parquet('{ROOT/'data/interim/stage1g_targets/targets_5d.parquet'}')
        WHERE signal_date IN (DATE '1994-10-28',DATE '1994-11-04') GROUP BY 1,2,3 ORDER BY 1""").fetchdf()
    endpoint.to_csv(out/'missing_label_date_attribution.csv',index=False)
    opens=c.execute(f"""SELECT dlycaldt,count(*) daily_rows,count(*) FILTER(WHERE eligible) eligible_rows,
        count(*) FILTER(WHERE eligible AND dlyopen>0) eligible_positive_open,
        count(*) FILTER(WHERE eligible AND dlyprc>0) eligible_positive_close
        FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_parts/part_*.parquet'}')
        WHERE dlycaldt IN (DATE '1994-10-31',DATE '1994-11-07') GROUP BY 1 ORDER BY 1""").fetchdf()
    opens.to_csv(out/'missing_open_date_qa.csv',index=False)
    # Fixed audit dates, no return-driven date choice and no holdout signal query.
    dates="DATE '1993-05-03',DATE '2005-06-30',DATE '2019-12-31'"
    c.execute(f"""CREATE TABLE f AS SELECT permno,signal_date,{','.join(f+'_z' for f in FEATURES)}
        FROM read_parquet('{ROOT/'data/interim/stage2a_features/parts/part_*.parquet'}')
        WHERE signal_date IN ({dates}) AND signal_date<=DATE '2019-12-31'""")
    c.execute(f"""CREATE TABLE labels AS SELECT permno,signal_date,target_5d FROM
        read_parquet('{ROOT/'data/interim/stage1g_targets/targets_5d.parquet'}')
        WHERE signal_date IN ({dates}) AND signal_date<=DATE '2019-12-31'""")
    data=c.execute('SELECT f.*,l.target_5d FROM f JOIN labels l USING(permno,signal_date)').fetchdf();c.close()
    for date,frame in data.groupby('signal_date'):
        for feature in FEATURES:
            expected,reason,n=rank_ic(frame[feature+'_z'],frame.target_5d)
            got=daily[(daily.feature==feature)&(daily.signal_date==date)].iloc[0]
            assert n==got.n_pairs and reason==got.ic_reason
            error=abs(expected-got.ic) if np.isfinite(expected) else 0.
            assert error<1e-12
            checks.append({'check':'independent_scipy_rank_ic','feature':feature,'signal_date':str(date.date()),'passed':True,'max_error':error})
    pd.DataFrame(checks).to_csv(out/'independent_evaluation_qa.csv',index=False)
    manifest_path=cache/'manifest.json';m=json.loads(manifest_path.read_text())
    m.update(independent_rank_checks=24,independent_rank_max_error=max(x['max_error'] for x in checks),
        quantile_empty_buckets=int(sum(x['empty_bucket_dates'] for x in buckets)),
        fixed_lags=[4,20],sampled_phase_lag=4,phase_anchor='1993-01-04',phases=list(range(5)),
        quantile_rule='average ranks; floor(5*(rank-0.5)/n)+1; ties together',
        primary_feature_version='stored Stage2A z; no reprocessing',
        missing_label_rows=4816452-4804070,
        development_cash_delisting_numeric=2549,development_valid_entry_unresolved=3534+1616,
        final_holdout_policy='2020-01-02 through 2025-12-31 SIGNALS untouched; development crossing holdings retained',
        performance_driven_specification_changes=False)
    manifest_path.write_text(json.dumps(m,indent=2)+'\n')
    qa_keys=('keys','numeric_labels','development_signal_dates','cross_boundary_eligible','cross_boundary_numeric',
        'calendar_rows','calendar_index_mismatches','source_feature_hashes_verified','holdout_signal_values_materialized',
        'holdout_predictive_diagnostics','duplicate_or_key_difference_count','all_quintile_pair_counts_reconciled',
        'all_feature_pair_counts_reconciled','preprocessing_recomputed','features_dropped_or_flipped','horizons_constructed',
        'independent_rank_checks','independent_rank_max_error','quantile_empty_buckets','missing_label_rows',
        'development_cash_delisting_numeric','development_valid_entry_unresolved','fixed_lags','sampled_phase_lag','phase_anchor','qa_passed')
    pd.DataFrame([{'check':key,'value':json.dumps(m[key])} for key in qa_keys]).to_csv(out/'evaluation_qa.csv',index=False)
    print(json.dumps({k:m[k] for k in ('independent_rank_checks','independent_rank_max_error','quantile_empty_buckets','qa_passed')},indent=2))

if __name__=='__main__':run()
