"""Sequential Stage5 training maturity adapter; frozen target inputs only."""
import json
from pathlib import Path
import pandas as pd
from src.features.panel import ROOT, FEATURES
from src.evaluation.baseline import sha
from src.models.stage3a_pipeline import verify_sources

CACHE=ROOT/'data/interim/stage5'
OUT=ROOT/'results/tables/stage5'
START='2020-01-02'; END='2025-12-31'
TARGET=ROOT/'data/interim/stage1g_targets/targets_5d.parquet'
FEATURE=ROOT/'data/interim/stage2a_features/parts/part_*.parquet'


def frozen_sources():
    dev=verify_sources()
    sm=json.loads((ROOT/'data/interim/stage2a_features/manifest.json').read_text())
    assert sm['complete'] and sm['qa_passed']
    for r in sm['final_files']:assert sha(ROOT/r['file'])==r['sha256']
    # Preserve all existing frozen development/public accounting artifacts.
    protected={}
    for group in ['data/interim/stage3a','results/tables/stage2b','results/tables/stage3a',
                  'results/figures/stage2b','results/figures/stage3a']:
        for p in (ROOT/group).rglob('*'):
            if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    for group in ['results/tables','results/figures','docs']:
        pattern='stage4*' if group=='docs' else 'stage4*/*'
        for p in (ROOT/group).glob(pattern):
            if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    inputs=[TARGET,ROOT/'data/interim/stage2a_features/manifest.json',
            ROOT/'data/interim/stage1g_extraction/event_resolution_cases.parquet',
            ROOT/'data/interim/stage1g_extraction/stkdistributions.parquet',
            ROOT/'data/interim/reconstruction_diagnostic_daily.parquet',
            ROOT/'data/interim/stage2a_events/stkdistributions.parquet',
            ROOT/'data/interim/reconstruction_diagnostic_parts/part_00.parquet']
    inputs += [ROOT/r['file'] for r in sm['final_files']]
    fingerprints=[dict(path=str(p.relative_to(ROOT)),size=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns) for p in inputs]
    return dict(input_fingerprints=fingerprints,protected_hashes=protected,development_source=dev,
                target_sha256=sha(TARGET),features_verified=32)


