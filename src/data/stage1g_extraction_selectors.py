"""Local-only Stage 1G selectors; no remote connection or target construction."""
from pathlib import Path
from datetime import datetime, timezone
import json
import duckdb
from src.data.target_exception_inventory import DELIST, DIST

ROOT = Path(__file__).resolve().parents[2]


def merge_windows(c, source, target):
    """Running maximum handles nested intervals; calendar adjacency is inclusive."""
    c.execute(f'''CREATE TABLE {target} AS WITH prior AS (
      SELECT *,max(hi) OVER (PARTITION BY permno ORDER BY lo,hi,signal_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) previous_hi FROM {source}
    ), marked AS (
      SELECT *,CASE WHEN previous_hi IS NULL OR lo>previous_hi+1 THEN 1 ELSE 0 END new_group FROM prior
    ), numbered AS (
      SELECT *,sum(new_group) OVER (PARTITION BY permno ORDER BY lo,hi,signal_date ROWS UNBOUNDED PRECEDING) window_id FROM marked
    ) SELECT permno,window_id,min(lo) lo,max(hi) hi,count(*) source_observations,
      list(struct_pack(signal_date:=signal_date,original_lo:=lo,original_hi:=hi,categories:=categories)
        ORDER BY signal_date) provenance
      FROM numbered GROUP BY permno,window_id''')
    assert c.execute(f'''SELECT count(*) FROM (
      SELECT lo,lag(hi) OVER(PARTITION BY permno ORDER BY lo) prev FROM {target}
    ) WHERE lo<=prev+1''').fetchone()[0] == 0
    assert c.execute(f'''SELECT count(*) FROM (
      SELECT p.permno,p.signal_date,count(m.window_id) matches FROM {source} p LEFT JOIN {target} m
        ON p.permno=m.permno AND p.lo>=m.lo AND p.hi<=m.hi
      GROUP BY p.permno,p.signal_date HAVING matches<>1)''').fetchone()[0] == 0


