"""Six cached cohorts: legal entitlement QA only; no prices, PnL or WRDS."""
import hashlib
import json
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.portfolio.successor import merger_entitlement

root=Path(__file__).resolve().parents[1]
protected=[p for folder in ('results/tables/stage4a','results/figures/stage4a',
    'results/tables/stage4b','results/figures/stage4b','data/interim/stage4b')
    for p in (root/folder).glob('*') if p.is_file()]
protected += [root/'docs/stage4a_continuation_feasibility.md',root/'docs/stage4b_execution_feasibility.md',
    root/'data/interim/stage4a_continuation/manifest.json']
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
out=root/'data/interim/stage4c';out.mkdir(exist_ok=True)
f=pd.read_parquet(root/'data/interim/stage4b/assumed_orders_and_execution_states.parquet',
    columns=['candidate','permno','received_permno','signal_date','side','state',
    'last_verified_parent_shares','scheduled_entry_date','scheduled_exit_date','five_day_deadline'])
f=f[f.state=='unresolved_execution'].copy()
assert len(f)==6 and set(f.permno)=={20124} and set(f.received_permno)=={87033}
assert not f.duplicated(['candidate','permno','signal_date']).any()
assert (pd.to_datetime(f.scheduled_entry_date)<pd.Timestamp('2003-03-31')).all()
assert set(pd.to_datetime(f.signal_date).dt.strftime('%Y-%m-%d'))=={
    '2003-03-21','2003-03-24','2003-03-27'}
assert (f.groupby(['candidate','side']).size().to_dict()=={
    ('ridge','long'):2,('ridge','short'):1,
    ('uni_reversal_5','long'):2,('uni_reversal_5','short'):1})
for col in ['ordinary_share_entitlement','ads_equivalent_entitlement','ads_ratio',
            'tradable_successor_quantity','inventory_verified','reason']:
    f[col]=[str(merger_entitlement(q,'2.675',5)[col]) for q in f.last_verified_parent_shares]
assert set(f.inventory_verified)=={'False'} and set(f.tradable_successor_quantity)=={'None'}
f.to_parquet(out/'cohort_entitlement_mapping.parquet',index=False)
summary=f.groupby(['candidate','side']).size().rename('observations').reset_index()
summary['legal_ads_ratio']='0.535';summary['ratio_verified']=True
summary['executable_inventory_verified']=False
summary['stage4b_inventory_gate']='unresolved_no_assumption_added'
summary.to_csv(root/'results/tables/stage4c/successor_recovery_gate.csv',index=False)
assert hashes=={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
(out/'manifest.json').write_text(json.dumps({'qa_passed':True,'cohorts':6,
    'entitlement_ratio_verified':True,'execution_inventory_gate_passed':False,
    'stage4b_full_rerun_deferred_for_material_election_fractional_settlement_gate':True,
    'wrds_queries':0,'performance_computed':False,'holdout_accessed':False,
    'construction_timestamp_utc':pd.Timestamp.now(tz='UTC').isoformat(),
    'ordinary_ratio':'2.675','ordinary_per_ads':5,'ads_ratio':'0.535',
    'legal_sources':[
        'https://www.sec.gov/Archives/edgar/data/48681/000004868102000447/mergerhihsbc8k.htm',
        'https://www1.hkexnews.hk/listedco/listconews/sehk/2003/0227/ltn20030227105.pdf'],
    'protected_artifact_hashes':hashes},indent=2)+'\n')
print(summary.to_string(index=False))
