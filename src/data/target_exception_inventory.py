"""Stage 1G extraction inventory from existing boundary audit only.

Categories overlap; dates are observation windows, not verified event dates.
No target construction or input mutation is performed.
"""
from pathlib import Path
import csv
import duckdb

ROOT = Path(__file__).resolve().parents[2]
DAILY = 'PERMNO; DlyCalDt; DlyOpen; DlyPrc; DlyPrcFlg; DlyVol; DlyDelFlg; DlyPrevDt; DlyPrevPrc; DlyPrevPrcFlg; DlyRetDurFlg; DlyRetMissFlg'
DELIST = 'PERMNO; DelistingDt; DelDlyDt; DelDtPrc; DelDtPrcFlg; DelAmtDt; DelNextDt; DelNextPrc; DelNextPrcFlg; DelRet; DelRetMissType; DelActionType; DelStatusType; DelReasonType; DelPaymentType; DelDivAmt; DelDisType; DelPERMNO; DelPERMCO'
DIST = 'PERMNO; DisExDt; DisSeqNbr; DisOrdinaryFlg; DisPaymentType; DisType; DisDetailType; DisDivAmt; DisFacPr; DisFacShr; DisPayDt; DisPERMNO; DisPERMCO'
EVENT = '(entry_nonordinary OR interior_nonordinary OR exit_nonordinary OR period_factor_event OR cumulative_factor_event)'


