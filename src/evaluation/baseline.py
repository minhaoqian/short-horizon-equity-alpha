"""Frozen-feature evaluation of DEVELOPMENT signal dates only; no fitting.

All source projections are filtered before materialization. There is deliberately
no end-date CLI override and no code path for holdout predictive evaluation.
"""
from pathlib import Path
import hashlib
import json
import itertools
import numpy as np
import pandas as pd
import duckdb
from src.features.panel import ROOT, FEATURES
from src.evaluation.source_qa import validate_relations
from src.evaluation.statistics import hac_mean

START='1993-01-04'
END='2019-12-31'
EXPECTED_KEYS=4816452
EXPECTED_NUMERIC=4804070


def development_projection(c,features,targets):
    """Materialize only permitted signals, retaining cross-boundary exits."""
    c.execute(f"CREATE TABLE f AS SELECT * FROM read_parquet('{features}') WHERE signal_date BETWEEN DATE '{START}' AND DATE '{END}'")
    c.execute(f"""CREATE TABLE labels AS SELECT permno,signal_date,entry_date,exit_date,target_5d,label_status,label_reason,
        target_5d IS NOT NULL numeric_label,isfinite(target_5d) finite_label
        FROM read_parquet('{targets}') WHERE signal_date BETWEEN DATE '{START}' AND DATE '{END}'""")


def ranked_pairs(c,feature):
    # SQL average rank = first tied rank + (tie multiplicity - 1)/2.
    c.execute(f"""CREATE OR REPLACE TEMP TABLE pairs AS SELECT *,
        rank() OVER(PARTITION BY signal_date ORDER BY x)+(count(*) OVER(PARTITION BY signal_date,x)-1)/2.0 rx,
        rank() OVER(PARTITION BY signal_date ORDER BY y)+(count(*) OVER(PARTITION BY signal_date,y)-1)/2.0 ry,
        count(*) OVER(PARTITION BY signal_date) n
        FROM (SELECT permno,signal_date,{feature}_z x,target_5d y FROM joined
        WHERE isfinite({feature}_z) AND isfinite(target_5d))""")
    c.execute("""CREATE OR REPLACE TEMP TABLE metrics AS SELECT signal_date,count(*) n_pairs,
        CASE WHEN count(*)>=30 AND stddev_pop(rx)>0 AND stddev_pop(ry)>0 THEN corr(rx,ry) END ic,
        CASE WHEN count(*)<30 THEN 'insufficient_pairs'
             WHEN stddev_pop(rx)=0 OR stddev_pop(ry)=0 THEN 'constant_rank_vector' ELSE 'observed' END ic_reason
        FROM pairs GROUP BY signal_date""")


def feature_aggregates(c,feature):
    ranked_pairs(c,feature)
    daily=c.execute("""SELECT cal.signal_date,cal.td,coalesce(e.eligible,0) eligible,
        coalesce(e.numeric_labels,0) numeric_labels,coalesce(m.n_pairs,0) n_pairs,m.ic,
        coalesce(m.ic_reason,'insufficient_pairs') ic_reason
        FROM calendar cal LEFT JOIN date_counts e USING(signal_date) LEFT JOIN metrics m USING(signal_date)
        ORDER BY cal.td""").fetchdf()
    daily['feature']=feature
    q=c.execute("""SELECT signal_date,least(5,1+floor(5*(rx-.5)/n))::INTEGER quintile,
        count(*) n_pairs,avg(y) mean_target,median(y) median_target
        FROM pairs JOIN metrics USING(signal_date) WHERE ic_reason='observed' GROUP BY 1,2 ORDER BY 1,2""").fetchdf()
    q['feature']=feature
    return daily,q