def extend_training(c, cutoff, previous_signal, features_relation='f'):
    """Read only newly mature past labels; prove ledger maturity before moments.

    Mirrors Stage3A proof (effective-date daily cash evidence and pre-exit
    terminal payment). No future prediction/evaluation labels enter this API.
    """
    cut=str(pd.Timestamp(cutoff).date());lo=str(pd.Timestamp(previous_signal).date())
    c.execute(f"""CREATE OR REPLACE TEMP TABLE train_labels AS SELECT * FROM read_parquet('{TARGET}')
        WHERE signal_date>DATE '{lo}' AND signal_date<=DATE '{cut}'
        AND exit_date<=DATE '{cut}' AND isfinite(target_5d)""")
    assert c.execute(f"SELECT count(*) FROM train_labels WHERE exit_date>DATE '{cut}' OR signal_date>DATE '{cut}'").fetchone()[0]==0
    c.execute(f"""CREATE OR REPLACE TEMP TABLE e AS SELECT e.* FROM
        read_parquet('{ROOT/'data/interim/stage1g_extraction/event_resolution_cases.parquet'}') e
        SEMI JOIN train_labels l USING(permno,signal_date)""")
    cash=c.execute("""SELECT count(*),count(*) FILTER(WHERE NOT coalesce(e.resolved AND
        e.resolution='resolved_cash_claim_by_exit' AND e.actual_delist_in_window AND e.delamtdt<=l.exit_date
        AND e.terminal_cash_count>=1 AND e.delpaymenttype='CASH' AND e.delstatustype='FPAY'
        AND e.delretmisstype='NA',false)) FROM train_labels l LEFT JOIN e USING(permno,signal_date)
        WHERE l.label_status='measurable_cash_only_delisting'""").fetchone()
    assert cash[1]==0,'Frozen cash-ledger maturity proof contradicted'
    c.execute(f"""CREATE OR REPLACE TEMP TABLE used_events AS SELECT l.permno,l.signal_date,l.exit_date,
        s.disexdt::DATE event_date,s.disseqnbr,s.dispaymenttype,s.disdivamt,s.distype,
        s.dispaydt::DATE pay_date,(s.disexdt=e.deldlydt AND e.resolution='resolved_cash_claim_by_exit') terminal
        FROM train_labels l JOIN e USING(permno,signal_date)
        JOIN read_parquet('{ROOT/'data/interim/stage1g_extraction/stkdistributions.parquet'}') s
        ON s.permno=l.permno AND s.disexdt>l.entry_date AND s.disexdt<=l.exit_date
        WHERE e.resolved AND (e.special_review OR l.label_status='measurable_cash_only_delisting')""")
    terminal=c.execute("""SELECT count(*),count(*) FILTER(WHERE NOT coalesce(pay_date<exit_date,false))
        FROM used_events WHERE terminal AND dispaymenttype='USD' AND distype='CP'""").fetchone()
    assert terminal[1]==0,'Terminal payment not established before exit'
    c.execute(f"""CREATE OR REPLACE TEMP TABLE daily_evidence AS SELECT permno,dlycaldt,
        dlyorddivamt,dlynonorddivamt,dlyretdurflg
        FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_parts/part_*.parquet'}') d
        SEMI JOIN (SELECT DISTINCT permno,event_date FROM used_events) u
        ON d.permno=u.permno AND d.dlycaldt=u.event_date WHERE dlycaldt>DATE '{lo}' AND dlycaldt<=DATE '{cut}'""")
    nonterminal=c.execute("""SELECT count(*),count(*) FILTER(WHERE d.dlycaldt IS NULL
        OR d.dlyretdurflg NOT IN ('D1','D2','D3','D4','DU') OR d.dlyorddivamt IS NULL
        OR d.dlynonorddivamt IS NULL OR abs(amount-d.dlyorddivamt-d.dlynonorddivamt)>0.00001)
        FROM (SELECT permno,signal_date,event_date,sum(disdivamt) amount FROM used_events
        WHERE dispaymenttype='USD' AND NOT terminal GROUP BY 1,2,3) u LEFT JOIN daily_evidence d
        ON u.permno=d.permno AND u.event_date=d.dlycaldt""").fetchone()
    assert nonterminal[1]==0,'Effective-date fixed cash lacks contemporaneous daily evidence'
    bundled=c.execute("""SELECT count(*),count(*) FILTER(WHERE d.dlycaldt IS NULL
        OR d.dlyorddivamt IS NULL OR d.dlynonorddivamt IS NULL
        OR abs(amount-d.dlyorddivamt-d.dlynonorddivamt)>0.00001)
        FROM (SELECT permno,signal_date,event_date,sum(disdivamt) amount,
        count(*) FILTER(WHERE distype IN ('CD','SD','ROC','CG')) fixed_claims
        FROM used_events WHERE terminal AND dispaymenttype='USD' GROUP BY 1,2,3) u
        LEFT JOIN daily_evidence d ON u.permno=d.permno AND u.event_date=d.dlycaldt WHERE fixed_claims>0""").fetchone()
    assert bundled[1]==0,'Bundled fixed claims lack through-exit amount evidence'
    direct=c.execute("""SELECT count(*),count(*) FILTER(WHERE NOT coalesce(entry_open>0 AND exit_open>0
        AND isfinite(entry_open) AND isfinite(exit_open),false)) FROM train_labels
        WHERE label_status='measurable_ordinary_event_adjusted'""").fetchone()
    assert direct[1]==0,'Frozen numeric ordinary label lacks verified endpoints'
    complete=' AND '.join(f'coalesce(isfinite(f.{f}_z),false)' for f in FEATURES)
    cols=['count(*) n','max(l.exit_date) exit_date','max(l.exit_date) maturity_date','avg(l.target_5d) my']
    for j,f in enumerate(FEATURES):
        cols += [f'avg(f.{f}_z) m{j}',f'avg(f.{f}_z*l.target_5d) xy{j}']
        for k in range(j,8):cols.append(f'avg(f.{f}_z*f.{FEATURES[k]}_z) xx{j}_{k}')
    moments=c.execute(f"SELECT l.signal_date,{','.join(cols)} FROM train_labels l JOIN {features_relation} f USING(permno,signal_date) WHERE {complete} GROUP BY l.signal_date ORDER BY l.signal_date").fetchdf()
    assert len(moments)>0 and moments.signal_date.is_unique
    qa=dict(cutoff=cut,new_training_rows=int(moments.n.sum()),new_training_dates=len(moments),
        cash_labels_verified=cash[0],terminal_cash_events_verified=terminal[0],
        contemporaneous_cash_groups_verified=nonterminal[0],bundled_cash_groups_verified=bundled[0],
        ordinary_endpoints_verified=direct[0],maturity_violation_count=0,
        economic_maturity_rule='exit_date under frozen through-exit ledger proof',static_publication_vintage_proven=False)
    return moments,qa
