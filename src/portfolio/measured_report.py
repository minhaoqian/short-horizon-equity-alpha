"""Coverage-qualified conditional components; no synthetic wealth path or selection."""
import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .reservation_sources import ROOT, digest
from .reservation_audit import CANDIDATES
from .measured_components import qualified_hac, SD_LABEL, HAC_LABEL

TITLE='Conditional simulation under a generalized unresolved-position reservation convention'
DISCLAIMER='Full-account wealth unidentified; reserves are budget proxies; no candidate selection.'


def coverage_summary(g):
    denominator=int(g.asset_intervals.sum())
    basis=float(g.verified_entry_basis_denominator.sum())
    return dict(calendar_dates=len(g),numeric_dates=int(g.net.notna().sum()),
        asset_intervals=denominator,identified_asset_intervals=int(g.identified_asset_intervals.sum()),
        asset_interval_coverage=g.identified_asset_intervals.sum()/denominator if denominator else 1.,
        complete_component_interval_coverage=g.complete_component_intervals.sum()/denominator if denominator else 1.,
        verified_entry_basis_coverage=g.identified_entry_basis.sum()/basis if basis else 1.,
        asset_coverage_min=float(g.asset_coverage.min()),asset_coverage_end=float(g.asset_coverage.iloc[-1]),
        unresolved_positions_end=int(g.unresolved_positions.iloc[-1]),
        unresolved_queued_executions_end=int(g.unresolved_queued_execution_count.iloc[-1]),
        executed_basis_reserve_end=float(g.verified_executed_reserve_long.iloc[-1]+g.verified_executed_reserve_short.iloc[-1]),
        planned_proxy_reserve_end=float(g.unresolved_queued_proxy_commitment.iloc[-1]),
        newly_identified_fixed_cash_claims=int(g.newly_established_fixed_claims.sum()),
        signed_fixed_entitlement_dollars=float(g.signed_fixed_entitlement_dollars.sum()),
        unknown_asset_claim_residual_bundles_end=int(g.unresolved_positions.iloc[-1]),
        raw_reserve_fraction_end=float(g.raw_reserve_fraction.iloc[-1]),
        paired_budget_reserve_fraction_end=float(g.paired_budget_reserve_fraction.iloc[-1]),
        raw_reserve_fraction_mean=float(g.raw_reserve_fraction.mean()),
        unmatched_side_allowance_end=float(g.structural_matched_side_idle.iloc[-1]),
        unknown_short_borrow_bases_end=int(g.unknown_short_borrow_basis_count.iloc[-1]),
        unknown_exit_execution_cost_obligations_end=int(g.unresolved_positions.iloc[-1]),
        market_value_fraction_identified='UNAVAILABLE',full_account_wealth_identified=False,
        reference_budget_is_wealth=False,candidate_selection_permitted=False,
        reporting_scope=TITLE)


