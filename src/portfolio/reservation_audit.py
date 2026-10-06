"""Generalized reservation feasibility/measurement availability; no PnL."""
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
from .construction import CAPITAL, SLEEVE
from .fallback import positive_open, verified_split_multiplier
from .reservation import Reservations, paired_plan, interval_measurable, verified_entry_multiplier, EntryBasisUnidentified
from .reservation_sources import ROOT, DevelopmentSources, preserve_prior, digest

CANDIDATES=('uni_reversal_5','ridge')


def event_batch(events,daily,delists,on_date):
    """Classify independently owned parent terms, without successor guesses."""
    multiplier=1.;cash=[];unknown=[]
    late=any(e.get('disdeclaredt') is not None and e['disdeclaredt']>on_date for e in events)
    if late:
        return {'multiplier':None,'cash':[], 'terminal':False,
                'unknown':'opening_event_terms_chronology_not_certified'}
    for e in events:
        m=verified_split_multiplier(e)
        if m is not None:
            multiplier*=m;continue
        fixed=(e['dispaymenttype']=='USD' and e['distype'] in ('CD','SD','ROC','CG')
            and e['disfacshr']==0 and e['disfacpr']==0
            and (e.get('dispermno') is None or e.get('dispermno')==0)
            and pd.notna(e['disdivamt']) and np.isfinite(e['disdivamt']) and e['disdivamt']>=0)
        if fixed:
            cash.append(e);continue
        unknown.append(e)
    cp=any(e['dispaymenttype']=='USD' and e['distype']=='CP' for e in events)
    if cp and events and all(e['dispaymenttype']=='USD' and pd.notna(e['disdivamt'])
                             and np.isfinite(e['disdivamt']) and e['disdivamt']>=0 for e in events):
        matches=[d for d in delists if d['delpaymenttype']=='CASH' and d['delstatustype']=='FPAY'
            and d['deldistype'] in ('D1','D2') and d['delretmisstype']=='NA'
            and pd.notna(d['delamtdt']) and pd.Timestamp(d['delamtdt']).date()<=on_date]
        amount=sum(e['disdivamt'] for e in events)
        if (len(matches)==1 and daily is not None
            and np.isfinite(daily.dlyorddivamt) and np.isfinite(daily.dlynonorddivamt)
            and abs(amount-daily.dlyorddivamt-daily.dlynonorddivamt)<1e-5
            and abs(amount-matches[0]['deldivamt'])<1e-5):
            return {'multiplier':1.,'cash':events,'terminal':True,'unknown':None}
    if unknown:
        return {'multiplier':None,'cash':cash,'terminal':False,
                'unknown':'received_inventory_rights_or_event_terms_unverified'}
    if delists or (daily is not None and daily.dlydelflg=='Y'):
        return {'multiplier':None,'cash':cash,'terminal':False,
                'unknown':'stored_delisting_without_verified_terminal_asset_terms'}
    return {'multiplier':multiplier,'cash':cash,'terminal':False,'unknown':None}


def reserve_position(p,budgets,on_date,reason,events):
    if p['state'] in ('corporate_action_unresolved','exit_execution_unresolved'):
        raise ValueError('Duplicate quarantine')
    p['reserve_basis']='verified_executed_entry_notional'
    p['last_verified_signed_quantity']=p['current_shares']
    p['current_shares']=None
    p['state']='exit_execution_unresolved' if reason=='five_global_date_cap_failure' else 'corporate_action_unresolved'
    p['quarantine_date']=on_date;p['quarantine_reason']=reason
    p['quantity_current_verified']=False
    p['unknown_event_types']='|'.join(sorted({e['distype'] for e in events}))
    p['linked_identifiers']=sorted({int(e['dispermno']) for e in events if e.get('dispermno') is not None and np.isfinite(e['dispermno']) and e['dispermno']!=0})
    p['unknown_successor_quantity']=None;p['unknown_wealth']=None
    return budgets.quarantine(p['key'],p['phase'],p['side'],p['entry_notional'],on_date,reason)


