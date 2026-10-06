"""Replay immutable Stage4F orders; journal only identified signed increments.

Future terminal snapshots are isolated reconciliation expectations, never an
execution, availability, quantity, price or event input. No order reconstruction.
"""
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from .construction import CAPITAL
from .fallback import positive_open
from .reservation import verified_entry_multiplier, EntryBasisUnidentified
from .reservation_audit import event_batch, CANDIDATES
from .reservation_sources import ROOT, DevelopmentSources, preserve_prior, digest
from .measured_components import (
    finite, asset_increment, terminal_asset_increment, execution_primitives,
    borrow_primitive, DailyJournal)

ORDER_FIELDS = ['key','permno','signal_date','phase','side','scheduled_entry_date',
                'scheduled_exit_date','deadline','planned_entry_notional','order_shares']
EXPECT_FIELDS = ['key','state','entry_notional','actual_entry_date','actual_exit_date',
                 'quarantine_date','current_shares','executed_exit_quantity']
SCHEMA = pa.schema([
    ('candidate',pa.string()),('key',pa.string()),('permno',pa.int64()),
    ('phase',pa.int64()),('side',pa.string()),('date',pa.date32()),
    ('previous_date',pa.date32()),('kind',pa.string()),('amount',pa.float64()),
    ('reason',pa.string()),('verified_entry_basis',pa.float64()),
    ('quantity',pa.float64()),('previous_open',pa.float64()),('opening',pa.float64()),
    ('multiplier',pa.float64()),('execution_notional',pa.float64()),
    ('sigma_date',pa.date32()),('sigma',pa.float64()),('participation',pa.float64()),
    ('event_sequence',pa.int64()),('payment_date',pa.date32())])


class JournalWriter:
    def __init__(self, path):
        self.writer = pq.ParquetWriter(path, SCHEMA, compression='zstd')
        self.rows = []; self.count = 0

    def add(self, row):
        self.rows.append(row); self.count += 1
        if len(self.rows) >= 25000: self.flush()

    def flush(self):
        if self.rows:
            self.writer.write_table(pa.Table.from_pylist(self.rows, schema=SCHEMA))
            self.rows.clear()

    def close(self):
        self.flush(); self.writer.close()