def validate_journal(c, path, daily):
    pattern=str(path/'journal_*.parquet')
    n,unique,bad=c.execute(f"""SELECT count(*),count(DISTINCT(key,date,kind,reason,event_sequence)),
        count(*) FILTER(WHERE amount IS NOT NULL AND NOT isfinite(amount))
        FROM read_parquet('{pattern}')""").fetchone()
    assert n==unique and bad==0,'Duplicate or nonfinite primitive journal'
    d=c.execute(f"""SELECT date,
        count(*) FILTER(WHERE amount IS NULL) unknown_count,
        count(*) FILTER(WHERE amount IS NOT NULL) identified_count,
        sum(amount) net,
        sum(amount) FILTER(WHERE kind='gross') gross,
        sum(amount) FILTER(WHERE kind='fixed') fixed,
        sum(amount) FILTER(WHERE kind='impact') impact,
        sum(amount) FILTER(WHERE kind='borrow') borrow
        FROM read_parquet('{pattern}') GROUP BY date ORDER BY date""").fetchdf()
    d['date']=d.date.dt.date;d=d.set_index('date')
    f=daily.set_index('date')
    assert set(d.index)==set(f.index)
    for kind in ('net','gross','fixed','impact','borrow'):
        # No primitive in an economic scope means verified structural absence;
        # SQL empty sum null is compared to declared 0 only with zero count.
        for day in f.index:
            val=d.loc[day,kind]; expected=f.loc[day,kind]
            count=f.loc[day,kind+'_identified_count']+f.loc[day,kind+'_unknown_count']
            if kind!='net' and count==0:assert expected==0
            elif pd.isna(expected):assert pd.isna(val)
            else:np.testing.assert_allclose(val,expected,atol=1e-6,rtol=1e-11)
    assert (d.unknown_count.to_numpy()==f.net_unknown_count.to_numpy()).all()
    # Closed, entirely measured lifecycles must telescope to signed terminal
    # cash/market wealth minus executed entry principal plus separate claims.
    # This is an accounting identity, not completed-cohort performance reporting.
    frozen=ROOT/'data/interim/stage4f/development'/path.name
    lifecycles=c.execute(f"""WITH a AS (
        SELECT key,sum(amount) FILTER(WHERE kind='gross') gross,
        sum(amount) FILTER(WHERE kind='gross' AND reason='established_prior_owned_basis_entitlement') claims,
        count(*) FILTER(WHERE kind='gross' AND amount IS NULL) unknown_gross,
        max(execution_notional) FILTER(WHERE kind='fixed' AND reason='verified_exit') exit_notional
        FROM read_parquet('{pattern}') GROUP BY key),
        e AS (SELECT key,state,side,entry_notional
        FROM read_parquet('{frozen}/terminal_states_*.parquet',union_by_name=true)
        WHERE state IN ('assumed_exited','measurable_cash_termination'))
        SELECT count(*),max(abs(a.gross - (coalesce(a.claims,0) +
        (CASE WHEN side='long' THEN 1 ELSE -1 END) *
        (CASE WHEN state='assumed_exited' THEN a.exit_notional ELSE 0 END - e.entry_notional))))
        FROM a JOIN e USING(key) WHERE unknown_gross=0""").fetchone()
    assert lifecycles[0]>0 and lifecycles[1]<1e-6,('Lifecycle identity',lifecycles)
    return dict(primitive_rows=n,unique_primitives=unique,nonfinite_amounts=bad,
                primitive_aggregate_reconciliation=True,
                wholly_identified_closed_lifecycles=int(lifecycles[0]),
                maximum_lifecycle_accounting_error=float(lifecycles[1]))