def reserve_queued_execution(p,budgets,on_date,events):
    """No executed shares/notional inferred from a positive post-event open."""
    p.update(state='queued_execution_quantity_unresolved',reserve_basis='planned_notional_reserve_proxy',
        entry_status='queued_execution_quantity_unresolved',current_shares=None,
        entry_notional=None,actual_entry_date=None,executed_entry_notional=None,
        last_verified_signed_quantity=None,quantity_current_verified=False,
        unknown_successor_quantity=None,unknown_wealth=None,borrow_basis=None,
        entry_cost_inputs_known=None,exit_cost_inputs_known=None,
        execution_state_unknown=True,claims_and_obligations_measurement_unknown=True,
        quarantine_date=on_date,quarantine_reason='entry_boundary_share_basis_unverified',
        planned_notional_reserve_proxy=p['planned_entry_notional'])
    p['unknown_event_types']='|'.join(sorted({e['distype'] for e in events}))
    p['linked_identifiers']=sorted({int(e['dispermno']) for e in events
        if e.get('dispermno') is not None and np.isfinite(e['dispermno']) and e['dispermno']!=0})
    return budgets.queued_proxy(p['key'],p['phase'],p['side'],
        p['planned_entry_notional'],on_date,p['quarantine_reason'])


def add_claims(p,terms,q0,on_date,claims,claim_events):
    for e in terms:
        amount=q0*float(e['disdivamt'])
        c={'position_key':p['key'],'permno':p['permno'],'signal_date':p['signal_date'],
            'effective_date':on_date,'payment_date':e.get('dispaydt'),
            'signed_amount':amount,'prior_owned_share_basis':q0,
            'cash_state':'established_measurable_receivable',
            'settlement_evidence':'economic_payment_date_not_account_termination_certificate'}
        p['measured_claims_count']+=1
        claims.append(c);claim_events.append(c.copy())


def occupied(book,submitted):
    out=np.zeros((5,2))
    for p in book:
        out[p['phase'],0 if p['side']=='long' else 1]+=p['entry_notional']
    for values in submitted.values():
        for p in values:out[p['phase'],0 if p['side']=='long' else 1]+=p['planned_entry_notional']
    return out


def retained_at_replacement(book,submitted,today,tomorrow):
    k=np.zeros((5,2))
    for p in book:
        # Only normal, not-yet-overdue scheduled retirement tomorrow retains
        # the frozen retirement/replacement lifecycle. Never erase a reserve.
        if p['scheduled_exit_date']==tomorrow and p['scheduled_exit_date']>today:
            continue
        k[p['phase'],0 if p['side']=='long' else 1]+=p['entry_notional']
    for values in submitted.values():
        for p in values:k[p['phase'],0 if p['side']=='long' else 1]+=p['planned_entry_notional']
    return k


def write_table(path,rows):
    if rows:
        pd.DataFrame(rows).to_parquet(path,index=False)
    elif path.exists():path.unlink()