def main():
    folder = ROOT / 'data/interim/target_boundary_audit_parts'
    assert sorted(p.name for p in folder.glob('*.parquet')) == [f'part_{i:02d}.parquet' for i in range(32)]
    out = ROOT / 'results/tables/stage1g'
    c = duckdb.connect()
    c.execute("SET threads=2")
    c.execute(f"CREATE VIEW a AS SELECT *, COALESCE(entry_open>0 AND isfinite(entry_open),false) valid_entry, COALESCE(exit_open>0 AND isfinite(exit_open),false) valid_exit FROM read_parquet('{folder}/*.parquet')")
    n, keys = c.execute('SELECT count(*),count(DISTINCT (permno,signal_date)) FROM a').fetchone()
    assert n == keys == 6699101
    # Missing-exit categories include missing-entry cases: completeness before
    # entry-valid subsets, rather than silently omitting failed entry paths.
    specs = [
        ('missing_entry', 'NOT valid_entry', 'entry_date', DAILY, 'StkDly', 'Actual opening quote required; re-extraction may reproduce null. Status/volume cannot prove no-fill.'),
        ('missing_exit_with_return_flag', 'NOT valid_exit AND daily_delist_flag', 'exit_date', DAILY+'; '+DELIST, 'StkDly; StkDelists', 'Flag is storage-date proxy. Need actual event and amount dates; successor opening value at planned exit if stock payment.'),
        ('missing_exit_without_return_flag', 'NOT valid_exit AND NOT daily_delist_flag', 'exit_date', DAILY+'; '+DELIST, 'StkDly; StkDelists', 'Absence of flag does not rule out event. Verify opening quote and event coverage; no horizon shift.'),
        ('missing_exit_with_flag_valid_entry', 'valid_entry AND NOT valid_exit AND daily_delist_flag', 'exit_date', DAILY+'; '+DELIST, 'StkDly; StkDelists', 'Subset of missing_exit_with_return_flag; matches prior holding audit.'),
        ('missing_exit_without_flag_valid_entry', 'valid_entry AND NOT valid_exit AND NOT daily_delist_flag', 'exit_date', DAILY+'; '+DELIST, 'StkDly; StkDelists', 'Subset of missing_exit_without_return_flag; matches prior holding audit.'),
        ('both_endpoints_missing', 'NOT valid_entry AND NOT valid_exit', 'entry_date', DAILY+'; '+DELIST, 'StkDly; StkDelists', 'Overlaps both endpoint categories; preserve signal key.'),
        ('nonordinary_entry_boundary', 'entry_nonordinary', 'entry_date', DIST, 'StkDistributions', 'Daily amount-date proxy, not verified DisExDt. Entry-day rights excluded only after actual ex-date confirmation.'),
        ('nonordinary_exit_boundary', 'exit_nonordinary', 'exit_date', DIST, 'StkDistributions', 'Confirm actual ex-date and retained claims at exit; linked securities require StkDly opening quotes.'),
        ('nonordinary_interior', 'interior_nonordinary', 'NULL::DATE', DIST, 'StkDistributions', 'Exact event day unavailable in aggregated audit; extract event history over full entry/exit window.'),
        ('factor_or_nonordinary_review', EVENT, 'NULL::DATE', DIST+'; DlyCumFacShr; DlyCumFacPr; DlyFacPrc', 'StkDistributions; StkDly (cumulative-factor extract)', 'Conservative union including entry events; price factor is not share quantity. Existing cumulative factors may substitute for re-extraction.'),
        ('delisting_return_flag_review', 'daily_delist_flag OR delist_price_flag', 'NULL::DATE', DELIST, 'StkDelists', 'Includes cases with available endpoints. Query actual DelistingDt OR DelDlyDt windows; retain later amount/payment records.'),
        ('interior_missing_price', 'interior_missing_price', 'NULL::DATE', DAILY+'; '+DELIST, 'StkDly; StkDelists', 'Not automatically an endpoint failure; reconcile event interval and claims without filling prices.'),
        ('missing_event_fields', 'missing_event_fields', 'NULL::DATE', DAILY+'; '+DIST+'; '+DELIST, 'StkDly; StkDistributions; StkDelists', 'May overlap absent rows and delistings; audit does not identify exact missing-field day.'),
        ('invalid_factor', 'invalid_factor', 'NULL::DATE', 'PERMNO; DlyCalDt; DlyCumFacPr; DlyCumFacShr; DlyFacPrc; '+DIST, 'StkDly (cumulative-factor extract); StkDistributions', 'Includes absent-row effects; verify against existing factor cache before any re-extraction.'),
        ('aggregated_event_interval', 'aggregated_event_interval', 'NULL::DATE', DAILY+'; '+DIST, 'StkDly; StkDistributions', 'Source interval may cross ownership boundary; never assign aggregated amount to storage date.'),
        ('ordinary_entry_boundary', 'entry_ordinary', 'entry_date', DIST, 'StkDistributions', 'Boundary validation control; ordinary amount-date proxy requires actual ex-date/payment type.'),
        ('ordinary_exit_boundary', 'exit_ordinary', 'exit_date', DIST, 'StkDistributions', 'Boundary validation control; retain earned exit-date rights without exit-day intraday return.'),
    ]
    rows = []
    selectors = []
    for category, predicate, date, fields, source, note in specs:
        where = f'NOT right_censored AND ({predicate})'
        values = c.execute(f'''SELECT count(*),count(DISTINCT permno),min(signal_date),max(signal_date),min(entry_date),max(entry_date),min(exit_date),max(exit_date),min({date}),max({date}) FROM a WHERE {where}''').fetchone()
        rows.append([category,*values,100*values[0]/n,source,fields,note])
        selectors.extend([category,*r] for r in c.execute(f'''SELECT permno,count(*),min(signal_date),max(signal_date),min(entry_date),max(exit_date),min({date}),max({date}) FROM a WHERE {where} GROUP BY permno ORDER BY permno''').fetchall())
    values = c.execute('SELECT count(*),count(DISTINCT permno),min(signal_date),max(signal_date),min(entry_date),max(entry_date),min(exit_date),max(exit_date) FROM a WHERE right_censored').fetchone()
    rows.append(['right_censored',*values,None,None,100*values[0]/n,'none','none','Administrative extraction-end censoring; null planned dates must not be replaced by last observed security date.'])
    with (out/'target_exception_inventory.csv').open('w', newline='') as f:
        w=csv.writer(f); w.writerow(['category','observations','distinct_permnos','signal_min','signal_max','entry_min','entry_max','exit_min','exit_max','relevant_date_min','relevant_date_max','percentage_full_universe','source_tables','required_fields','interpretation']); w.writerows(rows)
    # Per-security min/max ranges are conservative envelopes, not exact event
    # dates or a promise that every intervening date requires extraction.
    with (out/'target_exception_extraction_selectors.csv').open('w', newline='') as f:
        w=csv.writer(f); w.writerow(['category','permno','observations','signal_min','signal_max','window_min','window_max','endpoint_min','endpoint_max']); w.writerows(selectors)
    by_name={r[0]:r[1] for r in rows}
    assert by_name['missing_entry']==7596 and by_name['right_censored']==8686
    assert by_name['missing_exit_with_flag_valid_entry']==6916
    assert by_name['missing_exit_without_flag_valid_entry']==787
    assert by_name['both_endpoints_missing']==6863
    assert by_name['missing_exit_with_return_flag']+by_name['missing_exit_without_return_flag']==14566
    assert by_name['aggregated_event_interval']==0
    print('Unique input keys:',n,'; selector rows:',len(selectors))
    for r in rows: print(r[:11])


if __name__ == '__main__':
    main()