def report():
    private=ROOT/'data/interim/stage4g/development'
    manifest=json.loads((private/'manifest.json').read_text());assert manifest['qa_passed']
    tables=ROOT/'results/tables/stage4g';tables.mkdir(parents=True,exist_ok=True)
    figures=ROOT/'results/figures/stage4g';figures.mkdir(parents=True,exist_ok=True)
    c=duckdb.connect();c.execute('SET threads=2')
    daily=[];qa={}
    for candidate in CANDIDATES:
        path=private/candidate;d=pd.read_parquet(path/'daily_contributions.parquet')
        assert len(d)==4278 and not d.date.duplicated().any()
        assert d.date.min().isoformat()=='2003-01-03' and d.date.max().isoformat()=='2019-12-31'
        qa[candidate]=validate_journal(c,path,d)
        cash=c.execute(f"SELECT date,sum(amount) signed_fixed_entitlement_dollars,count(*) identified_fixed_claim_count FROM read_parquet('{path}/journal_*.parquet') WHERE reason='established_prior_owned_basis_entitlement' GROUP BY date").fetchdf()
        cash['date']=cash.date.dt.date
        d=d.merge(cash,on='date',how='left',validate='one_to_one')
        # These are certified absent postings on dates without claim journal rows,
        # never substitutions for an unknown asset/claim bundle.
        no_claim=d.identified_fixed_claim_count.isna()
        d.loc[no_claim,['signed_fixed_entitlement_dollars','identified_fixed_claim_count']]=0
        assert (d.identified_fixed_claim_count==d.newly_established_fixed_claims).all()
        d['unknown_asset_claim_residual_count']=d.unresolved_positions
        d['unknown_claim_residual_count_is_bundle_proxy']=True
        d['unknown_exit_cost_obligation_count']=d.unresolved_positions
        d['unknown_full_account_residual']=(d.net_unknown_count>0)|(d.unresolved_positions>0)
        d['full_period_account_wealth_identified']=False
        d['execution_cost_count_coverage']=(d.fixed_identified_count+d.impact_identified_count)/(d.fixed_identified_count+d.impact_identified_count+d.fixed_unknown_count+d.impact_unknown_count).replace(0,np.nan)
        daily.append(d)
    c.close();all_daily=pd.concat(daily,ignore_index=True)
    # Large pure aggregate paths are reproducible/local; no security-level rows
    # or licensed quotations are exported to public result files.
    all_daily.to_csv(tables/'daily_component_contributions.csv',index=False)
    annual=[];summaries=[];hac=[];costs=[];turnover=[];coverage=[]
    def stats(g):
        r=g.conditional_measured_component_return
        return dict(conditional_daily_mean=float(r.mean()),conditional_daily_sample_sd=float(r.std(ddof=1)),
            annualized_conditional_mean_252=float(252*r.mean()),
            annualized_conditional_sd=float(np.sqrt(252)*r.std(ddof=1)),
            annualized_sd_label=SD_LABEL,denominator=10000000,
            contribution_label='conditional measured-component return')
    for candidate,d in zip(CANDIDATES,daily):
        cov=coverage_summary(d);s=dict(candidate=candidate,**stats(d),**cov)
        for kind in ('gross','fixed','impact','borrow','net'):
            s[kind+'_identified_dollars']=float(d[kind].sum(min_count=1))
            s[kind+'_identified_components']=int(d[kind+'_identified_count'].sum())
            s[kind+'_unknown_components']=int(d[kind+'_unknown_count'].sum())
        summaries.append(s)
        for lag in (20,4):
            hac.append({**qualified_hac(d.conditional_measured_component_return,lag,cov),'candidate':candidate})
        for year,g in d.groupby('year',sort=True):
            cv=coverage_summary(g)
            a=dict(candidate=candidate,year=int(year),**stats(g),**cv)
            for kind in ('gross','fixed','impact','borrow','net'):
                a[kind+'_identified_dollars']=float(g[kind].sum(min_count=1))
                a[kind+'_identified_dollars_over_reference']=a[kind+'_identified_dollars']/10000000
                a[kind+'_unknown_primitive_count']=int(g[kind+'_unknown_count'].sum())
                a[kind+'_numeric_dates']=int(g[kind].notna().sum())
            annual.append(a);coverage.append(dict(candidate=candidate,year=int(year),**cv))
            costs.append(dict(candidate=candidate,year=int(year),**cv,
                fixed_identified_dollars=float(g.fixed.sum(min_count=1)),
                impact_identified_dollars=float(g.impact.sum(min_count=1)),
                borrow_identified_dollars=float(g.borrow.sum(min_count=1)),
                known_fixed_primitives=int(g.fixed_identified_count.sum()),unknown_fixed_primitives=int(g.fixed_unknown_count.sum()),
                known_impact_primitives=int(g.impact_identified_count.sum()),unknown_impact_primitives=int(g.impact_unknown_count.sum()),
                known_borrow_primitives=int(g.borrow_identified_count.sum()),unknown_borrow_primitives=int(g.borrow_unknown_count.sum()),
                wholly_measured_cost_dates=int(((g.fixed_unknown_count==0)&(g.impact_unknown_count==0)&(g.borrow_unknown_count==0)).sum()),
                baseline_linear_bp=6,impact_coefficient=.10,borrow_annual_bp=100,financing_drag=0))
            turnover.append(dict(candidate=candidate,year=int(year),**cv,
                verified_execution_count=int(g.verified_execution_count.sum()),
                verified_execution_notional=float(g.verified_execution_notional.sum()),
                verified_turnover=float(g.verified_turnover.sum()),
                conventional_one_way_turnover=float(g.conventional_one_way_turnover.sum()),
                unknown_execution_quantities_end=int(g.unresolved_queued_execution_count.iloc[-1]),
                proxies_in_turnover=False))
    for name,records in [('annual_component_summary',annual),('conditional_mean_hac',hac),
                         ('descriptive_candidate_comparison',summaries),('daily_annual_coverage',coverage),
                         ('cost_borrow_decomposition',costs),('verified_turnover',turnover)]:
        pd.DataFrame(records).to_csv(tables/(name+'.csv'),index=False)
    pd.DataFrame([dict(candidate=candidate,**qa[candidate],**coverage_summary(d)) for candidate,d in zip(CANDIDATES,daily)]).to_csv(tables/'accounting_qa.csv',index=False)
    strict=pd.DataFrame([
        ('4A','Strict identification failed','2003-01-13',7,4279,'Unidentified scheduled exit; no complete ledger'),
        ('4B','Five-date fallback failed','2003-03-31',60,4279,'Unidentified received inventory'),
        ('4C','Legal entitlement recovered only',None,None,4279,'0.535 economic ratio; delivery/cash method not established'),
        ('4D','Historical settlement identification unresolved',None,None,4279,'Delivery D and issuer method M unidentified; branch closed'),
        ('4E','All hypothetical cases halt at second event','2003-04-16',72,4279,'D0/D2/D5 retained equally; not historical settlement'),
        ('4F','Reference-budget continuation feasible',None,4279,4279,'Full wealth unknown; reserve not value/funding/solvency')],
        columns=['stage','finding','halt_date','operational_dates','original_development_dates','limitation'])
    strict['performance_scope']=TITLE;strict.to_csv(tables/'strict_findings.csv',index=False)
    plot(daily,pd.DataFrame(annual),figures)
    output_hashes={str(p.relative_to(ROOT)):digest(p) for folder in (tables,figures) for p in folder.iterdir() if p.is_file() and p.name!='report_manifest.json'}
    report_manifest=dict(qa_passed=True,journal_qa=qa,reporting_dates_per_candidate=4278,
        original_eligible_development_keys=3829908,original_decision_dates=4279,
        full_account_wealth_identified=False,market_value_coverage_unavailable=True,
        performance_scope=TITLE,sd_label=SD_LABEL,hac_label=HAC_LABEL,
        unknowns_imputed=False,sharpe_nav_drawdown_or_selection_computed=False,
        holdout_outcomes_read=False,baseline_only=True,output_hashes=output_hashes,
        source_manifest_sha256=digest(private/'manifest.json'),
        source_daily_sha256={candidate:digest(private/candidate/'daily_contributions.parquet') for candidate in CANDIDATES})
    (tables/'report_manifest.json').write_text(json.dumps(report_manifest,indent=2)+'\n')
    return summaries