def main():
    out=ROOT/'data/interim/stage1g_extraction'
    out.mkdir(exist_ok=True)
    parts=sorted((ROOT/'data/interim/target_boundary_audit_parts').glob('*.parquet'))
    assert [p.name for p in parts]==[f'part_{i:02d}.parquet' for i in range(32)]
    daily=ROOT/'data/interim/reconstruction_diagnostic_daily.parquet'
    inputs=parts+[daily]
    fingerprints={str(p.relative_to(ROOT)):{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in inputs}
    c=duckdb.connect();c.execute("SET threads=2");c.execute("SET memory_limit='4GB'")
    c.execute(f"CREATE VIEW a AS SELECT *,coalesce(entry_open>0 AND isfinite(entry_open),false) ve,coalesce(exit_open>0 AND isfinite(exit_open),false) vx FROM read_parquet('{parts[0].parent}/*.parquet')")
    assert c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM a').fetchone()==(6699101,6699101)
    delcats={'missing_entry':'NOT ve','missing_exit_with_flag':'NOT vx AND daily_delist_flag',
      'missing_exit_without_flag':'NOT vx AND NOT daily_delist_flag','delisting_or_DA':'daily_delist_flag OR delist_price_flag',
      'interior_missing_price':'interior_missing_price','missing_event_fields':'missing_event_fields'}
    discats={'factor_nonordinary':'entry_nonordinary OR interior_nonordinary OR exit_nonordinary OR period_factor_event OR cumulative_factor_event',
      'missing_event_fields':'missing_event_fields','ordinary_entry':'entry_ordinary','ordinary_exit':'exit_ordinary'}
    manifest={'constructed_at_utc':datetime.now(timezone.utc).isoformat(),'sources':fingerprints,
      'wrds_query_executed':False,'stage':'Stage 1G OPEN','selectors':{},'qa':{}}
    for name,cats,lo,table,fields,batch in [
      ('delist',delcats,'signal_date','crsp.stkdelists',DELIST,200),
      ('distribution',discats,'entry_date','crsp.stkdistributions',DIST,100)]:
        pred=' OR '.join(f'({v})' for v in cats.values())
        categories='list_filter(['+','.join(f"CASE WHEN {v} THEN '{k}' END" for k,v in cats.items())+'],x -> x IS NOT NULL)'
        c.execute(f'''CREATE TABLE {name}_pre AS SELECT permno,signal_date,{lo} lo,exit_date hi,{categories} categories
          FROM a WHERE NOT right_censored AND ({pred})''')
        assert c.execute(f'SELECT count(*) FROM {name}_pre WHERE lo IS NULL OR hi IS NULL OR lo>hi').fetchone()[0]==0
        assert c.execute(f'''SELECT count(*) FROM {name}_pre p JOIN a USING(permno,signal_date) WHERE a.right_censored''').fetchone()[0]==0
        merge_windows(c,name+'_pre',name+'_merged')
        path=out/f'{name}_windows.parquet'
        c.execute(f"COPY (SELECT * FROM {name}_merged ORDER BY permno,lo) TO '{path}' (FORMAT PARQUET)")
        pre=c.execute(f'SELECT count(*) FROM {name}_pre').fetchone()[0]
        post,perms,mn,mx=c.execute(f'SELECT count(*),count(DISTINCT permno),min(lo),max(hi) FROM {name}_merged').fetchone()
        longest=c.execute(f'SELECT permno,lo,hi,hi-lo+1 AS calendar_days,source_observations FROM {name}_merged ORDER BY calendar_days DESC,permno LIMIT 5').fetchall()
        manifest['selectors'][name]={'file':path.name,'pre_merge':pre,'post_merge':post,'distinct_permnos':perms,'min_date':str(mn),'max_date':str(mx),
          'rules':{'exclude_right_censored':True,'interval':[lo,'exit_date'],'merge':'overlap or calendar-day adjacency, per PERMNO','categories':cats},
          'provenance':'Every source signal date, original interval and category list retained in each merged window.',
          'wrds_table':table,'columns':[x.strip().lower() for x in fields.split(';')],'batch_permnos':batch,
          'longest_windows':[{'permno':r[0],'lo':str(r[1]),'hi':str(r[2]),'calendar_days':r[3],'source_observations':r[4]} for r in longest]}
    c.execute(f"CREATE VIEW d AS SELECT * FROM read_parquet('{daily}')")
    # Existing rows only. No calendar grid, absent-row manufacture or price fill.
    c.execute('''CREATE TABLE daily_selected AS WITH candidates AS (
      SELECT d.* FROM d WHERE EXISTS (SELECT 1 FROM delist_merged w
        WHERE w.permno=d.permno AND d.dlycaldt BETWEEN w.lo AND w.hi)
    ) SELECT permno,dlycaldt,
      true need_dlyprevdt,true need_dlyretmissflg,
      list_filter([
        CASE WHEN dlyprc IS NULL THEN 'missing_price' END,
        CASE WHEN dlyret IS NULL OR dlyretx IS NULL THEN 'missing_return' END,
        CASE WHEN dlyretdurflg LIKE 'P%' THEN 'multi_period_return' END,
        CASE WHEN dlydelflg='Y' OR dlyprcflg='DA' THEN 'delisting_return_or_DA' END,
        CASE WHEN dlyorddivamt IS NULL OR dlynonorddivamt IS NULL OR dlyfacprc IS NULL THEN 'missing_event_fields' END,
        CASE WHEN (dlyopen IS NULL OR NOT isfinite(dlyopen) OR dlyopen<=0) AND EXISTS (
          SELECT 1 FROM delist_pre p JOIN a USING(permno,signal_date)
          WHERE p.permno=candidates.permno AND
            ((NOT a.ve AND candidates.dlycaldt=a.entry_date) OR (NOT a.vx AND candidates.dlycaldt=a.exit_date))
        ) THEN 'missing_endpoint_open' END
      ],x -> x IS NOT NULL) reasons
      FROM candidates''')
    candidate_rows=c.execute('SELECT count(*) FROM daily_selected').fetchone()[0]
    c.execute('DELETE FROM daily_selected WHERE len(reasons)=0')
    count,keys,perms,mn,mx=c.execute('SELECT count(*),count(DISTINCT(permno,dlycaldt)),count(DISTINCT permno),min(dlycaldt),max(dlycaldt) FROM daily_selected').fetchone()
    assert count==keys
    assert c.execute('SELECT count(*) FROM daily_selected s WHERE NOT EXISTS(SELECT 1 FROM d WHERE d.permno=s.permno AND d.dlycaldt=s.dlycaldt)').fetchone()[0]==0
    c.execute(f"COPY (SELECT * FROM daily_selected ORDER BY permno,dlycaldt) TO '{out/'daily_missing_field_dates.parquet'}' (FORMAT PARQUET)")
    manifest['selectors']['daily']={'file':'daily_missing_field_dates.parquet','candidate_windows':manifest['selectors']['delist']['pre_merge'],
      'candidate_existing_rows':candidate_rows,'rows':count,'unique_keys':keys,'distinct_permnos':perms,'min_date':str(mn),'max_date':str(mx),
      'rules':'Existing cached rows in non-censored delist-review windows; missing endpoint open, price, return, event fields, multi-period return or delisting/DA. Both missing metadata fields requested on these rows; no absent rows generated.',
      'wrds_table':'crsp.stkdlysecuritydata','columns':['permno','dlycaldt','dlyprevdt','dlyretmissflg'],'batch_keys':5000}
    assert all(v=={'size':(ROOT/k).stat().st_size,'mtime_ns':(ROOT/k).stat().st_mtime_ns} for k,v in fingerprints.items())
    manifest['qa']={'unique_input_keys':6699101,'no_censored_source_signals':True,'merged_nonoverlap_and_nonadjacency':True,
      'every_premerge_window_maps_once':True,'daily_keys_unique_and_existing':True,'source_fingerprints_unchanged':True}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest['selectors'],indent=2))


if __name__=='__main__':
    main()