def audit_candidate(src,candidate,end):
    bounded=end<date(2019,12,31)
    tag='bounded' if bounded else 'development'
    out=src.root/tag/candidate;out.mkdir(parents=True,exist_ok=True)
    budgets=Reservations();book=[];unknown=[];submitted={};claims=[]
    blocked=set();count=Counter();coverage=[];phase_rows=[];overcommits=[]
    event_rows=[];orders=[];decisions=[];claim_events=[];intervals=[];execution_legs=[];terminal_states=[]
    state_counts=Counter();year=None;month=None;processed=0;last_date=None
    source_year=None
    exhausted_phase=[None]*5;exhausted_candidate=None
    def flush(y):
        if y is None:return
        for name,rows in [('orders',orders),('decisions',decisions),('measured_claims',claim_events),
                          ('component_intervals',intervals),('execution_inputs',execution_legs),('terminal_states',terminal_states)]:
            write_table(out/f'{name}_{y}.parquet',rows);rows.clear()
    for today in src.calendar:
        if today.year<2003:continue
        if today>end:break
        if year is not None and today.year!=year:flush(year)
        year=today.year
        src.load(year)
        idx=src.index[today];previous=src.calendar[idx-1];tomorrow=src.calendar[idx+1]
        if last_date is not None:
            assert previous==last_date
        last_date=today
        if month!=(today.year,today.month):
            month=(today.year,today.month)
            print(f'{candidate} {today}: reserves={budgets.amounts.sum():,.0f}, quarantined={len(unknown)}, entered={count["entered"]:,}',flush=True)
        start_u=len(unknown);start_basis=float(budgets.executed_amounts.sum())
        start_verified_u=sum(p['state']!='queued_execution_quantity_unresolved' for p in unknown)
        for p in unknown:p['original_exit_cap_exceeded']=today>p['deadline']
        n_interval=start_u;basis_interval=start_basis
        n_wealth=n_full=n_expenses=0;basis_full=basis_wealth=0.
        today_quarantine=[];today_executed=[]
        # Existing holdings acquire exit-day rights; new entries do not.
        for p in list(book):
            key=(p['permno'],today);terms=src.events.get(key,[])
            dl=src.delists.get(key,[]);r=src.row(p['permno'],today)
            q0=p['current_shares'];before_mark=p['last_open_measured']
            status=event_batch(terms,r,dl,today)
            add_claims(p,status['cash'],q0,today,claims,claim_events)
            if status['unknown']:
                reserve_position(p,budgets,today,status['unknown'],terms)
                unknown.append(p);today_quarantine.append(p)
                blocked.add(p['permno']);blocked.update(p['linked_identifiers'])
                p['exit_cost_inputs_known']=None
                count['quarantined']+=1
                event_rows.append({'candidate':candidate,'permno':p['permno'],
                    'signal_date':p['signal_date'],'phase':p['phase'],'side':p['side'],
                    'quarantine_date':today,'event_type':p['unknown_event_types'],
                    'reason':status['unknown'],'entry_notional':p['entry_notional'],
                    'last_verified_signed_quantity':q0,'linked_identifiers':p['linked_identifiers'],
                    'deadline':p['deadline'],'release_date':None})
            elif status['terminal']:
                p['current_shares']=0.;p['state']='measurable_cash_termination'
                p['actual_exit_date']=today;p['delay']=None;p['exit_cost_inputs_known']=True
                count['cash_termination']+=1;today_executed.append(p)
            else:
                p['current_shares']*=status['multiplier']
                if today>=p['scheduled_exit_date']:
                    lag=idx-src.index[p['scheduled_exit_date']];assert 0<=lag<=5
                    opening=src.opening(p['permno'],today)
                    if positive_open(opening):
                        p['executed_exit_quantity']=p['current_shares']
                        p['current_shares']=0.;p['state']='assumed_exited'
                        p['actual_exit_date']=today;p['delay']=lag
                        p['exit_cost_inputs_known']=src.cost_inputs(p['permno'],previous) and p['permno'] not in blocked
                        count['market_exited']+=1;count[f'delay_{lag}']+=1
                        today_executed.append(p)
                        execution_legs.append({'candidate':candidate,'permno':p['permno'],
                            'signal_date':p['signal_date'],'date':today,'leg':'exit',
                            'cost_inputs_measured':p['exit_cost_inputs_known'],
                            'execution_notional':abs(p['executed_exit_quantity'])*opening,
                            'sigma_decision_date':previous,'no_performance_computed':True})
                    elif lag==5:
                        reserve_position(p,budgets,today,'five_global_date_cap_failure',[])
                        unknown.append(p);today_quarantine.append(p);blocked.add(p['permno'])
                        count['quarantined']+=1
                        event_rows.append({'candidate':candidate,'permno':p['permno'],
                            'signal_date':p['signal_date'],'phase':p['phase'],'side':p['side'],
                            'quarantine_date':today,'event_type':'','reason':'five_global_date_cap_failure',
                            'entry_notional':p['entry_notional'],'last_verified_signed_quantity':q0,
                            'linked_identifiers':[],'deadline':p['deadline'],'release_date':None})
            measured_terminal=p['state']=='measurable_cash_termination'
            end_mark=measured_terminal or (p['state'] not in ('corporate_action_unresolved','exit_execution_unresolved') and positive_open(src.opening(p['permno'],today)))
            expense_known=(p['entry_cost_inputs_known'] if previous==p['actual_entry_date'] else True)
            if p['state']=='assumed_exited':expense_known=expense_known and p['exit_cost_inputs_known']
            wealth,expense,full=interval_measurable(before_mark,end_mark,
                p['state'] not in ('corporate_action_unresolved','exit_execution_unresolved'),
                status['unknown'] is None,expense_known)
            n_interval+=1;basis_interval+=p['entry_notional']
            n_wealth+=wealth;n_expenses+=expense;n_full+=full
            basis_wealth+=p['entry_notional']*wealth;basis_full+=p['entry_notional']*full
            intervals.append({'candidate':candidate,'permno':p['permno'],'signal_date':p['signal_date'],
                'interval_end':today,'entry_reference_notional':p['entry_notional'],
                'wealth_measurable':wealth,'expense_inputs_measurable':expense,
                'complete_component_measurable':full,'state':p['state']})
            p['last_open_measured']=end_mark
        # Quarantined stock wealth stays unknown: later prices are not substitutes.
        # Known fixed-basis borrowing inputs remain separately measurable.
        n_expenses+=start_verified_u
        for p in today_executed+today_quarantine:terminal_states.append(p.copy())
        book=[p for p in book if p['state']=='outstanding']
        before_entry=occupied(book,{})+budgets.amounts
        queued=submitted.pop(today,[])
        for p in queued:
            opening=src.opening(p['permno'],today)
            if not positive_open(opening):
                p['state']='canceled_entry';p['entry_status']='canceled_missing_open'
                count['canceled_entry']+=1
                terminal_states.append(p.copy())
                continue
            terms=src.events.get((p['permno'],today),[])
            try:
                entry_multiplier=verified_entry_multiplier(terms)
            except EntryBasisUnidentified:
                reserve_queued_execution(p,budgets,today,terms)
                unknown.append(p);count['queued_execution_quantity_unresolved']+=1
                count['quarantined']+=1;terminal_states.append(p.copy())
                blocked.add(p['permno']);blocked.update(p['linked_identifiers'])
                event_rows.append({'candidate':candidate,'permno':p['permno'],
                    'signal_date':p['signal_date'],'phase':p['phase'],'side':p['side'],
                    'quarantine_date':today,'event_type':p['unknown_event_types'],
                    'reason':p['quarantine_reason'],'entry_notional':None,
                    'last_verified_signed_quantity':None,'linked_identifiers':p['linked_identifiers'],
                    'deadline':p['deadline'],'release_date':None})
                execution_legs.append({'candidate':candidate,'permno':p['permno'],
                    'signal_date':p['signal_date'],'date':today,'leg':'queued_entry_unknown',
                    'cost_inputs_measured':False,'execution_notional':None,
                    'sigma_decision_date':p['signal_date'],'no_performance_computed':True})
                continue
            q=p['order_shares']*entry_multiplier
            p['current_shares']=q;p['entry_notional']=abs(q)*opening
            p['actual_entry_date']=today;p['state']='outstanding';p['entry_status']='assumed_entry'
            p['quantity_current_verified']=True;p['last_open_measured']=True
            p['entry_cost_inputs_known']=p['planned_cost_inputs_known'] and p['permno'] not in blocked
            p['borrow_basis']=p['entry_notional'] if p['side']=='short' else 0.
            count['entered']+=1;book.append(p)
            execution_legs.append({'candidate':candidate,'permno':p['permno'],
                'signal_date':p['signal_date'],'date':today,'leg':'entry',
                'cost_inputs_measured':p['entry_cost_inputs_known'],
                'execution_notional':p['entry_notional'],'sigma_decision_date':p['signal_date'],
                'no_performance_computed':True})
        full_occupied=occupied(book,submitted)
        over=budgets.opening_overcommitment(full_occupied)
        # Every excess is recorded, not erased; distinguish queued contribution.
        queue_phases={p['phase'] for p in queued if p['entry_status'] in ('assumed_entry','queued_execution_quantity_unresolved')}
        for ph,side in zip(*np.nonzero(over>1e-8)):
            overcommits.append({'candidate':candidate,'date':today,'phase':int(ph),
                'side':'long' if side==0 else 'short','overcommitment':float(over[ph,side]),
                'prequeued_overcommitment':max(0.,float(before_entry[ph,side]-SLEEVE)),
                'queued_orders_honored':ph in queue_phases,
                'queued_increment':max(0.,float(over[ph,side]-max(0.,before_entry[ph,side]-SLEEVE)))})
        structural_remaining,structural_pair,structural_idle=budgets.budgets()
        for ph in range(5):
            if structural_pair[ph]<=1e-8 and exhausted_phase[ph] is None:exhausted_phase[ph]=today
        if structural_pair.sum()<=1e-8 and exhausted_candidate is None:exhausted_candidate=today
        retained=retained_at_replacement(book,submitted,today,tomorrow)
        remaining,pair,idle=budgets.budgets(retained)
        phase=src.phase[today]
        g=src.signal_groups[today];processed+=len(g)
        gross=defaultdict(float)
        for p in book:
            if p['scheduled_exit_date']<=tomorrow:gross[p['permno']]+=abs(p['current_shares'])
        price=np.array([src.row(p,today).dlyprc if src.row(p,today) else np.nan for p in g.permno])
        adv=np.array([src.row(p,today).adv20 if src.row(p,today) else np.nan for p in g.permno])
        exit_q=np.array([gross.get(int(p),0.) for p in g.permno])
        blocked_rows=np.array([int(p) in blocked for p in g.permno])
        sides,dollars,reasons=paired_plan(g[candidate],price,adv,exit_q,float(pair[phase]),blocked_rows)
        new_amount=float(dollars[dollars>0].sum())
        assert new_amount<=pair[phase]+1e-7
        assert np.isclose(new_amount,-dollars[dollars<0].sum(),atol=1e-7)
        for ph in range(5):
            phase_rows.append({'candidate':candidate,'date':today,'phase':ph,
                'reserved_long':float(budgets.amounts[ph,0]),
                'verified_executed_reserve_long':float(budgets.executed_amounts[ph,0]),
                'verified_executed_reserve_short':float(budgets.executed_amounts[ph,1]),
                'planned_proxy_reserve_long':float(budgets.planned_amounts[ph,0]),
                'planned_proxy_reserve_short':float(budgets.planned_amounts[ph,1]),'reserved_short':float(budgets.amounts[ph,1]),
                'retained_long':float(retained[ph,0]),'retained_short':float(retained[ph,1]),
                'paired_reserve':float(max(budgets.amounts[ph])),
                'raw_reserve_fraction':float(budgets.amounts[ph].sum()/CAPITAL),
                'paired_reserve_fraction':float(max(budgets.amounts[ph])/CAPITAL),
                'structural_paired_allowance':float(structural_pair[ph]),
                'new_allowance_if_current_replacement':float(pair[ph]),
                'structural_matched_idle_long':float(structural_idle[ph,0]),
                'structural_matched_idle_short':float(structural_idle[ph,1]),
                'matched_idle_long':float(idle[ph,0]),'matched_idle_short':float(idle[ph,1]),
                'is_current_phase':ph==phase,'new_paired_allocation':new_amount if ph==phase else 0.,
                'reference_deployment_exhausted':structural_pair[ph]<=1e-8,
                'exhaustion_is_insolvency':False})
        d=g[['permno','signal_date','entry_date','exit_date']].copy()
        d['candidate']=candidate;d['phase']=phase;d['side']=sides
        d['planned_dollars']=dollars;d['decision_reason']=reasons
        decisions.extend(d.to_dict('records'))
        for i,r in enumerate(g.itertuples()):
            if dollars[i]==0:continue
            p={'key':f'{int(r.permno)}:{today}', 'candidate':candidate,'permno':int(r.permno),
                'signal_date':today,'phase':phase,'side':'long' if dollars[i]>0 else 'short',
                'scheduled_entry_date':r.entry_date,'scheduled_exit_date':r.exit_date,
                'deadline':src.calendar[src.index[r.exit_date]+5],
                'planned_entry_notional':abs(dollars[i]),'order_shares':dollars[i]/price[i],
                'state':'submitted','entry_status':'pending','current_shares':None,
                'entry_notional':None,'actual_entry_date':None,'actual_exit_date':None,'delay':None,
                'planned_cost_inputs_known':src.cost_inputs(int(r.permno),today),
                'entry_cost_inputs_known':None,'exit_cost_inputs_known':None,
                'measured_claims_count':0,'quarantine_date':None,'quarantine_reason':None}
            orders.append(p);submitted.setdefault(r.entry_date,[]).append(p)
            count['submitted']+=1
        # Asset intervals only. Fixed measured cash/claims shown separately.
        coverage.append({'candidate':candidate,'date':today,'year':today.year,'current_phase':phase,
            'eligible_keys':len(g),'unresolved_positions':len(unknown),
            'unresolved_longs':sum(p['side']=='long' for p in unknown),
            'unresolved_shorts':sum(p['side']=='short' for p in unknown),
            'reserved_long':float(budgets.amounts[:,0].sum()),
            'verified_executed_reserve_long':float(budgets.executed_amounts[:,0].sum()),
            'verified_executed_reserve_short':float(budgets.executed_amounts[:,1].sum()),
            'planned_proxy_reserve_long':float(budgets.planned_amounts[:,0].sum()),
            'planned_proxy_reserve_short':float(budgets.planned_amounts[:,1].sum()),
            'unresolved_queued_execution_count':sum(p['state']=='queued_execution_quantity_unresolved' for p in unknown),
            'unresolved_queued_proxy_commitment':float(budgets.planned_amounts.sum()),'reserved_short':float(budgets.amounts[:,1].sum()),
            'raw_reserve_fraction':float(budgets.amounts.sum()/CAPITAL),
            'paired_budget_reserve_fraction':float(budgets.amounts.max(axis=1).sum()/CAPITAL),
            'structural_paired_reference_allowance':float(structural_pair.sum()),
            'structural_matched_side_idle':float(structural_idle.sum()),
            'current_phase_allowance':float(pair[phase]),
            'current_phase_matched_idle':float(idle[phase].sum()),
            'reference_permits_new_paired_deployment':pair[phase]>1e-8,
            'new_paired_allocation':new_amount,'orders_planned':int(np.count_nonzero(dollars)),
            'blocked_unresolved_signal_keys':int(blocked_rows.sum()),
            'component_intervals':n_interval,'wealth_measurable_intervals':n_wealth,
            'expense_inputs_measurable_intervals':n_expenses,'fully_measurable_intervals':n_full,
            'interval_entry_basis_denominator':basis_interval,
            'interval_planned_proxy_denominator_separate':float(budgets.planned_amounts.sum()),
            'coverage_denominator_excludes_unmeasured_executed_notional':True,
            'identified_wealth_entry_basis':basis_wealth,'fully_measured_entry_basis':basis_full,
            'verified_outstanding_inventory_positions':len(book),
            'measured_claim_components':len(claims),
            'unresolved_short_borrow_basis':sum(p['borrow_basis'] for p in unknown if p['side']=='short' and p['borrow_basis'] is not None),
            'unknown_short_borrow_basis_count':sum(p['side']=='short' and p['borrow_basis'] is None for p in unknown),
            'reference_exhaustion_is_insolvency':False})
        # Claim state transfer is not a gain or loss; reserve never released.
        for c in claims:
            if (c['cash_state']=='established_measurable_receivable' and c['payment_date'] is not None
                    and c['payment_date']<=today):
                c['cash_state']='economic_payment_date_cash_transfer';c['transfer_date']=today
        # Keep receipt/claim journal, but do not loop settled claims forever.
        claims=[c for c in claims if c['cash_state']=='established_measurable_receivable']
    flush(year)
    # Orders surviving a year flush have mutable state; save final live/unknown
    # inventory separately, and join by key instead of stale yearly terminal snapshots.
    pending=[p for rows in submitted.values() for p in rows]
    write_table(out/'final_verified_inventory.parquet',book)
    write_table(out/'final_pending_orders.parquet',pending)
    write_table(out/'unresolved_obligations.parquet',unknown)
    for e in event_rows:
        key=f"{e['permno']}:{e['signal_date']}";r=budgets.records[key]
        e['reserve_basis']=r['reserve_basis'];e['reference_commitment']=r['reserve']
        e['planned_notional_reserve_proxy']=r['planned_notional_reserve_proxy']
    write_table(out/'quarantine_events.parquet',event_rows)
    write_table(out/'daily_coverage.parquet',coverage)
    write_table(out/'phase_budget_path.parquet',phase_rows)
    write_table(out/'opening_overcommitments.parquet',overcommits)
    write_table(out/'remaining_measurable_claims.parquet',claims)
    assert count['submitted']==count['entered']+count['canceled_entry']+count['queued_execution_quantity_unresolved']+len(pending)
    assert count['entered']==count['market_exited']+count['cash_termination']+len(unknown)-count['queued_execution_quantity_unresolved']+len(book)
    assert count['quarantined']==len(unknown)==len(budgets.records)
    assert np.isclose(budgets.executed_amounts.sum(),sum(p['entry_notional'] for p in unknown if p['entry_notional'] is not None))
    assert np.isclose(budgets.planned_amounts.sum(),sum(p['planned_notional_reserve_proxy'] for p in unknown if p['state']=='queued_execution_quantity_unresolved'))
    np.testing.assert_allclose(budgets.amounts,budgets.executed_amounts+budgets.planned_amounts)
    assert all(p['current_shares'] is None and p['unknown_wealth'] is None for p in unknown)
    assert all(p['entry_notional']==budgets.records[p['key']]['reserve'] for p in unknown if p['state']!='queued_execution_quantity_unresolved')
    assert all(p['entry_notional'] is None and p['borrow_basis'] is None for p in unknown if p['state']=='queued_execution_quantity_unresolved')
    cov=pd.DataFrame(coverage);phase=pd.DataFrame(phase_rows)
    assert not cov.duplicated(['candidate','date']).any()
    assert not phase.duplicated(['candidate','date','phase']).any()
    if not bounded:assert processed==3829908 and len(cov)==4279
    unknown_frame=pd.DataFrame(unknown)
    summary={'candidate':candidate,'scope':tag,'eligible_keys':processed,
        'decision_dates':len(cov),'end_date':str(end),**dict(count),
        'unresolved_positions_created':len(unknown),
        'unresolved_distinct_securities':int(unknown_frame.permno.nunique()) if len(unknown) else 0,
        'distinct_quarantine_security_dates':len({(p['permno'],p['quarantine_date']) for p in unknown}),
        'distinct_corporate_events':len({(p['permno'],p['quarantine_date']) for p in unknown if p['state'] in ('corporate_action_unresolved','queued_execution_quantity_unresolved')}),
        'unresolved_longs':sum(p['side']=='long' for p in unknown),
        'unresolved_shorts':sum(p['side']=='short' for p in unknown),
        'corporate_action_unresolved_positions':sum(p['state']=='corporate_action_unresolved' for p in unknown),
        'ordinary_cap_failure_positions':sum(p['state']=='exit_execution_unresolved' for p in unknown),
        'ending_verified_executed_reserve':float(budgets.executed_amounts.sum()),
        'ending_planned_notional_proxy_reserve':float(budgets.planned_amounts.sum()),
        'unresolved_queued_execution_count':count['queued_execution_quantity_unresolved'],
        'unresolved_queued_longs':sum(p['state']=='queued_execution_quantity_unresolved' and p['side']=='long' for p in unknown),
        'unresolved_queued_shorts':sum(p['state']=='queued_execution_quantity_unresolved' and p['side']=='short' for p in unknown),
        'ending_reserved_long':float(budgets.amounts[:,0].sum()),'ending_reserved_short':float(budgets.amounts[:,1].sum()),
        'ending_raw_reserve_fraction':float(budgets.amounts.sum()/CAPITAL),
        'ending_paired_budget_reserve_fraction':float(budgets.amounts.max(axis=1).sum()/CAPITAL),
        'ending_structural_matched_side_idle':float(budgets.budgets()[2].sum()),
        'phase_exhaustion_dates':{str(i):str(x) if x else None for i,x in enumerate(exhausted_phase)},
        'candidate_reference_exhaustion_date':str(exhausted_candidate) if exhausted_candidate else None,
        'independently_evidenced_releases':0,
        'dates_permitting_reference_deployment':int(cov.reference_permits_new_paired_deployment.sum()),
        'reference_deployment_date_fraction':float(cov.reference_permits_new_paired_deployment.mean()),
        'dates_with_new_paired_orders':int((cov.new_paired_allocation>1e-8).sum()),
        'fully_measurable_component_interval_fraction':float(cov.fully_measurable_intervals.sum()/max(1,cov.component_intervals.sum())),
        'wealth_measurable_component_interval_fraction':float(cov.wealth_measurable_intervals.sum()/max(1,cov.component_intervals.sum())),
        'expense_inputs_measurable_interval_fraction':float(cov.expense_inputs_measurable_intervals.sum()/max(1,cov.component_intervals.sum())),
        'identified_verified_entry_basis_fraction':float(cov.identified_wealth_entry_basis.sum()/cov.interval_entry_basis_denominator.sum()),
        'planned_proxy_excluded_from_executed_entry_basis_denominator':True,
        'component_interval_count':int(cov.component_intervals.sum()),
        'fully_measurable_component_intervals':int(cov.fully_measurable_intervals.sum()),
        'opening_overcommitment_side_dates':len(overcommits),
        'queued_order_overcommitment_side_dates':sum(x['queued_orders_honored'] and x['queued_increment']>1e-8 for x in overcommits),
        'maximum_side_opening_overcommitment':max((x['overcommitment'] for x in overcommits),default=0.),
        'remaining_verified_positions_at_2019_boundary':len(book),
        'pending_development_orders_at_2019_boundary':len(pending),
        'conditional_measured_component_analysis_technically_feasible':bool(cov.fully_measurable_intervals.sum()>0),
        'full_account_wealth_identified':not unknown,
        'reference_budget_exhaustion_means_insolvency':False,
        'performance_computed':False}
    (out/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
    return summary


def run(end=date(2019,12,31)):
    before=preserve_prior();src=DevelopmentSources()
    if end==date(2019,12,31):
        prior=src.root/'development';archive=src.root/'development_entry_gate_provisional'
        if prior.exists() and not archive.exists():prior.rename(archive)
    tag='bounded' if end<date(2019,12,31) else 'development'
    (src.root/tag).mkdir(exist_ok=True)
    (src.root/tag/'manifest.json').write_text(json.dumps({'qa_passed':False,'status':'RUNNING','performance_computed':False})+'\n')
    results=[]
    for candidate in CANDIDATES:
        src.year=None;src.records={};src.previous_tail={}
        try:
            results.append(audit_candidate(src,candidate,end))
        except EntryBasisUnidentified as error:
            (src.root/tag/'manifest.json').write_text(json.dumps({
                'qa_passed':False,'status':'BLOCKED_ENTRY_SHARE_BASIS_REVIEW',
                'exception_class':type(error).__name__,'message':str(error),
                'full_candidate_counts_certified':False,'performance_computed':False,
                'provisional_outputs_must_not_be_used':True},indent=2)+'\n')
            src.c.close()
            raise
    assert before==preserve_prior(),'Prior strict/conditional artifacts modified'
    tag='bounded' if end<date(2019,12,31) else 'development'
    (src.root/tag/'manifest.json').write_text(json.dumps({'qa_passed':True,
        'scope':tag,'end_date':str(end),'original_development_keys':3829908,
        'original_development_dates':4279,'forecast_checksums_verified':68,
        'protected_artifact_hashes':before,'source_fingerprints':src.fingerprints,
        'cache_checksums':src.cache_checksums,'performance_computed':False,
        'raw_scanned':False,'wrds_queries':0,'holdout_forecasts_targets_or_eligibility_used':False,
        '2020_price_event_or_feature_records_accessed':0,'calendar_only_2020_dates':src.calendar_extension_dates,'summaries':results,
        'timestamp_utc':pd.Timestamp.now(tz='UTC').isoformat()},indent=2)+'\n')
    src.c.close()
    return results
