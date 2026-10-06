"""Development-only conditional execution audit. No returns/target projections."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from .construction import plan
from .fallback import positive_open, entry_assumption, verified_split_multiplier
from .settlement import (SCENARIOS, PARENT, SUCCESSOR, EVENT_DATE, QUOTE_DATE,
                         certify_reference, applies, entitlement, credit_cash,
                         delivery_gated_exit)

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ('uni_reversal_5', 'ridge')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def protected_hashes():
    paths = []
    for folder in ('data/interim/stage4a', 'data/interim/stage4a_continuation',
                   'data/interim/stage4b', 'data/interim/stage4c',
                   'results/tables/stage4a', 'results/tables/stage4b',
                   'results/tables/stage4c', 'results/tables/stage4d',
                   'results/figures/stage4a', 'results/figures/stage4b'):
        paths += [p for p in (ROOT/folder).rglob('*') if p.is_file()]
    paths += [p for p in (ROOT/'docs').glob('stage4[abcd]*.md')]
    paths += [ROOT/'docs/methodology.md']
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


class Sources:
    """One reusable yearly source cache; no holdout signals or outcomes."""
    def __init__(self):
        self.cache = ROOT/'data/interim/stage4e_scenarios'
        self.cache.mkdir(parents=True, exist_ok=True)
        self.c = duckdb.connect()
        self.c.execute('SET threads=2')
        self.parts = str(ROOT/'data/interim/reconstruction_diagnostic_parts/part_*.parquet')
        self.forecasts = str(ROOT/'data/interim/stage3a/predictions/*.parquet')
        self.daily_sources = {str(p.relative_to(ROOT)): [p.stat().st_size, p.stat().st_mtime_ns]
                              for p in sorted((ROOT/'data/interim/reconstruction_diagnostic_parts').glob('*.parquet'))}
        self.source_files = ['data/interim/stage3a/calendar.parquet',
            'data/interim/stage2a_events/stkdistributions.parquet',
            'data/interim/stage2a_events/stkdelists.parquet']
        self.event_hashes = {p: digest(ROOT/p) for p in self.source_files}
        m = json.loads((ROOT/'data/interim/stage3a/manifest.json').read_text())
        for i in range(1, 69):
            p = ROOT/f'data/interim/stage3a/predictions/fold_{i:02d}.parquet'
            assert digest(p) == m['folds'][str(i)]['hashes']['predictions']
        for x in json.loads((ROOT/'data/interim/stage3a/source_manifest.json').read_text())['input_fingerprints']:
            p = ROOT/x['path']
            assert [p.stat().st_size, p.stat().st_mtime_ns] == [x['size'], x['mtime_ns']]
        counts = self.c.execute(f"SELECT count(*), count(DISTINCT(permno,signal_date)), count(DISTINCT signal_date) FROM read_parquet('{self.forecasts}') WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2019-12-31'").fetchone()
        assert counts == (3829908, 3829908, 4279)
        self.counts = counts
        self.calendar = self.c.execute(f"SELECT signal_date::DATE d FROM read_parquet('{ROOT}/data/interim/stage3a/calendar.parquet') WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2020-01-16' ORDER BY 1").fetchdf().d.dt.date.tolist()
        self.index = {d:i for i,d in enumerate(self.calendar)}
        self.development = [d for d in self.calendar if d.year <= 2019]
        assert len(self.development) == 4279
        self.records = {}; self.year = None; self.signal_groups = {}; self.event_groups = {}; self.delists = None
        q = self.c.execute(f"SELECT permno,dlycaldt,dlyprc,dlyprcflg FROM read_parquet('{self.parts}') WHERE permno={SUCCESSOR} AND dlycaldt=DATE '{QUOTE_DATE}'").fetchdf()
        q.dlycaldt = q.dlycaldt.dt.date
        certify_reference(q.to_dict('records'))
        self.reference = q.to_dict('records')[0]

    def load(self, year, owned=None):
        if self.year == year:
            return
        # 2020 can contain only settlement records for pre-existing development positions.
        narrow = ''
        end = f'{year}-12-31'
        if year == 2020:
            assert owned is not None
            ids = sorted({int(p['asset_permno']) for p in owned} | {int(p['permno']) for p in owned})
            if not ids:
                return
            narrow = ' AND permno IN (' + ','.join(map(str, ids)) + ')'
            end = '2020-01-16'
        else:
            assert 2003 <= year <= 2019
        key = hashlib.sha256(json.dumps([self.daily_sources, self.event_hashes, year, narrow], sort_keys=True).encode()).hexdigest()[:16]
        target = self.cache/f'daily_{year}_{key}.parquet'
        if not target.exists():
            temp = target.with_suffix('.tmp.parquet')
            self.c.execute(f"COPY (SELECT permno,dlycaldt,dlyprc,dlyopen,adv20,dlyorddivamt,dlynonorddivamt FROM read_parquet('{self.parts}') WHERE dlycaldt BETWEEN DATE '{year}-01-01' AND DATE '{end}' {narrow}) TO '{temp}' (FORMAT PARQUET)")
            temp.replace(target)
        f = pd.read_parquet(target)
        assert not f.duplicated(['permno','dlycaldt']).any()
        self.records = {(int(x.permno), pd.Timestamp(x.dlycaldt).date()):x for x in f.itertuples()}
        e = self.c.execute(f"SELECT * FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdistributions.parquet') WHERE disexdt BETWEEN DATE '{year}-01-01' AND DATE '{end}' {narrow} ORDER BY disexdt,permno,disseqnbr").fetchdf()
        e.disexdt = e.disexdt.dt.date
        self.event_groups = {d:g.to_dict('records') for d,g in e.groupby('disexdt')}
        self.delists = self.c.execute(f"SELECT * FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdelists.parquet') WHERE (delistingdt BETWEEN DATE '{year}-01-01' AND DATE '{end}' OR deldlydt BETWEEN DATE '{year}-01-01' AND DATE '{end}' OR delamtdt BETWEEN DATE '{year}-01-01' AND DATE '{end}') {narrow}").fetchdf()
        self.signal_groups = {}
        if year <= 2019:
            g = self.c.execute(f"SELECT permno,signal_date::DATE signal_date,entry_date::DATE entry_date,exit_date::DATE exit_date,ridge,uni_reversal_5 FROM read_parquet('{self.forecasts}') WHERE signal_date BETWEEN DATE '{year}-01-01' AND DATE '{year}-12-31' ORDER BY signal_date,permno").fetchdf()
            for col in ('signal_date','entry_date','exit_date'):
                g[col] = g[col].dt.date
            self.signal_groups = {d:v.reset_index(drop=True) for d,v in g.groupby('signal_date')}
        self.year = year
        print(f'Cached sources loaded: {year}; {len(f):,} daily rows, {len(e):,} events', flush=True)

    def row(self, permno, date):
        return self.records.get((int(permno), date))

    def opening(self, permno, date):
        r = self.row(permno, date)
        return None if r is None else r.dlyopen


def focused(src):
    """All six original obligations, independently under every scenario."""
    original = pd.read_parquet(ROOT/'data/interim/stage4b/assumed_orders_and_execution_states.parquet')
    original = original[original.state == 'unresolved_execution']
    assert len(original) == 6 and set(original.permno) == {PARENT}
    src.load(2003)
    output = []
    for scenario in SCENARIOS:
        for r in original.itertuples():
            x = entitlement(r.last_verified_parent_shares, scenario)
            scheduled = pd.Timestamp(r.scheduled_exit_date).date()
            opens = {d:src.opening(SUCCESSOR, d) for d in src.calendar if scheduled <= d <= src.calendar[src.index[scheduled]+5]}
            result = delivery_gated_exit(src.calendar, scheduled, x['credit_date'], opens)
            assert src.calendar[src.index[scheduled]+5] == pd.Timestamp(r.five_day_deadline).date()
            claim = {'amount':x['fractional_cash'], 'credit_date':x['credit_date'], 'credited':False}
            assert credit_cash(claim, QUOTE_DATE) == 0
            assert credit_cash(claim, x['credit_date']) == x['fractional_cash']
            assert credit_cash(claim, x['credit_date']) == 0
            output.append({'scenario':scenario, 'candidate':r.candidate,
                'signal_date':pd.Timestamp(r.signal_date).date(), 'side':r.side,
                'scheduled_exit_date':scheduled, 'deadline':r.five_day_deadline,
                'delivery_date':x['credit_date'], 'whole_ads':int(x['whole_ads']),
                'fractional_ads':str(x['fractional_ads']), 'fractional_cash':str(x['fractional_cash']),
                'cash_credit_date':x['credit_date'], 'state':result['state'],
                'actual_exit_date':result['date'], 'delay':result['delay'],
                'cash_reference_semantics':'approved_hypothetical_crsp_close_not_wsj_certified',
                'quantity_identity_passed':True})
    f = pd.DataFrame(output)
    assert len(f) == 18 and not f.duplicated(['scenario','candidate','signal_date']).any()
    assert (f.state == 'assumed_exited').all()
    f.to_parquet(src.cache/'focused_six_cohorts.parquet', index=False)
    return f


def apply_actions(pos, terms, date, src, scenario):
    """Prior-owned basis: actions before trades, including exit-day rights."""
    same = [e for e in terms if e['permno'] == pos['asset_permno']]
    if not same:
        return
    q0 = pos['current_shares']
    for e in same:
        multiplier = verified_split_multiplier(e)
        fixed = (e['dispaymenttype'] == 'USD' and e['distype'] in ('CD','SD','ROC','CG')
                 and e['disfacshr'] == 0 and e['disfacpr'] == 0
                 and pd.notna(e['disdivamt']) and np.isfinite(e['disdivamt']))
        dl = src.delists
        cash_terminal = (e['dispaymenttype'] == 'USD' and e['distype'] == 'CP'
            and ((dl.permno == pos['asset_permno']) & (dl.delpaymenttype == 'CASH')
                 & (dl.delstatustype == 'FPAY') & dl.deldistype.isin(['D1','D2'])
                 & (dl.delretmisstype == 'NA') & (dl.deldlydt.dt.date == date)
                 & (dl.delamtdt.dt.date <= date)).any())
        if applies(e):
            x = entitlement(pos['current_shares'], scenario)
            pos['merger_parent_quantity'] = pos['current_shares']
            pos['ads_equivalent'] = str(x['ads_equivalent'])
            pos['whole_ads_entitlement'] = int(x['whole_ads'])
            pos['fractional_ads'] = str(x['fractional_ads'])
            pos['fractional_cash'] = str(x['fractional_cash'])
            pos['delivery_date'] = x['credit_date']
            pos['asset_permno'] = SUCCESSOR
            pos['current_shares'] = float(x['whole_ads'])
            pos['scenario_cash_claim'] = {'amount':x['fractional_cash'],
                'credit_date':x['credit_date'], 'credited':False}
            pos['settlement_scenario'] = scenario
        elif multiplier is not None:
            pos['current_shares'] *= multiplier
            pos['split_events'] += 1
        elif fixed:
            pos['cash_claims'].append({'effective_date':date,
                'payment_date':None if pd.isna(e['dispaydt']) else pd.Timestamp(e['dispaydt']).date(),
                'signed_amount':q0*float(e['disdivamt']), 'prior_share_basis':q0,
                'sequence':e['disseqnbr'], 'source':'global_crsp_fixed_cash_terms'})
        elif cash_terminal:
            cash_terms = [z for z in same if z['dispaymenttype'] == 'USD']
            if not all(pd.notna(z['disdivamt']) and np.isfinite(z['disdivamt']) and z['disdivamt'] >= 0 for z in cash_terms):
                raise ValueError('Unmeasurable cash termination')
            amount = sum(z['disdivamt'] for z in cash_terms)
            daily = src.row(pos['asset_permno'], date)
            matched = dl[(dl.permno == pos['asset_permno']) & (dl.deldlydt.dt.date == date)]
            if (daily is None or len(matched) != 1
                    or abs(amount-daily.dlyorddivamt-daily.dlynonorddivamt) >= 1e-5
                    or abs(amount-matched.iloc[0].deldivamt) >= 1e-5):
                raise ValueError('Cash-event reconciliation failure')
            pos['cash_claims'].append({'effective_date':date,
                'signed_amount':q0*amount, 'source':'verified_terminal_cash_replacement'})
            pos['state'] = 'measurable_cash_termination'
            pos['actual_exit_date'] = date
            pos['current_shares'] = 0.
            pos['resolution_reason'] = 'independent_cash_replacement_not_market_trade'
            break
        else:
            pos['state'] = 'unresolved_execution'
            pos['unresolved_known_date'] = date
            pos['resolution_reason'] = 'unsupported_corporate_action_quantity_or_terms'
            pos['unknown_event_type'] = e['distype']
            pos['unknown_payment_type'] = e['dispaymenttype']
            pos['unknown_detail_type'] = e['disdetailtype']
            pos['unknown_successor_permno'] = e['dispermno']
            pos['last_verified_quantity'] = pos['current_shares']
            pos['current_shares'] = None
            break


def audit_candidate(src, scenario, candidate):
    """Actual chronological orders until persistent halt, not a virtual book."""
    src.year = None
    book = []; orders = []; claims = []; states = []; halt = None
    submitted = {}; operated = 0; processed = 0
    for date in src.calendar:
        if halt is not None and not book and not claims and not submitted:
            break
        src.load(date.year, book if date.year == 2020 else None)
        terms = src.event_groups.get(date, [])
        for pos in list(book):
            if pos['state'] != 'outstanding':
                continue
            apply_actions(pos, terms, date, src, scenario)
            if (pos.get('scenario_cash_claim') is not None
                    and not pos['scenario_cash_claim']['credited'] and pos not in claims):
                claims.append(pos)
            if pos['state'] == 'unresolved_execution':
                halt = halt or date
        # Credit remains independent of inventory liquidation; no receivable double count.
        for pos in list(claims):
            claim = pos['scenario_cash_claim']
            credit_cash(claim, date)
            if claim['credited']:
                pos['fractional_cash_credit_date'] = date
                claims.remove(pos)
        for order in submitted.pop(date, []):
            opening = src.opening(order['permno'], date)
            order['entry_status'] = entry_assumption(opening)
            if order['entry_status'] == 'canceled_missing_open':
                order['state'] = 'canceled_entry'
                order['resolution_reason'] = 'scheduled_entry_not_positive_no_fill'
                continue
            q = order['order_shares']
            for e in terms:
                if e['permno'] == order['permno']:
                    mult = verified_split_multiplier(e)
                    if mult is not None:
                        q *= mult
            order['current_shares'] = q
            order['entry_notional'] = abs(q)*opening
            order['actual_entry_date'] = date
            order['state'] = 'outstanding'; book.append(order)
        for pos in list(book):
            if pos['state'] != 'outstanding' or date < pos['scheduled_exit_date']:
                continue
            lag = src.index[date]-src.index[pos['scheduled_exit_date']]
            assert lag <= 5
            deliverable = pos.get('delivery_date') is None or date >= pos['delivery_date']
            open_value = src.opening(pos['asset_permno'], date)
            if deliverable and (pos['current_shares'] == 0 or positive_open(open_value)):
                pos['executed_asset_quantity'] = pos['current_shares']
                pos['current_shares'] = 0.
                pos['state'] = 'assumed_exited'
                pos['actual_exit_date'] = date; pos['delay'] = lag
                pos['resolution_reason'] = 'delivery_gated_successor_open' if pos.get('delivery_date') else ('scheduled_open' if lag == 0 else 'first_positive_open_within_five')
            elif lag == 5:
                pos['state'] = 'unresolved_execution'
                pos['unresolved_known_date'] = date
                pos['resolution_reason'] = 'no_deliverable_positive_open_within_original_five_date_cap'
                halt = halt or date
        book = [p for p in book if p['state'] == 'outstanding']
        if date.year <= 2019:
            operational = halt is None
            operated += int(operational)
            states.append({'scenario':scenario, 'candidate':candidate, 'decision_date':date,
                           'operational':operational})
        if halt is not None:
            continue
        if date not in src.signal_groups:
            continue
        g = src.signal_groups[date]
        tomorrow = src.calendar[src.index[date]+1]
        gross = {}
        for pos in book:
            if pos['scheduled_exit_date'] <= tomorrow:
                p = pos['asset_permno']; gross[p] = gross.get(p, 0.)+abs(pos['current_shares'])
        price = np.array([src.row(p, date).dlyprc if src.row(p, date) else np.nan for p in g.permno])
        adv = np.array([src.row(p, date).adv20 if src.row(p, date) else np.nan for p in g.permno])
        exits = np.array([gross.get(int(p), 0.) for p in g.permno])
        sides, dollars, reasons = plan(g[candidate], price, adv, exits)
        processed += len(g)
        for i, r in enumerate(g.itertuples()):
            if dollars[i] == 0:
                continue
            order = {'scenario':scenario, 'candidate':candidate, 'permno':int(r.permno),
                'asset_permno':int(r.permno), 'signal_date':date,
                'scheduled_entry_date':r.entry_date, 'scheduled_exit_date':r.exit_date,
                'deadline':src.calendar[src.index[r.exit_date]+5],
                'side':'long' if dollars[i] > 0 else 'short',
                'planned_entry_notional':abs(dollars[i]), 'order_shares':dollars[i]/price[i],
                'current_shares':None, 'state':'submitted', 'entry_status':'pending',
                'entry_notional':None, 'actual_entry_date':None, 'actual_exit_date':None,
                'delay':None, 'split_events':0, 'cash_claims':[], 'unresolved_known_date':None,
                'resolution_reason':None}
            orders.append(order); submitted.setdefault(r.entry_date, []).append(order)
        if date.month == 1 and date.day <= 4:
            print(f'{scenario}/{candidate}: decision {date}, {len(orders):,} submitted orders', flush=True)
    # Unknown account state has no new independently established termination convention.
    present = {s['decision_date'] for s in states}
    states += [{'scenario':scenario, 'candidate':candidate, 'decision_date':d,
                'operational':False} for d in src.development if d not in present]
    assert len(states) == 4279
    frame = pd.DataFrame(orders)
    assert not frame.duplicated(['permno','signal_date']).any()
    assert set(frame.state) <= {'assumed_exited','measurable_cash_termination','unresolved_execution','canceled_entry'}
    frame['holding_global_days'] = [None if pd.isna(a) or pd.isna(b) else src.index[b]-src.index[a]
                                   for a,b in zip(frame.actual_entry_date, frame.actual_exit_date)]
    market = frame[frame.state == 'assumed_exited']
    assert market.delay.between(0,5).all()
    assert (market.holding_global_days == 5+market.delay).all()
    assert (market.current_shares == 0).all()
    for r in market.itertuples():
        assert positive_open(src.opening(r.asset_permno, r.actual_exit_date)) or r.executed_asset_quantity == 0
        delivery = getattr(r, 'delivery_date', None)
        if pd.isna(delivery):
            delivery = r.scheduled_exit_date
        assert r.actual_exit_date >= delivery
        assert all(d < delivery or not positive_open(src.opening(r.asset_permno, d))
                   for d in src.calendar[src.index[r.scheduled_exit_date]:src.index[r.actual_exit_date]])
    assert not frame.loc[frame.state == 'canceled_entry', 'actual_entry_date'].notna().any()
    affected = frame[frame.settlement_scenario.notna()] if 'settlement_scenario' in frame else frame.iloc[:0]
    assert len(affected) == 3
    assert affected.current_shares.eq(0).all()
    assert affected.fractional_cash_credit_date.eq(SCENARIOS[scenario]).all()
    # Before the merger, new adapter must reproduce original submission keys/quantities.
    old = pd.read_parquet(ROOT/'data/interim/stage4b/assumed_orders_and_execution_states.parquet',
                          columns=['candidate','permno','signal_date','order_shares'])
    old = old[(old.candidate == candidate) & (pd.to_datetime(old.signal_date) < pd.Timestamp(EVENT_DATE))]
    old['signal_date'] = pd.to_datetime(old.signal_date)
    pre = frame[frame.signal_date < EVENT_DATE].copy()
    pre['signal_date'] = pd.to_datetime(pre.signal_date)
    z = pre.merge(old, on=['candidate','permno','signal_date'], suffixes=('','_old'), validate='one_to_one')
    assert len(z) == len(old) == len(pre)
    np.testing.assert_allclose(z.order_shares, z.order_shares_old, rtol=0, atol=1e-10)
    unresolved = frame[frame.state == 'unresolved_execution']
    canceled = frame[frame.state == 'canceled_entry']
    summary = {'scenario':scenario, 'candidate':candidate,
        'original_development_keys':3829908, 'development_decision_dates':4279,
        'processed_pre_halt_eligible_keys':processed, 'submitted_orders':len(frame),
        'merger_cohorts_resolved':int((affected.state == 'assumed_exited').sum()),
        'merger_cohorts_unresolved':int((affected.state == 'unresolved_execution').sum()),
        'missing_entries_canceled':len(canceled),
        'market_exited_orders':len(market),
        'measurable_cash_terminations':int((frame.state == 'measurable_cash_termination').sum()),
        'canceled_entry_close_sized_notional':float(canceled.planned_entry_notional.sum()),
        'unresolved_positions':len(unresolved), 'unresolved_permnos':int(unresolved.permno.nunique()),
        'unresolved_longs':int((unresolved.side == 'long').sum()),
        'unresolved_shorts':int((unresolved.side == 'short').sum()),
        'first_halt_decision_close':str(halt) if halt else '',
        'operational_decision_dates':operated, 'operational_fraction':operated/4279,
        'persistent_halt':halt is not None,
        'full_period_execution_feasible':halt is None and unresolved.empty,
        'full_portfolio_accounting_certified':False,
        'performance_computed':False,
        **{f'exits_delay_{k}':int((frame.delay == k).sum()) for k in range(6)}}
    out = src.cache/scenario/candidate; out.mkdir(parents=True, exist_ok=True)
    # JSON claim histories retained separately: nested heterogeneous data not coerced away.
    (out/'owned_claims.json').write_text(json.dumps([{'permno':p['permno'], 'signal_date':p['signal_date'],
        'ordinary_claims':p['cash_claims'], 'merger_claim':p.get('scenario_cash_claim')}
        for p in orders if p['cash_claims'] or p.get('scenario_cash_claim')], default=str, indent=2)+'\n')
    serial = frame.drop(columns=['cash_claims','scenario_cash_claim'], errors='ignore')
    serial.to_parquet(out/'orders_and_execution_states.parquet', index=False)
    pd.DataFrame(states).sort_values('decision_date').to_parquet(out/'operational_decision_states.parquet', index=False)
    unresolved.drop(columns=['cash_claims','scenario_cash_claim'], errors='ignore').to_parquet(out/'unresolved_positions.parquet', index=False)
    (out/'manifest.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary), flush=True)
    return summary, frame


def run():
    before = protected_hashes()
    src = Sources()
    f = focused(src)
    folder = ROOT/'results/tables/stage4e'; folder.mkdir(parents=True, exist_ok=True)
    f.to_csv(folder/'conditional_merger_cohort_accounting.csv', index=False)
    summaries = []; delays = []; durations = []; unresolved_rows = []
    for scenario in SCENARIOS:
        for candidate in CANDIDATES:
            summary, frame = audit_candidate(src, scenario, candidate)
            actual = frame[frame.settlement_scenario.notna()].copy()
            expected = f[(f.scenario == scenario) & (f.candidate == candidate)]
            joined = actual.merge(expected, on=['scenario','candidate','signal_date'],
                                  suffixes=('_actual','_focused'), validate='one_to_one')
            assert len(joined) == 3
            assert joined.actual_exit_date_actual.eq(joined.actual_exit_date_focused).all()
            assert joined.delay_actual.eq(joined.delay_focused).all()
            assert joined.fractional_cash_actual.eq(joined.fractional_cash_focused).all()
            assert joined.whole_ads_entitlement.eq(joined.whole_ads).all()
            expected_claims = (actual.scheduled_entry_date < pd.Timestamp('2003-03-26').date()).astype(int)
            assert actual.cash_claims.map(len).eq(expected_claims).all(), 'Prior parent cash entitlement changed'
            summaries.append(summary)
            delays.append(frame.groupby(['scenario','candidate','side','state','delay'], dropna=False).size().rename('observations').reset_index())
            durations.append(frame.groupby(['scenario','candidate','side','state','holding_global_days'], dropna=False).size().rename('observations').reset_index())
            u = frame[frame.state == 'unresolved_execution']
            if len(u):
                unresolved_rows.append(u.groupby(['scenario','candidate','unresolved_known_date','side','resolution_reason'], dropna=False).agg(observations=('permno','size'), distinct_permnos=('permno','nunique')).reset_index())
        pd.DataFrame(summaries).to_csv(folder/'conditional_feasibility_summary.csv', index=False)
    pd.concat(delays, ignore_index=True).to_csv(folder/'conditional_exit_delay_distribution.csv', index=False)
    pd.concat(durations, ignore_index=True).to_csv(folder/'conditional_holding_durations.csv', index=False)
    if unresolved_rows:
        pd.concat(unresolved_rows, ignore_index=True).to_csv(folder/'conditional_unresolved_summary.csv', index=False)
    else:
        pd.DataFrame(columns=['scenario','candidate','observations']).to_csv(folder/'conditional_unresolved_summary.csv', index=False)
    assert before == protected_hashes(), 'Earlier findings/artifacts changed'
    manifest = {'qa_passed':True, 'conditional_simulation_only':True,
        'performance_computed':False, 'wrds_queries':0, 'raw_scanned':False,
        'holdout_signals_or_outcomes_accessed':False, 'historical_D_M_identified':False,
        'reference_is_wsj_certified':False, 'hypothetical_crsp_reference':str(src.reference['dlyprc']),
        'protected_artifact_hashes':before, 'source_fingerprints':src.daily_sources,
        'event_and_calendar_hashes':src.event_hashes, 'forecast_hashes_verified':68,
        'construction_timestamp_utc':pd.Timestamp.now(tz='UTC').isoformat(), 'summaries':summaries}
    (src.cache/'feasibility_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    src.c.close()
    return summaries