def plot(daily,annual,folder):
    colors=['#245b8a','#cf7f2f'];labels=['Reversal','Ridge']
    plt.rcParams.update({'font.size':9,'figure.dpi':140})
    fig,axs=plt.subplots(4,1,figsize=(12,12),sharex=True)
    for d,col,label in zip(daily,colors,labels):
        x=pd.to_datetime(d.date)
        axs[0].plot(x,d.conditional_measured_component_return*1e4,color=col,lw=.45,alpha=.65,label=label)
        axs[1].plot(x,d.asset_coverage,color=col,label=label)
        axs[2].plot(x,d.raw_reserve_fraction,color=col,label=label+' raw reserve/N')
        axs[2].plot(x,d.paired_budget_reserve_fraction,color=col,ls='--',label=label+' paired-budget reserve/N')
        axs[3].plot(x,d.unknown_short_borrow_basis_count,color=col,label=label+' unknown short bases')
    axs[0].set_xlim(pd.Timestamp('2003-01-03'),pd.Timestamp('2019-12-31'))
    axs[0].set_ylabel('Conditional daily\ncontribution / N (bp)')
    axs[1].set_ylabel('Identified asset-interval\ncount fraction')
    axs[2].set_ylabel('Budget proxies / N\n(not wealth)');axs[3].set_ylabel('Unknown borrow bases')
    for ax in axs:ax.legend(loc='upper left',fontsize=8);ax.grid(alpha=.2)
    fig.suptitle(TITLE+'\nStrict 4A/4B/4E failures retained; full-account wealth remains unidentified',fontsize=11)
    fig.text(.02,.01,DISCLAIMER+' No holdout outcomes; all 4,278 reporting dates retained.',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.94));fig.savefig(folder/'daily_components_coverage.png');plt.close(fig)
    fig,axs=plt.subplots(3,2,figsize=(13,10),sharex='col')
    for j,(candidate,label) in enumerate(zip(CANDIDATES,labels)):
        a=annual.loc[annual.candidate==candidate]
        for kind,col in [('gross','#245b8a'),('fixed','#cf7f2f'),('impact','#bd4b4b'),('borrow','#6e6194')]:
            axs[0,j].plot(a.year,a[kind+'_identified_dollars']/1e6,'o-',label=kind,color=col)
        axs[0,j].plot(a.year,a.net_identified_dollars/1e6,'k--',label='identified net subtotal')
        axs[0,j].set_title(label);axs[0,j].set_ylabel('Identified dollars (million)')
        axs[1,j].plot(a.year,a.asset_interval_coverage,'o-',label='asset-interval count coverage')
        axs[1,j].plot(a.year,a.complete_component_interval_coverage,'s--',label='complete-component count coverage')
        axs[1,j].set_ylabel('Ratio of annual counts')
        axs[2,j].plot(a.year,a.raw_reserve_fraction_end,'o-',label='year-end raw proxy/N')
        axs[2,j].plot(a.year,a.paired_budget_reserve_fraction_end,'s--',label='year-end paired proxy/N')
        axs[2,j].set_ylabel('Deployment proxies / N');axs[2,j].set_xlabel('Calendar year')
        for ax in axs[:,j]:ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.suptitle('Identified annual subtotals with measurement coverage and reference commitments\n'+DISCLAIMER,fontsize=11)
    fig.tight_layout(rect=(0,0,1,.93));fig.savefig(folder/'annual_components_coverage.png');plt.close(fig)
    fig,axs=plt.subplots(3,1,figsize=(12,9),sharex=True)
    for d,col,label in zip(daily,colors,labels):
        x=pd.to_datetime(d.date)
        axs[0].plot(x,d.verified_turnover,color=col,lw=.5,label=label)
        denom=d.impact_identified_count+d.impact_unknown_count
        fraction=d.impact_identified_count/denom.where(denom>0)
        axs[1].plot(x,fraction,color=col,lw=.6,label=label)
        axs[2].plot(x,d.asset_coverage,color=col,label=label+' asset count fraction')
        axs[2].plot(x,d.raw_reserve_fraction,color=col,ls='--',label=label+' reserve proxy/N')
    axs[0].set_xlim(pd.Timestamp('2003-01-03'),pd.Timestamp('2019-12-31'))
    axs[0].set_ylabel('Verified traded notional / N\n(both legs; no netting)')
    axs[1].set_ylabel('Known impact primitives /\nrequired impact primitives')
    axs[2].set_ylabel('Coverage and budget proxy')
    for ax in axs:ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Verified turnover, cost availability and measurement coverage\n'+DISCLAIMER,fontsize=11)
    fig.tight_layout(rect=(0,0,1,.92));fig.savefig(folder/'turnover_cost_coverage.png');plt.close(fig)
    fig,axs=plt.subplots(3,2,figsize=(13,10),sharex='col')
    for j,(d,col,label) in enumerate(zip(daily,colors,labels)):
        groups=list(d.groupby('year'))
        axs[0,j].boxplot([g.conditional_measured_component_return.dropna()*1e4 for _,g in groups],
                        tick_labels=[str(y) for y,_ in groups],showfliers=True,
                        flierprops={'markersize':1,'alpha':.4})
        axs[0,j].set_title(label);axs[0,j].set_ylabel('Conditional daily contribution / N (bp)')
        axs[1,j].plot(range(1,18),[g.identified_asset_intervals.sum()/g.asset_intervals.sum() for _,g in groups],color=col)
        axs[1,j].set_ylabel('Asset-interval count coverage')
        axs[2,j].plot(range(1,18),[g.raw_reserve_fraction.iloc[-1] for _,g in groups],color=col)
        axs[2,j].set_ylabel('Year-end raw proxy / N');axs[2,j].tick_params(axis='x',rotation=70)
        for ax in axs[:,j]:ax.grid(alpha=.2)
    fig.suptitle('Fixed-calendar-year conditional contribution distributions with coverage\n'+DISCLAIMER,fontsize=11)
    fig.tight_layout(rect=(0,0,1,.93));fig.savefig(folder/'contribution_distribution_coverage.png');plt.close(fig)
