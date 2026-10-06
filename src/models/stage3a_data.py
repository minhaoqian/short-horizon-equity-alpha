"""Development-only sources and economic ledger-maturity proof for Stage 3A."""
import json
import duckdb
import pandas as pd
from src.features.panel import ROOT,FEATURES
from src.evaluation.baseline import sha
from src.evaluation.source_qa import validate_relations

CACHE=ROOT/'data/interim/stage3a'
OUT=ROOT/'results/tables/stage3a'


def prepare():
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    c=duckdb.connect();c.execute("SET threads=2; SET memory_limit='2GB'")
    c.execute(f"SET temp_directory='{CACHE/'temp'}'")
    sm=json.loads((ROOT/'data/interim/stage2a_features/manifest.json').read_text())
    assert sm['complete'] and sm['qa_passed']
    for r in sm['final_files']:assert sha(ROOT/r['file'])==r['sha256']
    c.execute(f"""CREATE TABLE f AS SELECT permno,signal_date,max_input_date,
        {','.join(f+'_z,'+f+'_processed_reason' for f in FEATURES)}
        FROM read_parquet('{ROOT/'data/interim/stage2a_features/parts/part_*.parquet'}')
        WHERE signal_date BETWEEN DATE '1993-01-04' AND DATE '2019-12-31'""")
    c.execute(f"""CREATE TABLE labels AS SELECT *,target_5d IS NOT NULL numeric_label,isfinite(target_5d) finite_label
        FROM read_parquet('{ROOT/'data/interim/stage1g_targets/targets_5d.parquet'}')
        WHERE signal_date BETWEEN DATE '1993-01-04' AND DATE '2019-12-31'""")
    validate_relations(c,4816452,4804070)
    assert c.execute('SELECT count(*) FROM f WHERE max_input_date>signal_date').fetchone()[0]==0
    # Maturity proof covers every candidate label potentially used by any fit.
    c.execute("CREATE TABLE train_labels AS SELECT * FROM labels WHERE numeric_label AND exit_date<=DATE '2019-09-30'")
    c.execute(f"""CREATE TABLE e AS SELECT * FROM read_parquet('{ROOT/'data/interim/stage1g_extraction/event_resolution_cases.parquet'}')
        WHERE signal_date<=DATE '2019-12-31'""")
    cash=c.execute("""SELECT count(*),count(*) FILTER(WHERE NOT coalesce(e.resolved AND e.resolution='resolved_cash_claim_by_exit'
        AND e.actual_delist_in_window AND e.delamtdt<=l.exit_date AND e.terminal_cash_count>=1
        AND e.delpaymenttype='CASH' AND e.delstatustype='FPAY' AND e.delretmisstype='NA',false))
        FROM train_labels l LEFT JOIN e USING(permno,signal_date) WHERE l.label_status='measurable_cash_only_delisting'""").fetchone()
    assert cash[1]==0,'Cash-ledger maturity contradicts frozen proof'
    # Exactly the event records used by the frozen target, not a new target ledger.
    c.execute(f"""CREATE TABLE used_events AS SELECT l.permno,l.signal_date,l.entry_date,l.exit_date,l.label_status,
        s.disexdt::DATE event_date,s.disseqnbr,s.dispaymenttype,s.disdivamt,s.disfacshr,s.disdetailtype,s.distype,s.disordinaryflg,
        s.dispaydt::DATE pay_date,(s.disexdt=e.deldlydt AND e.resolution='resolved_cash_claim_by_exit') terminal,
        s.dispaymenttype='SS' AND s.distype='FRS' AND s.disdetailtype IN ('STKSPL','STKDIV') split
        FROM train_labels l JOIN e USING(permno,signal_date)
        JOIN read_parquet('{ROOT/'data/interim/stage1g_extraction/stkdistributions.parquet'}') s
        ON s.permno=l.permno AND s.disexdt>l.entry_date AND s.disexdt<=l.exit_date
        WHERE e.resolved AND (e.special_review OR l.label_status='measurable_cash_only_delisting')""")
    terminal=c.execute("SELECT count(*),count(*) FILTER(WHERE NOT coalesce(pay_date<exit_date,false)) FROM used_events WHERE terminal AND dispaymenttype='USD' AND distype='CP'").fetchone()
    assert terminal[1]==0,'Terminal cash payment not matured by exit'
    c.execute(f"""CREATE TABLE daily_evidence AS SELECT permno,dlycaldt,dlyorddivamt,dlynonorddivamt,dlyretdurflg
        FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_daily.parquet'}') d
        SEMI JOIN (SELECT DISTINCT permno,event_date FROM used_events) u
        ON d.permno=u.permno AND d.dlycaldt=u.event_date
        WHERE dlycaldt<=DATE '2019-09-30'""")
    nonterminal=c.execute("""SELECT count(*),count(*) FILTER(WHERE d.dlycaldt IS NULL
        OR d.dlyretdurflg NOT IN ('D1','D2','D3','D4','DU') OR d.dlyorddivamt IS NULL
        OR d.dlynonorddivamt IS NULL OR abs(amount-d.dlyorddivamt-d.dlynonorddivamt)>0.00001)
        FROM (SELECT permno,signal_date,event_date,sum(disdivamt) amount FROM used_events
        WHERE dispaymenttype='USD' AND NOT terminal GROUP BY 1,2,3) u LEFT JOIN daily_evidence d
        ON u.permno=d.permno AND u.event_date=d.dlycaldt""").fetchone()
    assert nonterminal[1]==0,'Established cash not reconciled to effective-date daily evidence'
    bundled=c.execute("""SELECT count(*),count(*) FILTER(WHERE d.dlycaldt IS NULL OR d.dlyorddivamt IS NULL
        OR d.dlynonorddivamt IS NULL OR abs(amount-d.dlyorddivamt-d.dlynonorddivamt)>0.00001)
        FROM (SELECT permno,signal_date,event_date,sum(disdivamt) amount,
        count(*) FILTER(WHERE distype IN ('CD','SD','ROC','CG')) fixed_claims
        FROM used_events WHERE terminal AND dispaymenttype='USD' GROUP BY 1,2,3) u
        LEFT JOIN daily_evidence d ON u.permno=d.permno AND u.event_date=d.dlycaldt
        WHERE fixed_claims>0""").fetchone()
    assert bundled[1]==0,'Mixed terminal cash/established receivables lack through-exit amount evidence'

    # Annotation only: declaration chronology never delays an already measurable
    # daily claim or a terminal cash payment verified before the exit boundary.
    conflicts=c.execute(f"""SELECT count(*) FROM used_events u JOIN
        read_parquet('{ROOT/'data/interim/stage2a_events/stkdistributions.parquet'}') g
        ON g.permno=u.permno AND g.disexdt=u.event_date AND g.disseqnbr=u.disseqnbr
        WHERE g.disdeclaredt>u.exit_date""").fetchone()[0]
    direct=c.execute("""SELECT count(*) FILTER(WHERE label_status='measurable_ordinary_event_adjusted'),
        count(*) FILTER(WHERE label_status='measurable_ordinary_event_adjusted' AND
        NOT coalesce(entry_open>0 AND exit_open>0 AND isfinite(entry_open) AND isfinite(exit_open),false)) FROM train_labels""").fetchone()
    assert direct[1]==0,'Observed boundary values absent'
    # Frozen source construction uses through-exit daily fields/split endpoint
    # checks, established event-date cash, and pre-exit terminal payments; hence
    # economic maturity is exit_date, not later settlement/metadata dates.
    complete=' AND '.join(f'coalesce(isfinite({f}_z),false)' for f in FEATURES)
    c.execute(f"""CREATE TABLE joined AS SELECT f.*,l.* EXCLUDE(permno,signal_date),
        {complete} complete_features,CASE WHEN numeric_label THEN exit_date END maturity_date
        FROM f JOIN labels l USING(permno,signal_date)""")
    cols=['count(*) n','max(exit_date) exit_date','max(maturity_date) maturity_date','avg(target_5d) my']
    for j,f in enumerate(FEATURES):
        cols.extend([f'avg({f}_z) m{j}',f'avg({f}_z*target_5d) xy{j}'])
        for k in range(j,8):cols.append(f'avg({f}_z*{FEATURES[k]}_z) xx{j}_{k}')
    # Only last-fit-mature labels needed for training moments; evaluation labels
    # whose exits cross into 2020 stay in joined, never in training moments.
    moments=c.execute(f"""SELECT signal_date,{','.join(cols)} FROM joined
        WHERE complete_features AND numeric_label AND exit_date<=DATE '2019-09-30'
        GROUP BY signal_date ORDER BY signal_date""").fetchdf()
    moments.to_parquet(CACHE/'training_moments.parquet',index=False)
    c.execute(f"COPY joined TO '{CACHE/'development.parquet'}' (FORMAT PARQUET)")
    c.execute(f"""COPY (SELECT dlycaldt signal_date,row_number() OVER(ORDER BY dlycaldt)-1 td
        FROM (SELECT DISTINCT dlycaldt FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_parts/part_00.parquet'}')
        WHERE dlycaldt BETWEEN DATE '1993-01-04' AND DATE '2019-12-31')) TO '{CACHE/'calendar.parquet'}' (FORMAT PARQUET)""")
    report={'development_keys':4816452,'numeric_labels':4804070,'feature_hashes_verified':32,
        'cash_training_labels_verified':cash[0],'terminal_event_rows_verified':terminal[0],
        'established_cash_date_groups_verified':nonterminal[0],'direct_endpoint_labels_verified':direct[0],
        'bundled_fixed_claim_groups_verified':bundled[0],
        'declared_after_exit_used_events':conflicts,'economic_maturity_rule':'exit_date; frozen through-exit ledger proof',
        'static_publication_vintage_proven':False,'future_payment_used_as_unestablished_value':False,
        'maturity_violation_count':0,'holdout_signal_values_materialized':False,'qa_passed':True}
    pd.DataFrame([{'check':k,'value':json.dumps(v)} for k,v in report.items()]).to_csv(OUT/'source_maturity_qa.csv',index=False)
    inputs=[ROOT/'data/interim/stage1g_targets/targets_5d.parquet',ROOT/'data/interim/stage2a_features/manifest.json',
        ROOT/'data/interim/stage1g_extraction/event_resolution_cases.parquet',ROOT/'data/interim/stage1g_extraction/stkdistributions.parquet',
        ROOT/'data/interim/reconstruction_diagnostic_daily.parquet',ROOT/'data/interim/stage2a_events/stkdistributions.parquet',
        ROOT/'data/interim/reconstruction_diagnostic_parts/part_00.parquet']+[ROOT/r['file'] for r in sm['final_files']]
    report['input_fingerprints']=[{'path':str(p.relative_to(ROOT)),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in inputs]
    report['outputs']=[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in [CACHE/'training_moments.parquet',CACHE/'development.parquet',CACHE/'calendar.parquet']]
    (CACHE/'source_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    c.close();return report