def protected():
    hashes = preserve_prior()
    # Full Stage4F accounting artifacts must remain byte-for-byte unchanged.
    for folder in ('data/interim/stage4f/development','results/tables/stage4f','results/figures/stage4f'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file(): hashes[str(p.relative_to(ROOT))] = digest(p)
    return hashes


def orders_for_year(src, frozen, year):
    path = frozen/f'orders_{year}.parquet'
    fields = ','.join('o.'+x for x in ORDER_FIELDS)
    expectations = ','.join('e.'+x+' expected_'+x for x in EXPECT_FIELDS if x != 'key')
    d = src.c.execute(f"SELECT {fields},{expectations} FROM read_parquet('{path}') o LEFT JOIN expectations e USING(key) ORDER BY scheduled_entry_date,permno").fetchdf()
    assert len(d) == src.c.execute(f"SELECT count(*) FROM read_parquet('{path}')").fetchone()[0]
    assert not d.key.duplicated().any() and d.expected_state.notna().all()
    for col in d.columns:
        if col.endswith('date') or col=='deadline':
            d[col] = pd.to_datetime(d[col]).dt.date.where(d[col].notna(), None)
    grouped = defaultdict(list)
    for p in d.to_dict('records'): grouped[p['scheduled_entry_date']].append(p)
    return grouped, len(d)


def check_state(p, state, today, q=None):
    """Terminal evidence is QA-only, called after independently computed state."""
    assert p['expected_state'] == state, (p['key'], state, p['expected_state'])
    field = 'expected_quarantine_date' if 'unresolved' in state else 'expected_actual_exit_date'
    if state == 'canceled_entry': field = 'scheduled_entry_date'
    if state != 'outstanding':
        assert p[field] == today, (p['key'], field, p[field], today)
    if q is not None:
        if state == 'assumed_exited':
            np.testing.assert_allclose(q, p['expected_executed_exit_quantity'], rtol=1e-12, atol=1e-9)
        elif state == 'outstanding':
            np.testing.assert_allclose(q, p['expected_current_shares'], rtol=1e-12, atol=1e-9)


def participation(src, permno, previous, gross_quantities):
    row = src.row(permno, previous)
    if row is None or not finite(row.adv20) or row.adv20 <= 0 or not positive_open(row.dlyprc):
        return None, None
    # Frozen gross planned entry + due/overdue exit flow at preceding close.
    p = gross_quantities.get(permno, 0.) * row.dlyprc / row.adv20
    return row.sigma20 if finite(row.sigma20) and row.sigma20 >= 0 else None, p


def replay_candidate(src, candidate, end):
    tag = 'bounded' if end < date(2019,12,31) else 'development'
    out = ROOT/'data/interim/stage4g'/tag/candidate; out.mkdir(parents=True,exist_ok=True)
    frozen = ROOT/'data/interim/stage4f/development'/candidate
    fields = ','.join(EXPECT_FIELDS)
    # Canonical terminal snapshots plus live/pending final state; stale order
    # snapshots are deliberately never used as final states.
    terminal = f"SELECT {fields} FROM read_parquet('{frozen}/terminal_states_*.parquet',union_by_name=true)"
    live = ','.join(x if x != 'executed_exit_quantity' else 'NULL executed_exit_quantity' for x in EXPECT_FIELDS)
    src.c.execute(f"CREATE OR REPLACE TEMP TABLE expectations AS {terminal} UNION ALL SELECT {live} FROM read_parquet('{frozen}/final_verified_inventory.parquet') UNION ALL SELECT {live} FROM read_parquet('{frozen}/final_pending_orders.parquet',union_by_name=true)")
    n, unique = src.c.execute('SELECT count(*),count(DISTINCT key) FROM expectations').fetchone()
    assert n == unique
    cov = pd.read_parquet(frozen/'daily_coverage.parquet').set_index('date')
    book=[]; unknown=[]; pending=defaultdict(list); blocked=set(); rows=[]
    counts=Counter(); year=None; writer=None; journal_count=0
    expected_legs={}; seen_legs=set(); actual_claims=[]; expected_claims=[]
    submitted_count=0; retired=0; verified_entries=0; verified_exit=0; terminal_cash=0; canceled=0
    def validate_year():
        if year is None: return
        assert set(expected_legs) == seen_legs, ('Execution leg keys differ',year)
        assert sorted(actual_claims) == sorted(expected_claims), ('Claim identities differ',year)
    for today in src.calendar:
        if today < date(2003,1,2): continue
        if today > end: break
        if today.year != year:
            validate_year()
            if writer is not None: writer.close(); journal_count += writer.count
            year = today.year; src.load(year)
            grouped, num = orders_for_year(src,frozen,year)
            for d, values in grouped.items(): pending[d].extend(values)
            submitted_count += num
            writer = JournalWriter(out/f'journal_{year}.parquet')
            legs = pd.read_parquet(frozen/f'execution_inputs_{year}.parquet')
            if end.year == year: legs = legs.loc[legs.date <= end]
            expected_legs = {(int(r.permno),r.signal_date,r.date,r.leg):r.execution_notional for r in legs.itertuples()}
            seen_legs = set(); actual_claims=[]; expected_claims=[]
            claim_path=frozen/f'measured_claims_{year}.parquet'
            if claim_path.exists():
                claims=pd.read_parquet(claim_path)
                claims=claims.loc[claims.effective_date<=end]
                expected_claims=[(r.position_key,r.effective_date,round(r.signed_amount,8)) for r in claims.itertuples()]
        idx=src.index[today]; previous=src.calendar[idx-1]
        queued=pending.pop(today,[])
        gross=defaultdict(float)
        for p in book:
            if p['scheduled_exit_date'] <= today: gross[p['permno']] += abs(p['q'])
        for p in queued: gross[p['permno']] += abs(p['order_shares'])
        daily=DailyJournal(); ninterval=len(book)+len(unknown); nwealth=0; ncomplete=0
        basis_den=sum(p['basis'] for p in book)+sum(p['basis'] for p in unknown if finite(p['basis']))
        basis_measured=0.; turnover=0.; leg_count=0; claim_count=0
        fixed_count=impact_count=borrow_count=0
        def emit(p,kind,value,reason,**inputs):
            row={'candidate':candidate,'key':p['key'],'permno':p['permno'],
                 'phase':p['phase'],'side':p['side'],'date':today,'previous_date':previous,
                 'kind':kind,'amount':float(value) if finite(value) else None,'reason':reason,
                 'verified_entry_basis':p.get('basis'),**inputs}
            writer.add(row); daily.add(kind,value)
        def execution(p,leg,q):
            nonlocal turnover,leg_count
            opening=src.opening(p['permno'],today)
            v=abs(q)*opening if finite(q) and positive_open(opening) else None
            sigma,part=participation(src,p['permno'],previous,gross)
            # Stage4F blocks identities once a linked obligation is unresolved;
            # the order persists but impact inputs cannot be certified there.
            if p['permno'] in blocked: part=None
            fixed,impact=execution_primitives(v,sigma,part)
            for kind,val in [('fixed',fixed),('impact',impact)]:
                emit(p,kind,val,'verified_'+leg if finite(val) else 'unidentified_'+leg+'_cost_inputs',
                     quantity=q,opening=opening,execution_notional=v,
                     sigma_date=previous,sigma=sigma,participation=part)
            legkey=(p['permno'],p['signal_date'],today,leg)
            assert legkey in expected_legs and legkey not in seen_legs, legkey
            expected=expected_legs[legkey]
            if finite(v): np.testing.assert_allclose(v,expected,rtol=1e-12,atol=1e-8); turnover+=v;leg_count+=1
            else: assert not finite(expected)
            seen_legs.add(legkey)
            return finite(fixed) and finite(impact)
        def quarantine(p,reason,events):
            nonlocal retired
            state='exit_execution_unresolved' if reason=='five_global_date_cap_failure' else 'corporate_action_unresolved'
            check_state(p,state,today)
            p['state']=state;p['quarantine_date']=today
            unknown.append(p);counts[state]+=1;retired+=1
            blocked.add(p['permno'])
            blocked.update(int(e['dispermno']) for e in events if finite(e.get('dispermno')) and e['dispermno']!=0)
            # Exit execution/cost is not independently established. Nullable
            # primitives record the unresolved obligation, not a zero fee.
            emit(p,'fixed',None,'unresolved_exit_execution_obligation')
            emit(p,'impact',None,'unresolved_exit_execution_obligation')
        # Persisting unknown asset bundles are never recovered from later prices.
        for p in unknown:
            emit(p,'gross',None,'persistent_unidentified_asset_and_claim_residual')
            if p['side']=='short':
                b=borrow_primitive(p['basis'],(today-previous).days)
                emit(p,'borrow',b,'known_entry_basis_unresolved_short' if finite(b) else 'unknown_queued_short_basis')
        survivors=[]
        for p in book:
            q=p['q']; before=src.opening(p['permno'],previous); opening=src.opening(p['permno'],today)
            events=src.events.get((p['permno'],today),[])
            terms=event_batch(events,src.row(p['permno'],today),src.delists.get((p['permno'],today),[]),today)
            for e in terms['cash']:
                cash=q*float(e['disdivamt']); claim_count+=1
                emit(p,'gross',cash,'established_prior_owned_basis_entitlement',quantity=q,
                     event_sequence=int(e['disseqnbr']),payment_date=e.get('dispaydt'))
                actual_claims.append((p['key'],today,round(cash,8)))
            asset=(None if terms['unknown'] else terminal_asset_increment(q,before) if terms['terminal']
                   else asset_increment(q,before,opening,terms['multiplier']))
            # Terminal cash is already the disjoint claim component above;
            # the prior-parent decrement appears once only for verified replacement.
            emit(p,'gross',asset,'verified_cash_replacement_parent_component' if terms['terminal'] else
                 'unknown_event_asset_residual' if terms['unknown'] else
                 'adjacent_open_asset_increment' if finite(asset) else 'missing_adjacent_open_mark',
                 quantity=q,previous_open=before,opening=opening,multiplier=terms['multiplier'])
            wealth=finite(asset); nwealth+=wealth;basis_measured+=p['basis']*wealth
            expense=True
            if p['side']=='short':
                b=borrow_primitive(p['basis'],(today-previous).days)
                emit(p,'borrow',b,'verified_original_short_basis_act365');expense=finite(b)
            if terms['unknown']:
                quarantine(p,terms['unknown'],events);expense=False
            elif terms['terminal']:
                check_state(p,'measurable_cash_termination',today);terminal_cash+=1;retired+=1
            else:
                p['q']=q*terms['multiplier']
                if today>=p['scheduled_exit_date']:
                    delay=idx-src.index[p['scheduled_exit_date']];assert 0<=delay<=5
                    if positive_open(opening):
                        check_state(p,'assumed_exited',today,p['q'])
                        expense=execution(p,'exit',p['q']) and expense
                        verified_exit+=1;retired+=1
                    elif delay==5:
                        quarantine(p,'five_global_date_cap_failure',[]);expense=False
                    else: survivors.append(p)
                else: survivors.append(p)
            ncomplete+=wealth and expense
        book=survivors
        for p in queued:
            opening=src.opening(p['permno'],today)
            if not positive_open(opening):
                check_state(p,'canceled_entry',today);canceled+=1;retired+=1;continue
            events=src.events.get((p['permno'],today),[])
            try: multiplier=verified_entry_multiplier(events)
            except EntryBasisUnidentified:
                check_state(p,'queued_execution_quantity_unresolved',today)
                p.update(q=None,basis=None,state='queued_execution_quantity_unresolved',quarantine_date=today)
                unknown.append(p);counts[p['state']]+=1;retired+=1
                blocked.add(p['permno'])
                blocked.update(int(e['dispermno']) for e in events if finite(e.get('dispermno')) and e['dispermno']!=0)
                execution(p,'queued_entry_unknown',None)
                emit(p,'gross',None,'unknown_queued_entry_quantity_and_claims')
                continue
            p['q']=p['order_shares']*multiplier;p['basis']=abs(p['q'])*opening
            p['state']='outstanding'
            np.testing.assert_allclose(p['basis'],p['expected_entry_notional'],rtol=1e-12,atol=1e-8)
            assert p['expected_actual_entry_date']==today
            execution(p,'entry',p['q']);book.append(p);verified_entries+=1
        # Reconciliation is accounting QA only; future terminal data have not
        # influenced event classification, quantity, execution, prices or costs.
        reference=cov.loc[today]
        assert len(unknown)==reference.unresolved_positions
        r_exec=sum(p['basis'] for p in unknown if finite(p['basis']))
        r_proxy=sum(p['planned_entry_notional'] for p in unknown if not finite(p['basis']))
        np.testing.assert_allclose(r_exec,reference.verified_executed_reserve_long+reference.verified_executed_reserve_short,rtol=1e-12,atol=1e-6)
        np.testing.assert_allclose(r_proxy,reference.unresolved_queued_proxy_commitment,rtol=1e-12,atol=1e-6)
        assert len(book)==reference.verified_outstanding_inventory_positions
        assert ninterval==reference.component_intervals
        assert nwealth==reference.wealth_measurable_intervals
        if today>=date(2003,1,3):
            d=daily.result();d.update(candidate=candidate,date=today,year=year,
                conditional_measured_component_return=d['net']/CAPITAL if finite(d['net']) else None,
                reference_capital=CAPITAL,asset_intervals=ninterval,identified_asset_intervals=nwealth,
                complete_component_intervals=ncomplete,
                asset_coverage=nwealth/ninterval if ninterval else 1.,
                complete_component_coverage=ncomplete/ninterval if ninterval else 1.,
                verified_entry_basis_denominator=basis_den,identified_entry_basis=basis_measured,
                verified_entry_basis_coverage=basis_measured/basis_den if basis_den else 1.,
                verified_execution_notional=turnover,verified_execution_count=leg_count,
                verified_turnover=turnover/CAPITAL,conventional_one_way_turnover=turnover/CAPITAL/2,
                newly_established_fixed_claims=claim_count,
                unknown_full_account_residual=d['net_unknown_count']>0 or bool(unknown),market_value_coverage=None)
            # Original Stage4F eligibility/reserve/phase budget fields accompany
            # contributions, without being used to construct them.
            for col,value in reference.items():
                if col not in d:d[col]=value
            rows.append(d)
        if idx%63==0:
            print(f'{candidate} {today}: {verified_entries:,} verified entries; {len(unknown)} unknown obligations; reconciliation passed',flush=True)
    validate_year()
    writer.close();journal_count+=writer.count
    for p in book:check_state(p,'outstanding',end,p['q']) if end==date(2019,12,31) else None
    if end==date(2019,12,31):
        original=json.loads((frozen/'manifest.json').read_text())
        assert verified_entries==original['entered'] and verified_exit==original['market_exited']
        assert terminal_cash==original['cash_termination'] and canceled==original['canceled_entry']
        assert submitted_count==original['submitted']
        assert len(unknown)==original['unresolved_positions_created']
        assert len(book)==original['remaining_verified_positions_at_2019_boundary']
        assert sum(map(len,pending.values()))==original['pending_development_orders_at_2019_boundary']
        assert len(rows)==4278
    frame=pd.DataFrame(rows);assert not frame.duplicated(['candidate','date']).any()
    frame.to_parquet(out/'daily_contributions.parquet',index=False)
    summary=dict(candidate=candidate,scope=tag,calendar_dates=len(frame),journal_rows=journal_count,
        verified_entries=verified_entries,market_exits=verified_exit,cash_terminations=terminal_cash,
        canceled_entries=canceled,unresolved_positions=len(unknown),
        queued_execution_quantity_unresolved=counts['queued_execution_quantity_unresolved'],
        exact_orders_execution_claims_reserves_reconciled=True,
        remaining_inventory=len(book),pending_orders=sum(p['signal_date']<=end for v in pending.values() for p in v),
        numeric_dates=int(frame.net.notna().sum()),all_calendar_rows_preserved=True,
        holdout_outcome_rows_read=0,raw_scanned=False,wrds_queries=0,
        full_account_wealth_identified=False,candidate_selected=False)
    (out/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def run(end=date(2019,12,31)):
    if not date(2003,1,3) <= end <= date(2019,12,31):
        raise ValueError('Stage4G is development only: 2003-01-03 through 2019-12-31')
    before=protected();src=DevelopmentSources()
    tag='bounded' if end<date(2019,12,31) else 'development'
    out=ROOT/'data/interim/stage4g'/tag;out.mkdir(parents=True,exist_ok=True)
    path=out/'manifest.json';path.write_text(json.dumps({'qa_passed':False,'status':'RUNNING'})+'\n')
    results=[]
    try:
        for candidate in CANDIDATES:
            src.year=None;src.records={};src.previous_tail={}
            results.append(replay_candidate(src,candidate,end))
        assert before==protected(),'Protected earlier artifacts changed'
        path.write_text(json.dumps(dict(qa_passed=True,status='COMPLETE',results=results,
            protected_hashes=before,cache_checksums=src.cache_checksums,
            original_development_keys=3829908,forecast_checksums_verified=68,
            no_holdout_outcomes=True,raw_scanned=False,wrds_queries=0),indent=2)+'\n')
    except Exception as e:
        path.write_text(json.dumps(dict(qa_passed=False,status='FAILED',error_class=type(e).__name__,
            error=str(e),completed_candidates=results),indent=2)+'\n')
        raise
    finally:src.c.close()
    return results
