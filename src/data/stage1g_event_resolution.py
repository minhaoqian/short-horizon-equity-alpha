"""Cache-only Stage 1G event sufficiency audit, not frozen target labels.

Resolved means complete wealth measurement under the existing proposed
zero-interest/no-reinvestment ledger. Availability and economic assumptions
remain separate; no missing price or unknown received quantity is manufactured.
"""
from pathlib import Path
import json
import hashlib
import duckdb

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/tables/stage1g'
EX=ROOT/'data/interim/stage1g_extraction'


def entitled(entry,exit_,ex):
    return entry < ex <= exit_


def main():
    manifest=json.loads((EX/'download_manifest.json').read_text())
    assert manifest['complete'] and manifest['extraction_qa']['passed']
    for name,info in manifest['outputs'].items():
        assert hashlib.sha256((EX/info['file']).read_bytes()).hexdigest()==info['sha256']
    c=duckdb.connect();c.execute('SET threads=2');c.execute("SET memory_limit='4GB'")
    c.execute(f"CREATE VIEW a AS SELECT *,coalesce(entry_open>0 AND isfinite(entry_open),false) ve,coalesce(exit_open>0 AND isfinite(exit_open),false) vx FROM read_parquet('{ROOT/'data/interim/target_boundary_audit_parts'}/*.parquet')")
    assert c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM a').fetchone()==(6699101,6699101)
    special='entry_nonordinary OR interior_nonordinary OR exit_nonordinary OR period_factor_event OR cumulative_factor_event'
    c.execute(f'''CREATE TABLE paths AS SELECT *,NOT ve missing_entry,ve AND NOT vx AND daily_delist_flag exit_flag,
      ve AND NOT vx AND NOT daily_delist_flag exit_no_flag,({special}) special_review
      FROM a WHERE NOT right_censored AND (NOT ve OR NOT vx OR {special} OR missing_event_fields OR entry_ordinary OR exit_ordinary)''')
    for name,view in [('stkdelists','l'),('stkdistributions','s'),('stkdlysecuritydata','x')]:
        c.execute(f"CREATE VIEW {view} AS SELECT * FROM read_parquet('{EX/(name+'.parquet')}')")
    # Extract is complete by parent PERMNO; retain matches outside storage windows
    # in the row-level table but do not pretend they occurred during ownership.
    c.execute('''CREATE TABLE base AS SELECT p.*,l.* EXCLUDE(permno),
      l.delistingdt BETWEEN p.entry_date AND p.exit_date actual_delist_in_window,
      l.delistingdt BETWEEN p.signal_date AND p.exit_date OR l.deldlydt BETWEEN p.signal_date AND p.exit_date
        OR l.delamtdt BETWEEN p.signal_date AND p.exit_date event_date_match,
      xe.dlyprevdt entry_prevdt,xe.dlyretmissflg entry_return_missing,
      xb.dlyprevdt exit_prevdt,xb.dlyretmissflg exit_return_missing
      FROM paths p LEFT JOIN l USING(permno)
      LEFT JOIN x xe ON xe.permno=p.permno AND xe.dlycaldt=p.entry_date
      LEFT JOIN x xb ON xb.permno=p.permno AND xb.dlycaldt=p.exit_date''')
    c.execute('''CREATE TABLE events AS SELECT b.permno,b.signal_date,b.entry_date,b.exit_date,b.delistingdt,b.deldlydt,
      b.delamtdt,b.delpaymenttype,b.delstatustype,b.deldivamt,b.deldistype,b.delretmisstype,
      s.* EXCLUDE(permno),s.disexdt>b.entry_date entitled,
      (s.dispaymenttype='SS' AND s.distype='FRS' AND s.disdetailtype IN ('STKSPL','STKDIV')
        AND s.disfacshr>-1 AND isfinite(s.disfacshr) AND coalesce(s.dispermno,0)=0) pure_split,
      (s.dispaymenttype='USD' AND s.distype IN ('CD','SD','ROC','CG')
        AND s.disdetailtype IN ('CDIV','SDIV','SDROC','ROC','CAPG','CDPSR')
        AND s.disdivamt>=0 AND isfinite(s.disdivamt) AND s.disfacpr=0 AND s.disfacshr=0
        AND coalesce(s.dispermno,0)=0) fixed_cash,
      (s.dispaymenttype='USD' AND s.distype='CP' AND s.disdetailtype IN ('CPM','CPRCSH')
        AND s.disexdt=b.deldlydt AND s.disexdt<=b.exit_date AND s.dispaydt<b.exit_date
        AND s.disdivamt>=0 AND isfinite(s.disdivamt)
        AND b.delpaymenttype='CASH' AND b.delstatustype='FPAY' AND b.deldistype IN ('D1','D2')
        AND b.delretmisstype='NA' AND b.delamtdt<=b.exit_date) terminal_cash
      FROM base b JOIN s ON b.permno=s.permno AND s.disexdt>b.signal_date AND s.disexdt<=b.exit_date''')
    c.execute('''CREATE TABLE event_stats AS SELECT permno,signal_date,count(*) matched_events,
      count(*) FILTER(WHERE disexdt=entry_date) entry_events,count(*) FILTER(WHERE disexdt=exit_date) exit_events,
      count(*) FILTER(WHERE entitled AND NOT coalesce(pure_split OR fixed_cash OR terminal_cash,false)) unsupported_entitled,
      count(*) FILTER(WHERE entitled AND coalesce(terminal_cash,false)) terminal_cash_count,
      sum(disdivamt) FILTER(WHERE entitled AND disexdt=deldlydt AND (fixed_cash OR terminal_cash)) terminal_cash_sum,
      count(*) FILTER(WHERE entitled AND disexdt=deldlydt AND (fixed_cash OR terminal_cash)) terminal_cash_terms,
      count(*) FILTER(WHERE entitled AND coalesce(pure_split,false)) splits,
      count(*) FILTER(WHERE entitled AND coalesce(fixed_cash,false)) cash_events,
      count(*) FILTER(WHERE entitled AND (dispaymenttype IN ('OS','OP','UNIT') OR coalesce(dispermno,0)<>0)) received_assets,
      product(1+disfacshr) FILTER(WHERE entitled AND pure_split) share_multiplier,
      product(1+disfacshr-0.0000005) FILTER(WHERE entitled AND pure_split) share_low,
      product(1+disfacshr+0.0000005) FILTER(WHERE entitled AND pure_split) share_high,
      count(*) FILTER(WHERE entitled AND (fixed_cash OR terminal_cash) AND dispaydt>exit_date) future_payment_cash,
      count(*) FILTER(WHERE entitled AND (fixed_cash OR terminal_cash) AND dispaydt IS NULL) missing_cash_pay_date
      FROM events GROUP BY permno,signal_date''')
    c.execute('''CREATE TABLE same_day AS SELECT permno,signal_date,count(*) conflicts FROM (
      SELECT permno,signal_date,disexdt FROM events WHERE entitled GROUP BY ALL
      HAVING count(*) FILTER(WHERE pure_split)>0 AND count(*) FILTER(WHERE fixed_cash OR terminal_cash)>0
    ) GROUP BY permno,signal_date''')
    # Same-date split/cash amounts can use CRSP's documented previous-share
    # cash basis, without guessing an intraday event sequence. Require a
    # verified single-trading-period source interval and complete amount fields.
    c.execute(f"CREATE VIEW daily AS SELECT * FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_daily.parquet'}')")
    c.execute('''CREATE TABLE cash_basis AS SELECT e.permno,e.signal_date,count(*) FILTER(WHERE
      d.dlyretdurflg IN ('D1','D2','D3','D4','DU') AND d.dlyprevprc>0
      AND d.dlyorddivamt IS NOT NULL AND d.dlynonorddivamt IS NOT NULL AND d.dlyfacprc>0) proven_conflicts
      FROM (SELECT permno,signal_date,disexdt FROM events WHERE entitled GROUP BY ALL
        HAVING count(*) FILTER(WHERE pure_split)>0 AND count(*) FILTER(WHERE fixed_cash OR terminal_cash)>0) e
      LEFT JOIN daily d ON d.permno=e.permno AND d.dlycaldt=e.disexdt GROUP BY e.permno,e.signal_date''')
    # Project only cumulative shares at exact endpoints; no raw daily-file read.
    c.execute(f"CREATE VIEW f AS SELECT permno,dlycaldt,dlycumfacshr FROM read_parquet('{ROOT/'data/interim/crsp_cumfac_1993_2025.parquet'}')")
    c.execute('''CREATE TABLE q AS SELECT b.*,e.* EXCLUDE(permno,signal_date),coalesce(sd.conflicts,0) conflicts,
      coalesce(cb.proven_conflicts,0) proven_conflicts,
      fa.dlycumfacshr entry_share_factor,fb.dlycumfacshr exit_share_factor,
      coalesce(e.share_multiplier,1) expected_quantity,
      fa.dlycumfacshr/fb.dlycumfacshr factor_quantity,
      (fa.dlycumfacshr-0.0000005)/(fb.dlycumfacshr+0.0000005) factor_low,
      (fa.dlycumfacshr+0.0000005)/(fb.dlycumfacshr-0.0000005) factor_high
      FROM base b LEFT JOIN event_stats e USING(permno,signal_date) LEFT JOIN same_day sd USING(permno,signal_date)
      LEFT JOIN cash_basis cb USING(permno,signal_date)
      LEFT JOIN f fa ON fa.permno=b.permno AND fa.dlycaldt=b.entry_date
      LEFT JOIN f fb ON fb.permno=b.permno AND fb.dlycaldt=CASE WHEN b.exit_flag THEN cast(b.delistingdt AS DATE) ELSE b.exit_date END''')
    # Conservative complete-label resolution. Cash dated on exit day is not
    # treated as known before the opening without an established event claim.
    c.execute('''CREATE TABLE classified AS SELECT *,
      CASE WHEN missing_entry THEN 'missing_entry_open_unrecoverable'
        WHEN exit_no_flag THEN 'missing_exit_open_no_flag'
        WHEN exit_flag AND delamtdt>=exit_date AND NOT coalesce(terminal_cash_count>=1 AND delamtdt<=exit_date
          AND abs(terminal_cash_sum-deldivamt)<=(terminal_cash_terms+1)*0.0000005,false) THEN 'delisting_value_on_or_after_exit'
        WHEN exit_flag AND NOT coalesce(event_date_match,false) THEN 'delisting_event_not_matched'
        WHEN exit_flag AND NOT coalesce(delpaymenttype='CASH' AND delstatustype='FPAY' AND deldistype IN ('D1','D2')
          AND delretmisstype='NA' AND delamtdt<=exit_date AND terminal_cash_count>=1
          AND abs(terminal_cash_sum-deldivamt)<=(terminal_cash_terms+1)*0.0000005,false)
          THEN 'delisting_non_cash_or_incomplete_terms'
        WHEN coalesce(unsupported_entitled,0)>0 THEN 'received_security_or_other_terms_unavailable'
        WHEN conflicts>proven_conflicts THEN 'same_exdate_cash_split_basis_ambiguous'
        WHEN coalesce(matched_events,0)=0 AND special_review THEN 'factor_event_no_matching_history'
        WHEN NOT ve OR (NOT vx AND NOT exit_flag) THEN 'endpoint_unavailable'
        WHEN NOT (entry_share_factor>0.0000005 AND exit_share_factor>0.0000005
          AND greatest(factor_low,coalesce(share_low,1))<=least(factor_high,coalesce(share_high,1))+1e-12)
          OR entry_share_factor IS NULL OR exit_share_factor IS NULL THEN 'share_factor_event_inconsistent'
        WHEN exit_flag THEN 'resolved_cash_claim_by_exit'
        WHEN aggregated_event_interval OR missing_event_fields THEN 'event_interval_or_field_gap'
        ELSE 'resolved_split_cash_or_entry_only' END resolution
      FROM q''')
    c.execute("ALTER TABLE classified ADD COLUMN resolved BOOLEAN")
    c.execute("UPDATE classified SET resolved=resolution LIKE 'resolved_%'")
    assert c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM classified').fetchone()[0]==c.execute('SELECT count(*) FROM paths').fetchone()[0]
    def export(name,sql):c.execute(f"COPY ({sql}) TO '{OUT/name}' (HEADER,FORMAT CSV)")
    groups={'missing_entry':'missing_entry','missing_exit_with_flag_valid_entry':'exit_flag',
      'missing_exit_without_flag_valid_entry':'exit_no_flag','factor_nonordinary_review':'special_review',
      'factor_nonordinary_valid_endpoints':'special_review AND ve AND vx',
      'nonordinary_entry_boundary':'entry_nonordinary','nonordinary_exit_boundary':'exit_nonordinary',
      'nonordinary_interior':'interior_nonordinary','ordinary_entry_boundary':'entry_ordinary','ordinary_exit_boundary':'exit_ordinary'}
    rules={
      'missing_entry':('No observed next-open fill; previous closing price/volume cannot recover opening execution','entry_open,entry_volume,entry_price_flag,entry_prevdt,entry_return_missing,delisting/distribution dates'),
      'missing_exit_with_flag_valid_entry':('Only complete matched cash-only event bundles with terminal payment dated before exit and ex-date at/before exit pass; same-exit-date amount records require independent fixed-claim evidence. Retain all other assets/claims unresolved','DelistingDt,DelDlyDt,DelAmtDt,DelPaymentType,DelStatusType,DelDisType,DelRetMissType,DelDivAmt,DisExDt,DisPayDt,DisDivAmt'),
      'missing_exit_without_flag_valid_entry':('No actual exit opening value; later prices/returns do not replace it','exit_open,exit_price_flag,exit_prevdt,exit_return_missing,actual delisting dates'),
    }
    rows=[]
    for name,predicate in groups.items():
        n,k,r,u=c.execute(f'SELECT count(*),count(DISTINCT permno),count(*) FILTER(WHERE resolved),count(*) FILTER(WHERE NOT resolved) FROM classified WHERE {predicate}').fetchone()
        rule,fields=rules.get(name,('Entry ex-date excluded; exit ex-date included. Pure splits use 1+DisFacShr, confirmed against cumulative share-factor endpoints; fixed USD cash claims tracked without reinvestment. Received quantity/valuation and conflicting bases remain unresolved.','DisExDt,DisSeqNbr,DisPaymentType,DisType,DisDetailType,DisDivAmt,DisFacShr,DisPayDt,DisPERMNO,DlyCumFacShr,entry/exit opens'))
        rows.append((name,n,k,r,u,rule,fields,'Resolved counts are complete-label accounting sufficiency under the existing proposed ledger, not frozen labels; categories overlap.'))
    import csv
    with (OUT/'event_resolution_paths.csv').open('w',newline='') as file:
        w=csv.writer(file);w.writerow(['path','observations','distinct_permnos','resolved','unresolved','resolution_rule','fields_used','ambiguity']);w.writerows(rows)
    export('event_resolution_reasons.csv','SELECT resolution,count(*) observations,count(DISTINCT permno) distinct_permnos FROM classified GROUP BY resolution ORDER BY observations DESC')
    export('missing_entry_event_attribution.csv',"SELECT entry_price_flag,entry_return_missing,count(*) observations,count(*) FILTER(WHERE entry_prevdt<entry_date) previous_price_before_entry,count(*) FILTER(WHERE event_date_match) matched_delist,count(*) FILTER(WHERE actual_delist_in_window) delist_during_window FROM classified WHERE missing_entry GROUP BY ALL ORDER BY observations DESC")
    export('missing_exit_event_attribution.csv',"SELECT CASE WHEN exit_flag THEN 'with_flag' ELSE 'without_flag' END path,delpaymenttype,delstatustype,delretmisstype,deldistype,delnextprcflg,resolution,count(*) observations,count(*) FILTER(WHERE event_date_match) matched_event,count(*) FILTER(WHERE delamtdt<exit_date) amount_before_exit,count(*) FILTER(WHERE delamtdt=exit_date) amount_on_exit,count(*) FILTER(WHERE delamtdt>exit_date) amount_after_exit,count(*) FILTER(WHERE coalesce(delpermno,0)<>0) successor_link FROM classified WHERE exit_flag OR exit_no_flag GROUP BY ALL ORDER BY path,observations DESC")
    export('event_boundary_matches.csv',"SELECT CASE WHEN disexdt<entry_date THEN 'pre_entry_gap' WHEN disexdt=entry_date THEN 'entry' WHEN disexdt=exit_date THEN 'exit' ELSE 'interior' END boundary,dispaymenttype,distype,disdetailtype,count(*) observation_event_pairs,count(DISTINCT(permno,signal_date)) observations,count(DISTINCT(permno,disexdt,disseqnbr)) distinct_events FROM events GROUP BY ALL ORDER BY boundary,observation_event_pairs DESC")
    export('event_unresolved_cases.csv','SELECT * FROM classified WHERE NOT resolved ORDER BY signal_date,permno')
    c.execute(f"COPY classified TO '{ROOT/'data/interim/stage1g_extraction/event_resolution_cases.parquet'}' (FORMAT PARQUET)")
    print('PATH SUMMARY',rows,flush=True)
    print('RESOLUTION REASONS',c.execute('SELECT resolution,count(*) FROM classified GROUP BY 1 ORDER BY 2 DESC').fetchall(),flush=True)
    print('CASH CLAIM COUNT',c.execute("SELECT count(*) FROM classified WHERE resolution='resolved_cash_claim_by_exit'").fetchone(),flush=True)


if __name__=='__main__':main()
