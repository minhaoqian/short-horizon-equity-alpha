"""Stage 2B key/coverage preflight. No target values, ICs or performance statistics."""
from pathlib import Path
import hashlib
import json
import duckdb
from src.features.panel import FEATURES,ROOT


def validate_relations(c,expected_keys,expected_numeric):
    """Key/status gate before one-to-one evaluation joins; no outcome filtering."""
    for relation in ('f','labels'):
        assert c.execute(f'SELECT count(*),count(DISTINCT(permno,signal_date)) FROM {relation}').fetchone()==(expected_keys,expected_keys)
    for left,right in [('f','labels'),('labels','f')]:
        assert c.execute(f'SELECT count(*) FROM (SELECT permno,signal_date FROM {left} EXCEPT SELECT permno,signal_date FROM {right})').fetchone()[0]==0
    assert c.execute('''SELECT count(*) FROM labels WHERE numeric_label IS DISTINCT FROM
        (label_status IN ('measurable_ordinary_event_adjusted','measurable_cash_only_delisting'))
        OR (numeric_label AND NOT finite_label)''').fetchone()[0]==0
    numeric=c.execute('SELECT count(*) FROM labels WHERE numeric_label').fetchone()[0]
    assert numeric==expected_numeric
    return {'keys':expected_keys,'numeric_labels':numeric}


def main():
    source=ROOT/'data/interim/stage2a_features'
    m=json.loads((source/'manifest.json').read_text())
    assert m['complete'] and m['qa_passed'] and m['rows']==m['unique_keys']==6699101
    for batch in m['final_files']:
        path=ROOT/batch['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==batch['sha256']
    c=duckdb.connect();c.execute("SET threads=2; SET memory_limit='2GB'")
    output=ROOT/'data/interim/stage2b_preflight';output.mkdir(parents=True,exist_ok=True)
    c.execute(f"SET temp_directory='{output/'temp'}'")
    c.execute(f"CREATE VIEW f AS SELECT * FROM read_parquet('{source/'parts/part_*.parquet'}')")
    # Only availability booleans and statuses are projected. No numeric target
    # value is materialized in the joined relation or used for feature changes.
    c.execute(f'''CREATE VIEW labels AS SELECT permno,signal_date,label_status,
        target_5d IS NOT NULL numeric_label,isfinite(target_5d) finite_label
        FROM read_parquet('{ROOT/'data/interim/stage1g_targets/targets_5d.parquet'}')''')
    validate_relations(c,6699101,6676750)
    c.execute('CREATE VIEW joined AS SELECT f.*,l.numeric_label,l.label_status FROM f JOIN labels l USING(permno,signal_date)')
    n,labeled=c.execute('SELECT count(*),count(*) FILTER(WHERE numeric_label) FROM joined').fetchone()
    assert (n,labeled)==(6699101,6676750)
    out=ROOT/'results/tables/stage2b';out.mkdir(parents=True,exist_ok=True)
    coverage=[];byyear=[];bystatus=[]
    for feature in FEATURES:
        z=feature+'_z'
        finite=f'coalesce(isfinite({z}),false)'
        coverage.append(f'''SELECT '{feature}' feature,count(*) original_eligible,count(*) FILTER(WHERE numeric_label) numeric_labels,
            count(*) FILTER(WHERE numeric_label AND {finite}) evaluable_pairs,
            count(*) FILTER(WHERE numeric_label AND NOT {finite}) labeled_feature_missing,
            100.0*count(*) FILTER(WHERE numeric_label AND {finite})/count(*) eligible_coverage_pct,
            100.0*count(*) FILTER(WHERE numeric_label AND {finite})/count(*) FILTER(WHERE numeric_label) labeled_coverage_pct FROM joined''')
        byyear.append(f'''SELECT '{feature}' feature,year(signal_date) AS year,count(*) original_eligible,
            count(*) FILTER(WHERE numeric_label) numeric_labels,count(*) FILTER(WHERE numeric_label AND {finite}) evaluable_pairs
            FROM joined GROUP BY 2''')
        bystatus.append(f'''SELECT '{feature}' feature,label_status,count(*) status_rows,
            count(*) FILTER(WHERE {finite}) feature_observed,100.0*count(*) FILTER(WHERE {finite})/count(*) feature_coverage_pct FROM joined GROUP BY 2''')
    for name,queries in [('evaluation_coverage_preflight.csv',coverage),('evaluation_coverage_by_year_preflight.csv',byyear),
        ('feature_coverage_by_label_status_preflight.csv',bystatus)]:
        c.execute(f"COPY ({' UNION ALL '.join(queries)}) TO '{out/name}' (HEADER,DELIMITER ',')")
    report={'original_eligible_keys':n,'numeric_labels':labeled,'missing_labels':n-labeled,
        'source_checksums_verified':len(m['final_files']),'duplicate_or_key_difference_count':0,
        'target_values_materialized':False,'predictive_statistics_computed':False,
        'feature_or_target_methodology_changed':False,'full_period_counts_are_preflight_only':True,
        'evaluation_period_and_holdout_undefined':True,'certified_target_horizons':[5],
        'status':'Await temporal-scope review; no IC execution.'}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
