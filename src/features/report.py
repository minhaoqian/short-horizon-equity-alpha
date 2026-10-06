"""Reproducible integrity/coverage/distribution QA; no target/performance evidence."""
from pathlib import Path
import csv
import json
import duckdb
import numpy as np
import pandas as pd
import os
os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[2]/'data/interim/stage2a_features/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .panel import ROOT,FOLDER,FEATURES


def csv_query(c,query,path):
    c.execute(f"COPY ({query}) TO '{path}' (HEADER,DELIMITER ',')")


def main():
    c=duckdb.connect();c.execute("SET threads=2; SET memory_limit='2GB'")
    c.execute(f"SET temp_directory='{FOLDER/'temp'}'")
    manifest=json.loads((FOLDER/'manifest.json').read_text());assert manifest['complete']
    c.execute(f"CREATE VIEW f AS SELECT * FROM read_parquet('{FOLDER/'parts/part_*.parquet'}')")
    c.execute(f"CREATE VIEW stats AS SELECT * FROM read_parquet('{FOLDER/'cross_section_stats.parquet'}')")
    n,unique,future=c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)),count(*) FILTER(WHERE max_input_date>signal_date) FROM f').fetchone()
    assert n==unique==6699101 and future==0
    # Regression-only historical corner keys; never used for construction,
    # admission scope, preprocessing or eligible-key selection.
    rights=json.loads((ROOT/'data/interim/stage2a_historical_qa/event_screen_counterexamples.json').read_text())
    rights_checked=0
    for case in rights:
        if case['eligible'] and case['daily_zero_effect_screen']:
            row=c.execute('SELECT gap_1_raw,reversal_5_raw,volatility_20_raw,distribution_event FROM f WHERE permno=? AND signal_date=?',
                [case['permno'],case['dlycaldt']]).fetchone()
            assert row is not None and row[:3]==(None,None,None) and row[3]
            rights_checked+=1
    assert rights_checked==2
    out=ROOT/'results/tables/stage2a';fig=ROOT/'results/figures/stage2a';fig.mkdir(parents=True,exist_ok=True)
    coverage=[];missing=[];summaries=[];preprocessing=[];dispersion=[];checks=[]
    for feature in FEATURES:
        raw=feature+'_raw';clip=feature+'_clipped';z=feature+'_z';reason=feature+'_reason'
        invalid=c.execute(f'''SELECT count(*) FROM f WHERE ({raw} IS NOT NULL AND NOT isfinite({raw}))
            OR ({clip} IS NOT NULL AND NOT isfinite({clip})) OR ({z} IS NOT NULL AND NOT isfinite({z}))
            OR ({raw} IS NULL AND ({reason} IS NULL OR {reason}='observed'))
            OR ({raw} IS NULL AND ({clip} IS NOT NULL OR {z} IS NOT NULL))''').fetchone()[0]
        assert invalid==0,(feature,invalid)
        coverage.append(f'''SELECT '{feature}' feature,year(signal_date) AS year,count(*) eligible_keys,
            count({raw}) raw_observed,count({z}) standardized_observed,
            100.0*count({raw})/count(*) raw_coverage_pct,100.0*count({z})/count(*) standardized_coverage_pct FROM f GROUP BY 2''')
        missing.append(f"SELECT '{feature}' feature,{reason} reason,count(*) observations FROM f GROUP BY 2")
        for version,col in [('raw',raw),('clipped',clip),('standardized',z)]:
            summaries.append(f'''SELECT '{feature}' feature,'{version}' AS version,count({col}) n,avg({col}) mean,stddev_pop({col}) sd,
              min({col}) min,quantile_cont({col},.01) p01,quantile_cont({col},.5) median,quantile_cont({col},.99) p99,max({col}) max FROM f''')
        c.execute(f'''CREATE TABLE qa_{feature} AS SELECT f.signal_date,count({raw}) raw_n,count({z}) z_n,
            avg({z}) z_mean,stddev_pop({z}) z_sd,min({clip}) clip_min,max({clip}) clip_max,
            sum(({clip}<>{raw})::INT) clipped_n FROM f GROUP BY 1''')
        statsq=f"SELECT * FROM stats WHERE feature='{feature}'"
        qa=f'qa_{feature}'
        error,sd_error,clip_error,count_error=c.execute(f'''SELECT max(abs(z_mean)),max(abs(z_sd-1)) FILTER(WHERE s.sd>0),
            count(*) FILTER(WHERE clip_min<s.lo-1e-10 OR clip_max>s.hi+1e-10),
            count(*) FILTER(WHERE (coalesce(s.n,0)<30 AND z_n<>0) OR (s.n>=30 AND z_n<>raw_n))
            FROM {qa} q LEFT JOIN ({statsq}) s USING(signal_date)''').fetchone()
        assert (error or 0)<1e-10 and (sd_error or 0)<1e-10 and clip_error==count_error==0,(feature,error,sd_error,clip_error,count_error)
        checks.append({'feature':feature,'nonfinite_or_reason_violations':invalid,'max_abs_z_mean':error,
            'max_abs_z_sd_minus_one':sd_error,'clipping_violations':clip_error,'preprocessing_count_violations':count_error})
        preprocessing.append(f'''SELECT '{feature}' feature,q.*,s.lo,s.hi,s.mu clipped_mean,s.sd clipped_sd,
            CASE WHEN raw_n>0 THEN clipped_n::DOUBLE/raw_n END clipped_fraction FROM {qa} q LEFT JOIN ({statsq}) s USING(signal_date)''')
        dispersion.append(f"SELECT '{feature}' feature,signal_date,count({raw}) n,stddev_pop({raw}) raw_population_sd FROM f GROUP BY 2")
        print('integrity/preprocessing QA passed: '+feature,flush=True)
    for filename,queries in [('coverage_by_year.csv',coverage),('missingness_reasons.csv',missing),('distribution_summary.csv',summaries),
        ('preprocessing_diagnostics.csv',preprocessing),('cross_sectional_dispersion.csv',dispersion)]:
        csv_query(c,' UNION ALL '.join(queries),out/filename)
    with (out/'feature_definitions.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['feature','definition','window','missing_rule'])
        definitions=[('reversal_5','1-product(1+r)','t-4:t','5/5 admitted'),
            ('momentum_60_skip5','product(1+r)-1','t-59:t-5','55/55 admitted'),
            ('volatility_20','sample standard deviation','t-19:t','20/20 admitted'),
            ('turnover_20','log1p(mean(P*V/(1000*DlyCap)))','t-19:t','15/20 valid'),
            ('dollar_liquidity_20','log1p(mean(P*V))','t-19:t','15/20 valid'),
            ('volume_shock_20','log1p(P_t*V_t)-log1p(prior mean(P*V))','t-20:t-1 denominator','15/20 prior plus valid current'),
            ('gap_1','observed open_t / observed close_previous_market_date - 1','adjacent event-free interval','positive actual prices; no fallback'),
            ('intraday_1','observed close_t / observed open_t - 1','current day','positive actual prices')]
        w.writerows(definitions)
    # Equal-date pairwise feature correlations only, never a target join.
    correlations=[];matrix=np.eye(8)
    for i,left in enumerate(FEATURES):
        for j in range(i+1,len(FEATURES)):
            right=FEATURES[j]
            mean,dates,pairs=c.execute(f'''SELECT avg(rho),count(rho),sum(n) FILTER(WHERE rho IS NOT NULL AND isfinite(rho)) FROM
                (SELECT signal_date,count(*) n,CASE WHEN stddev_pop({left}_z)>0 AND stddev_pop({right}_z)>0
                  THEN corr({left}_z,{right}_z) END rho FROM f WHERE {left}_z IS NOT NULL AND {right}_z IS NOT NULL GROUP BY 1 HAVING count(*)>=2)
                WHERE rho IS NULL OR isfinite(rho)''').fetchone()
            correlations.append([left,right,mean,dates,pairs]);matrix[i,j]=matrix[j,i]=mean if mean is not None else np.nan
    with (out/'correlation_after_preprocessing.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['left_feature','right_feature','equal_date_mean_pearson','valid_dates','pair_observations']);w.writerows(correlations)
    print('descriptive feature correlations completed; no target correlation',flush=True)
    coverage_frame=pd.read_csv(out/'coverage_by_year.csv')
    heat=coverage_frame.pivot(index='feature',columns='year',values='raw_coverage_pct').reindex(FEATURES)
    fig1,ax=plt.subplots(figsize=(13,5),layout='constrained');im=ax.imshow(heat,aspect='auto',vmin=0,vmax=100,cmap='viridis')
    ax.set_yticks(range(8),FEATURES);ax.set_xticks(range(0,len(heat.columns),4),list(heat.columns)[::4]);ax.set_title('Stage 2A: raw-feature coverage (% of all eligible keys)')
    fig1.colorbar(im,ax=ax,label='%');fig1.savefig(fig/'annual_feature_coverage.png',dpi=160);plt.close(fig1)
    fig2,ax=plt.subplots(figsize=(10,8),layout='constrained');im=ax.imshow(matrix,vmin=-1,vmax=1,cmap='RdBu_r')
    ax.set_xticks(range(8),FEATURES,rotation=45,ha='right');ax.set_yticks(range(8),FEATURES)
    for i in range(8):
        for j in range(8):ax.text(j,i,f'{matrix[i,j]:.2f}',ha='center',va='center',fontsize=9)
    ax.set_title('Equal-date average pairwise feature correlations (descriptive)');fig2.colorbar(im,ax=ax);fig2.savefig(fig/'feature_correlation.png',dpi=160);plt.close(fig2)
    print('Rendering cached dispersion aggregates',flush=True)
    dispersion_frame=pd.read_csv(out/'cross_sectional_dispersion.csv',parse_dates=['signal_date'])
    fig3,axes=plt.subplots(4,2,figsize=(12,10),layout='constrained')
    for ax,feature in zip(axes.flat,FEATURES):
        frame=dispersion_frame[dispersion_frame.feature==feature].copy()
        frame['month']=frame.signal_date.dt.to_period('M').dt.to_timestamp()
        monthly=frame.groupby('month').raw_population_sd.median().sort_index()
        ax.plot(monthly.index,monthly.values,linewidth=.8);ax.set_title(feature);ax.set_ylabel('Raw cross-sectional SD')
    fig3.suptitle('Monthly median of daily raw cross-sectional dispersion; no outcomes');fig3.savefig(fig/'raw_dispersion.png',dpi=160);plt.close(fig3)
    print('Dispersion figure completed',flush=True)
    # Fixed calendar-based selection, with counts; no performance-based choice.
    chosen=c.execute('''SELECT year(signal_date) AS year,min(signal_date) AS d FROM f
        WHERE month(signal_date)=6 AND year(signal_date) IN (2000,2010,2020,2025) GROUP BY 1 ORDER BY 1''').fetchall()
    representatives={year:c.execute('SELECT '+','.join(f'{x}_z' for x in FEATURES)+' FROM f WHERE signal_date=?',[d]).fetchnumpy() for year,d in chosen}
    print('Representative dates loaded',flush=True)
    fig4,axes=plt.subplots(4,2,figsize=(12,10),layout='constrained')
    for ax,feature in zip(axes.flat,FEATURES):
        for year,d in chosen:
            values=representatives[year][feature+'_z']
            vals=values.compressed() if np.ma.isMaskedArray(values) else values[np.isfinite(values)]
            if len(vals):ax.hist(vals,bins=35,histtype='step',density=True,label=f'{year}: n={len(vals)}')
        ax.set_title(feature);ax.set_xlabel('Same-date clipped z-score');ax.legend(fontsize=7)
    fig4.suptitle('First June market date in 2000 / 2010 / 2020 / 2025');fig4.savefig(fig/'representative_distributions.png',dpi=160);plt.close(fig4)
    summary=[]
    for feature in FEATURES:
        a,b,timing=c.execute(f"SELECT count({feature}_raw),count({feature}_z),count(*) FILTER(WHERE {feature}_reason='timing_ambiguous') FROM f").fetchone()
        summary.append({'feature':feature,'raw_count':a,'standardized_count':b,'raw_coverage_pct':100*a/n,
            'standardized_coverage_pct':100*b/n,'timing_ambiguous_feature_keys':timing})
    # Explicit source-feature masks can become available through t, never outcome masks.
    manifest.update(qa_passed=True,qa={'rows':n,'unique_keys':unique,'future_input_violations':future,'rights_corner_regressions':rights_checked,'checks':checks},
        coverage=summary,figure_dates=[str(d) for _,d in chosen],correlations_role='descriptive feature-to-feature only',
        neutralization='deferred',missing_value_treatment='no fill; raw/clipped/z and explicit reasons')
    (FOLDER/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'rows':n,'qa_passed':True,'coverage':summary},indent=2),flush=True)

if __name__=='__main__':main()