def summarize(frame,lag=4,position='td',value='ic'):
    values=frame[value].to_numpy(float)
    h=hac_mean(values,frame[position].to_numpy(int),lag)
    finite=values[np.isfinite(values)]
    h.update(median=float(np.median(finite)) if len(finite) else None,
             std=float(np.std(finite,ddof=1)) if len(finite)>1 else None,
             positive_frequency=float(np.mean(finite>0)) if len(finite) else None)
    return h


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def run():
    cache=ROOT/'data/interim/stage2b';cache.mkdir(parents=True,exist_ok=True)
    out=ROOT/'results/tables/stage2b';out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/interim/stage2a_features'
    sm=json.loads((source/'manifest.json').read_text())
    assert sm['complete'] and sm['qa_passed']
    inputs=[source/'manifest.json',ROOT/'data/interim/stage1g_targets/targets_5d.parquet']+[ROOT/x['file'] for x in sm['final_files']]
    fingerprints=[{'path':str(p.relative_to(ROOT)),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in inputs]
    # Stage 2A's official hashes are verified without interpreting any rows.
    for record in sm['final_files']:
        assert sha(ROOT/record['file'])==record['sha256'],'Corrupt feature partition'
    token=hashlib.sha256(json.dumps({'sources':fingerprints,'implementation':sha(__file__),
        'statistics':sha(Path(__file__).with_name('statistics.py'))},sort_keys=True).encode()).hexdigest()
    manifest_path=cache/'manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'fingerprint':token,'batches':{}}
    if manifest['fingerprint']!=token:raise ValueError('Source/code fingerprint changed; explicitly archive incompatible cache before rerun')
    c=duckdb.connect();c.execute("SET threads=2; SET memory_limit='2GB'")
    c.execute(f"SET temp_directory='{cache/'temp'}'")
    development_projection(c,source/'parts/part_*.parquet',ROOT/'data/interim/stage1g_targets/targets_5d.parquet')
    key_qa=validate_relations(c,EXPECTED_KEYS,EXPECTED_NUMERIC)
    assert c.execute('SELECT count(*) FROM f WHERE max_input_date>signal_date').fetchone()[0]==0
    c.execute('CREATE TABLE joined AS SELECT f.*,l.* EXCLUDE(permno,signal_date) FROM f JOIN labels l USING(permno,signal_date)')
    # Market calendar is not security-row compressed; no price/return projection.
    c.execute(f"""CREATE TABLE calendar AS SELECT dlycaldt signal_date,(row_number() OVER(ORDER BY dlycaldt)-1)::INTEGER td
        FROM (SELECT DISTINCT dlycaldt FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_parts/part_00.parquet'}')
        WHERE dlycaldt BETWEEN DATE '{START}' AND DATE '{END}')""")
    assert str(c.execute('SELECT min(signal_date) FROM calendar').fetchone()[0])==START
    assert c.execute('SELECT count(*) FROM labels l ANTI JOIN calendar USING(signal_date)').fetchone()[0]==0
    # Independently verify absolute locked trading-day indexes, only development dates.
    mismatch=c.execute(f"""SELECT count(*) FROM (SELECT DISTINCT signal_date,signal_td FROM
        read_parquet('{ROOT/'data/interim/target_boundary_audit_parts/part_*.parquet'}')
        WHERE signal_date BETWEEN DATE '{START}' AND DATE '{END}') a JOIN calendar b USING(signal_date)
        WHERE signal_td<>td+1""").fetchone()[0]
    assert mismatch==0,'Global market-calendar mismatch'
    c.execute('CREATE TABLE date_counts AS SELECT signal_date,count(*) eligible,count(target_5d) numeric_labels FROM joined GROUP BY signal_date')
    status=c.execute('SELECT label_status,count(*) observations,count(target_5d) numeric_labels FROM labels GROUP BY 1 ORDER BY 1').fetchdf()
    status['eligible_pct']=100*status.observations/EXPECTED_KEYS;status.to_csv(out/'development_label_status.csv',index=False)
    cross=c.execute("SELECT count(*),count(target_5d) FROM labels WHERE exit_date>=DATE '2020-01-02'").fetchone()
    coverage=[];years=[];statuses=[];miss=[];all_daily=[];all_q=[]
    for feature in FEATURES:
        print(f'{feature}: coverage and daily tied-rank aggregates',flush=True)
        coverage.append(c.execute(f"""SELECT '{feature}' feature,count(*) eligible,count(target_5d) numeric_labels,
            count(*) FILTER(WHERE isfinite({feature}_z)) finite_feature,
            count(*) FILTER(WHERE isfinite({feature}_z) AND isfinite(target_5d)) evaluable_pairs FROM joined""").fetchdf())
        years.append(c.execute(f"""SELECT '{feature}' feature,year(signal_date) AS year,count(*) eligible,count(target_5d) numeric_labels,
            count(*) FILTER(WHERE isfinite({feature}_z) AND isfinite(target_5d)) evaluable_pairs FROM joined GROUP BY 2 ORDER BY 2""").fetchdf())
        statuses.append(c.execute(f"""SELECT '{feature}' feature,label_status,count(*) status_rows,
            count(*) FILTER(WHERE isfinite({feature}_z)) finite_feature FROM joined GROUP BY 2""").fetchdf())
        miss.append(c.execute(f"SELECT '{feature}' feature,{feature}_processed_reason reason,count(*) observations FROM joined GROUP BY 2").fetchdf())
        dp=cache/f'{feature}_ic.parquet';qp=cache/f'{feature}_quintiles.parquet';saved=manifest['batches'].get(feature)
        if saved:
            assert sha(dp)==saved['daily_sha'] and sha(qp)==saved['quantile_sha'],'Corrupt aggregate batch'
            d=pd.read_parquet(dp);q=pd.read_parquet(qp);print('  verified cached batch',flush=True)
        else:
            d,q=feature_aggregates(c,feature)
            for data,path in ((d,dp),(q,qp)):
                tmp=path.with_suffix('.tmp.parquet');data.to_parquet(tmp,index=False);tmp.replace(path)
            manifest['batches'][feature]={'daily_sha':sha(dp),'quantile_sha':sha(qp),'daily_rows':len(d),'quantile_rows':len(q)}
            manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
        assert d.signal_date.max()<=pd.Timestamp(END) and q.signal_date.max()<=pd.Timestamp(END)
        assert not d.signal_date.duplicated().any() and d.ic.dropna().between(-1-1e-12,1+1e-12).all()
        assert int(d.n_pairs.sum())==int(coverage[-1].evaluable_pairs.iloc[0])
        assert int(q.n_pairs.sum())==int(d.loc[d.ic.notna(),'n_pairs'].sum())
        all_daily.append(d);all_q.append(q)
    cov=pd.concat(coverage,ignore_index=True)
    cov['eligible_coverage_pct']=100*cov.evaluable_pairs/cov.eligible
    cov['labeled_coverage_pct']=100*cov.evaluable_pairs/cov.numeric_labels
    cov['feature_missing_labeled']=cov.numeric_labels-cov.evaluable_pairs
    cov.to_csv(out/'development_coverage.csv',index=False)
    pd.concat(years).to_csv(out/'development_coverage_by_year.csv',index=False)
    pd.concat(statuses).to_csv(out/'development_feature_coverage_by_status.csv',index=False)
    pd.concat(miss).to_csv(out/'development_feature_missingness.csv',index=False)
    daily=pd.concat(all_daily,ignore_index=True);quant=pd.concat(all_q,ignore_index=True)
    daily.to_csv(out/'daily_rank_ic.csv',index=False)
    quant.to_csv(out/'daily_quintiles.csv',index=False)
    summary=[];annual=[];phases=[];qs=[];spread=[]
    for feature,d in daily.groupby('feature',sort=False):
        for lag in (4,20):summary.append({'feature':feature,**summarize(d,lag)})
        for year,a in d.groupby(d.signal_date.dt.year):
            annual.append({'feature':feature,'year':year,**summarize(a,4)})
        for p in range(5):
            a=d.loc[d.td%5==p].copy();a['phase_td']=a.td//5
            phases.append({'feature':feature,'phase':p,**summarize(a,4,position='phase_td')})
        q=quant[quant.feature==feature]
        for bucket,a in q.groupby('quintile'):
            qs.append({'feature':feature,'quintile':bucket,'n_dates':len(a),'n_pairs':int(a.n_pairs.sum()),
                'mean_target':a.mean_target.mean(),'median_date_mean_target':a.mean_target.median()})
        pivot=q.pivot(index='signal_date',columns='quintile',values='mean_target')
        s=d[['signal_date','td']].copy().merge((pivot[5]-pivot[1]).rename('spread'),left_on='signal_date',right_index=True,how='left')
        s['feature']=feature;spread.append(s)
    pd.DataFrame(summary).to_csv(out/'ic_summary.csv',index=False)
    pd.DataFrame(annual).to_csv(out/'annual_ic.csv',index=False)
    pd.DataFrame(phases).to_csv(out/'nonoverlapping_phases.csv',index=False)
    pd.DataFrame(qs).to_csv(out/'quintile_summary.csv',index=False)
    sp=pd.concat(spread,ignore_index=True);sp.to_csv(out/'daily_quintile_spread.csv',index=False)
    ss=[];sa=[]
    for feature,s in sp.groupby('feature'):
        for lag in (4,20):ss.append({'feature':feature,**summarize(s,lag,value='spread')})
        for year,a in s.groupby(s.signal_date.dt.year):sa.append({'feature':feature,'year':year,**summarize(a,4,value='spread')})
    pd.DataFrame(ss).to_csv(out/'quintile_spread_summary.csv',index=False)
    pd.DataFrame(sa).to_csv(out/'annual_quintile_spread.csv',index=False)
    # Development feature redundancy uses ALL eligible features, no target mask.
    correlations=[]
    for a,b in itertools.combinations(FEATURES,2):
        row=c.execute(f"""SELECT avg(r),count(r),sum(n) FROM (SELECT signal_date,count(*) n,
            CASE WHEN count(*)>=30 THEN corr({a}_z,{b}_z) END r FROM f
            WHERE isfinite({a}_z) AND isfinite({b}_z) GROUP BY signal_date)""").fetchone()
        correlations.append({'feature_a':a,'feature_b':b,'mean_daily_correlation':row[0],'n_dates':row[1],'n_pairs':row[2]})
    pd.DataFrame(correlations).to_csv(out/'feature_correlations.csv',index=False)
    ip=daily.pivot(index='signal_date',columns='feature',values='ic')
    iccorr=[]
    for a,b in itertools.combinations(FEATURES,2):
        v=ip[[a,b]].dropna();iccorr.append({'feature_a':a,'feature_b':b,'ic_correlation':v[a].corr(v[b]),'n_dates':len(v)})
    pd.DataFrame(iccorr).to_csv(out/'ic_correlations.csv',index=False)
    report={**key_qa,'development_signal_dates':[START,END],'actual_signal_min':'1993-01-22',
        'cross_boundary_eligible':cross[0],'cross_boundary_numeric':cross[1],
        'calendar_rows':len(all_daily[0]),'calendar_index_mismatches':mismatch,
        'source_feature_hashes_verified':len(sm['final_files']),
        'holdout_signal_values_materialized':False,'holdout_predictive_diagnostics':False,
        'duplicate_or_key_difference_count':0,'all_quintile_pair_counts_reconciled':True,
        'all_feature_pair_counts_reconciled':True,'preprocessing_recomputed':False,
        'features_dropped_or_flipped':False,'horizons_constructed':[5],'qa_passed':True}
    manifest.update(report,sources=fingerprints,complete=True)
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    pd.DataFrame([{'check':k,'value':json.dumps(v)} for k,v in report.items()]).to_csv(out/'evaluation_qa.csv',index=False)
    c.close();print(json.dumps(report,indent=2),flush=True)
    figures(out)


def figures(out):
    import os
    os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'data/interim/stage2b/matplotlib'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    dest=ROOT/'results/figures/stage2b';dest.mkdir(parents=True,exist_ok=True)
    d=pd.read_csv(out/'daily_rank_ic.csv',parse_dates=['signal_date'])
    fig,axes=plt.subplots(4,2,figsize=(13,11),sharex=True)
    for ax,f in zip(axes.flat,FEATURES):
        v=d[d.feature==f].set_index('signal_date').ic.resample('ME').mean()
        ax.plot(v.index,v.values,lw=.8);ax.axhline(0,color='gray',lw=.6);ax.set_title(f);ax.set_ylabel('Monthly mean daily IC')
    fig.suptitle('Development 1993–2019: daily Rank IC, monthly display');fig.tight_layout();fig.savefig(dest/'rank_ic_time_series.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(4,2,figsize=(12,10))
    for ax,f in zip(axes.flat,FEATURES):
        ax.hist(d.loc[d.feature==f,'ic'].dropna(),bins=60,color='#387999');ax.axvline(0,color='black',lw=.7);ax.set_title(f);ax.set_xlabel('Daily Rank IC')
    fig.suptitle('Development 1993–2019: IC distributions');fig.tight_layout();fig.savefig(dest/'rank_ic_distribution.png',dpi=150);plt.close(fig)
    q=pd.read_csv(out/'quintile_summary.csv');fig,axes=plt.subplots(4,2,figsize=(12,10))
    for ax,f in zip(axes.flat,FEATURES):
        v=q[q.feature==f];ax.plot(v.quintile,100*v.mean_target,'o-');ax.axhline(0,color='gray',lw=.5);ax.set_title(f);ax.set_xticks(range(1,6));ax.set_xlabel('Tie-preserving feature quintile');ax.set_ylabel('Mean 5D target (%)')
    fig.suptitle('Development: equal-date conditional target means; not portfolio returns');fig.tight_layout();fig.savefig(dest/'quintile_monotonicity.png',dpi=150);plt.close(fig)
    for file,col,title in [('feature_correlations.csv','mean_daily_correlation','Mean daily eligible feature correlation'),('ic_correlations.csv','ic_correlation','Daily IC time-series correlation')]:
        matrix=np.eye(len(FEATURES));v=pd.read_csv(out/file)
        for row in v.to_dict('records'):
            i=FEATURES.index(row['feature_a']);j=FEATURES.index(row['feature_b']);matrix[i,j]=matrix[j,i]=row[col]
        fig,ax=plt.subplots(figsize=(10,8));im=ax.imshow(matrix,vmin=-1,vmax=1,cmap='RdBu_r');ax.set_xticks(range(8),FEATURES,rotation=50,ha='right');ax.set_yticks(range(8),FEATURES)
        for i in range(8):
            for j in range(8):ax.text(j,i,f'{matrix[i,j]:.2f}',ha='center',va='center',fontsize=8)
        ax.set_title('Development 1993–2019: '+title);fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(dest/file.replace('.csv','.png'),dpi=150);plt.close(fig)
    p=pd.read_csv(out/'nonoverlapping_phases.csv');s=pd.read_csv(out/'ic_summary.csv');fig,axes=plt.subplots(4,2,figsize=(12,10))
    for ax,f in zip(axes.flat,FEATURES):
        v=p[p.feature==f];ax.errorbar(v.phase,v['mean'],yerr=1.959963984540054*v.se,fmt='o',capsize=3)
        h=s[(s.feature==f)&(s.lag==4)].iloc[0];ax.axhline(h['mean'],label='All dates',color='orange');ax.axhline(0,color='gray',lw=.5);ax.set_xticks(range(5));ax.set_title(f);ax.set_xlabel('Fixed calendar phase');ax.set_ylabel('Mean IC / nominal 95% CI')
    fig.suptitle('Every-fifth-day phases: sampled HAC lag4; all-date reference');fig.tight_layout();fig.savefig(dest/'nonoverlapping_comparison.png',dpi=150);plt.close(fig)

if __name__=='__main__':run()
