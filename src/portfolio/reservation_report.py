"""Aggregate reservation/measurement evidence; never strategy performance."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/stage4f-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .reservation_sources import ROOT


def report(scope='development'):
    private=ROOT/'data/interim/stage4f'/scope
    assert json.loads((private/'manifest.json').read_text()).get('qa_passed') is True, 'Incomplete audit cannot produce certified full-panel reports'
    tables=ROOT/'results/tables/stage4f';figures=ROOT/'results/figures/stage4f'
    tables.mkdir(parents=True,exist_ok=True);figures.mkdir(parents=True,exist_ok=True)
    summaries=[];days=[];phases=[];annual=[];categories=[];over=[];durations=[];costs=[]
    for candidate in ('uni_reversal_5','ridge'):
        base=private/candidate
        summary=json.loads((base/'manifest.json').read_text());summaries.append(summary)
        d=pd.read_parquet(base/'daily_coverage.parquet');days.append(d)
        p=pd.read_parquet(base/'phase_budget_path.parquet');phases.append(p)
        events=pd.read_parquet(base/'quarantine_events.parquet')
        for reason,g in events.groupby(['reason','side']):
            categories.append(dict(candidate=candidate,reason=reason[0],side=reason[1],positions=len(g),
                securities=g.permno.nunique(),security_events=g[['permno','quarantine_date']].drop_duplicates().shape[0]))
        elapsed=(pd.Timestamp(summary.get('end_date','2019-12-31'))-pd.to_datetime(events.quarantine_date)).dt.days
        durations.append(dict(candidate=candidate,unresolved_positions=len(events),all_durations_right_censored=True,
            minimum_calendar_days=int(elapsed.min()),median_calendar_days=float(elapsed.median()),maximum_calendar_days=int(elapsed.max())))
        for year,g in d.groupby('year'):
            last=g.iloc[-1]
            annual.append(dict(candidate=candidate,year=year,decision_dates=len(g),eligible_keys=int(g.eligible_keys.sum()),
                end_unresolved_positions=int(last.unresolved_positions),end_longs=int(last.unresolved_longs),end_shorts=int(last.unresolved_shorts),
                end_reserved_long=last.reserved_long,end_reserved_short=last.reserved_short,
                end_raw_reserve_over_N=last.raw_reserve_fraction,end_paired_reserve_over_N=last.paired_budget_reserve_fraction,
                mean_raw_reserve_over_N=g.raw_reserve_fraction.mean(),mean_paired_reserve_over_N=g.paired_budget_reserve_fraction.mean(),
                end_undeployed_matched_side_allowance=last.structural_matched_side_idle,
                new_deployment_date_fraction=g.reference_permits_new_paired_deployment.mean(),
                intervals=int(g.component_intervals.sum()),wealth_measurable_fraction=g.wealth_measurable_intervals.sum()/g.component_intervals.sum(),
                expense_input_measurable_fraction=g.expense_inputs_measurable_intervals.sum()/g.component_intervals.sum(),
                complete_measurable_fraction=g.fully_measurable_intervals.sum()/g.component_intervals.sum(),
                identified_entry_basis_fraction=g.identified_wealth_entry_basis.sum()/g.interval_entry_basis_denominator.sum(),
                reference_exhaustion_is_insolvency=False))
        o=pd.read_parquet(base/'opening_overcommitments.parquet');o['year']=pd.to_datetime(o.date).dt.year
        for year,g in o.groupby('year'):
            over.append(dict(candidate=candidate,year=year,side_dates=len(g),dates=g.date.nunique(),
                queued_increment_side_dates=int(((g.queued_increment>1e-8)&g.queued_orders_honored).sum()),
                max_overcommitment=g.overcommitment.max(),max_queued_increment=g.queued_increment.max()))
        for f in sorted(base.glob('execution_inputs_*.parquet')):
            x=pd.read_parquet(f)
            for leg,g in x.groupby('leg'):
                costs.append(dict(candidate=candidate,year=int(f.stem.split('_')[-1]),leg=leg,executions=len(g),
                    measured_cost_input_count=int(g.cost_inputs_measured.sum()),measured_cost_input_fraction=g.cost_inputs_measured.mean()))
        # Durable terminal journal plus final live states covers every submitted key.
        states=pd.concat([pd.read_parquet(f) for f in sorted(base.glob('terminal_states_*.parquet'))],ignore_index=True)
        remaining=pd.concat([pd.read_parquet(base/f) for f in ('final_verified_inventory.parquet','final_pending_orders.parquet')],ignore_index=True)
        assert not states.key.duplicated().any()
        assert not set(states.key)&set(remaining.key)
        assert len(states)+len(remaining)==summary['submitted']
        assert len(states[states.state.isin(['corporate_action_unresolved','exit_execution_unresolved'])])==len(events)
        assert np.allclose(d.reserved_long+d.reserved_short,d.raw_reserve_fraction*1e7)
        grouped=p.groupby('date').paired_reserve.sum()
        assert np.allclose(grouped.to_numpy()/1e7,d.paired_budget_reserve_fraction)
    def save(name,rows):pd.DataFrame(rows).to_csv(tables/f'{name}.csv',index=False)
    flat=[{k:v for k,v in s.items() if not isinstance(v,dict)} for s in summaries]
    save('feasibility_summary',flat);save('annual_reservation_coverage',annual)
    save('quarantine_categories',categories);save('opening_overcommitments_annual',over)
    save('unresolved_duration_summary',durations);save('execution_input_coverage',costs)
    daily=pd.concat(days,ignore_index=True);daily.to_csv(tables/'daily_reservation_coverage.csv',index=False)
    phase=pd.concat(phases,ignore_index=True);phase.to_csv(tables/'phase_reservation_path.csv',index=False)
    endpoints=[]
    for (candidate,ph),g in phase.groupby(['candidate','phase']):
        last=g.iloc[-1];ex=g[g.reference_deployment_exhausted]
        endpoints.append(dict(candidate=candidate,phase=ph,end_reserved_long=last.reserved_long,end_reserved_short=last.reserved_short,
            end_paired_reserve=last.paired_reserve,end_structural_allowance=last.structural_paired_allowance,
            first_reference_exhaustion_date=ex.date.iloc[0] if len(ex) else None,reference_exhaustion_is_insolvency=False))
    save('phase_end_state',endpoints)
    fig,axes=plt.subplots(3,2,figsize=(13,10),sharex=True)
    for j,(candidate,d) in enumerate(daily.groupby('candidate',sort=False)):
        x=pd.to_datetime(d.date)
        axes[0,j].plot(x,100*d.raw_reserve_fraction,label='Raw unresolved reserve / N')
        axes[0,j].plot(x,100*d.paired_budget_reserve_fraction,label='Paired-budget reserve / N')
        axes[0,j].set_title(candidate);axes[0,j].set_ylabel('Reference budget (%)');axes[0,j].legend(fontsize=8)
        axes[1,j].plot(x,d.structural_paired_reference_allowance/1e6,label='Remaining paired allowance')
        axes[1,j].plot(x,d.structural_matched_side_idle/1e6,label='Unmatched unused allowance')
        axes[1,j].set_ylabel('Reference dollars (millions)');axes[1,j].legend(fontsize=8)
        denom=d.component_intervals.replace(0,np.nan)
        axes[2,j].plot(x,100*d.fully_measurable_intervals/denom,label='Complete asset intervals')
        axes[2,j].set_ylabel('Measured interval count (%)');axes[2,j].legend(fontsize=8)
        for ax in axes[:,j]:ax.grid(alpha=.2)
    fig.suptitle('Conditional reservation audit — budgeting proxies, not wealth or performance')
    fig.tight_layout();fig.savefig(figures/'reservation_measurement_paths.png',dpi=160);plt.close(fig)
    (tables/'report_manifest.json').write_text(json.dumps(dict(aggregate_qa_passed=True,
        performance_computed=False,licensed_security_level_data_committed=False,
        reporting_scope='2003–2019 decision dates; terminal development-origin runoff remains separate',
        component_coverage_is_count_or_entry_basis_not_market_wealth=True),indent=2)+'\n')
    return summaries


def bounded_checks():
    """Original six cohorts use generic quarantine; unrelated orders continue."""
    result={};summaries=[];fig,axes=plt.subplots(1,2,figsize=(10,3.5),sharey=True)
    for j,candidate in enumerate(('uni_reversal_5','ridge')):
        base=ROOT/'data/interim/stage4f/bounded'/candidate
        e=pd.read_parquet(base/'quarantine_events.parquet')
        h=e[e.permno==20124]
        assert len(h)==3 and h.side.value_counts().to_dict()=={'long':2,'short':1}
        d=pd.read_parquet(base/'daily_coverage.parquet')
        assert (d[d.date.astype(str)>'2003-04-16'].orders_planned>0).all()
        p=pd.read_parquet(base/'phase_budget_path.parquet')
        end=p[p.date==p.date.max()]
        for side in ('long','short'):
            assert np.isclose(end[f'reserved_{side}'].sum(),e[e.side==side].entry_notional.sum())
        m=json.loads((base/'manifest.json').read_text())
        summaries.append({k:m[k] for k in ['candidate','eligible_keys','decision_dates','unresolved_positions_created','unresolved_longs','unresolved_shorts','ending_reserved_long','ending_reserved_short','reference_deployment_date_fraction']})
        axes[j].plot(pd.to_datetime(d.date),d.reserved_long/1000,label='Long-origin reserve')
        axes[j].plot(pd.to_datetime(d.date),d.reserved_short/1000,label='Short-origin reserve')
        axes[j].set_title(candidate);axes[j].tick_params(axis='x',rotation=25)
        axes[j].grid(alpha=.2);axes[j].legend(fontsize=8)
        result[candidate]=dict(qa_passed=True,household_cohorts_quarantined=3,
            event_specific_adapter_used=False,unrelated_orders_continue=True)
    tables=ROOT/'results/tables/stage4f';figures=ROOT/'results/figures/stage4f'
    tables.mkdir(parents=True,exist_ok=True);figures.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(summaries).to_csv(tables/'bounded_reservation_qa.csv',index=False)
    axes[0].set_ylabel('Reference-budget reserve ($000)')
    fig.suptitle('Bounded Jan–Apr 2003 QA only — no wealth or performance inference')
    fig.tight_layout();fig.savefig(figures/'bounded_reservation_qa.png',dpi=140);plt.close(fig)
    (ROOT/'data/interim/stage4f/bounded/qa.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def entry_boundary_diagnostic():
    """Review counterexamples in provisional logs; never certify full counts."""
    import duckdb
    from .fallback import verified_split_multiplier
    c=duckdb.connect();rows=[]
    for candidate in ('uni_reversal_5','ridge'):
        private=ROOT/'data/interim/stage4f/development'/candidate
        x=c.execute(f"""SELECT x.signal_date,x.date,x.permno,e.* EXCLUDE(permno)
            FROM read_parquet('{private}/execution_inputs_*.parquet') x JOIN
            '{ROOT}/data/interim/stage2a_events/stkdistributions.parquet' e
            ON x.permno=e.permno AND x.date=e.disexdt
            WHERE x.leg='entry' AND x.date<=DATE '2019-12-31' AND e.disfacshr<>0""").fetchdf()
        bad=x[[verified_split_multiplier(r) is None for r in x.to_dict('records')]]
        bad.to_parquet(private/'uncertified_entry_basis.parquet',index=False)
        for key,g in bad.groupby(['distype','dispaymenttype','disdetailtype']):
            rows.append(dict(candidate=candidate,event_type=key[0],payment_type=key[1],detail_type=key[2],
                provisional_affected_order_keys=len(g[['permno','signal_date']].drop_duplicates()),
                distinct_securities=g.permno.nunique(),first_entry_date=str(g.date.min().date()),
                last_entry_date=str(g.date.max().date()),
                status='INCOMPLETE AUDIT / UNCERTIFIED EXECUTION QUANTITY'))
    c.close()
    pd.DataFrame(rows).to_csv(ROOT/'results/tables/stage4f/entry_basis_gate.csv',index=False)
    return rows
