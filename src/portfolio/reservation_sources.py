"""Narrow cached development sources for the approved reservation audit."""
import hashlib
import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from .settlement_audit import digest, protected_hashes

ROOT=Path(__file__).resolve().parents[2]


def preserve_prior():
    result=protected_hashes()
    for folder in ('data/interim/stage4e_scenarios','results/tables/stage4e','results/figures/stage4e'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file():result[str(p.relative_to(ROOT))]=digest(p)
    for p in (ROOT/'docs').glob('stage4e*.md'):result[str(p.relative_to(ROOT))]=digest(p)
    return result


class DevelopmentSources:
    def __init__(self):
        self.root=ROOT/'data/interim/stage4f'
        self.root.mkdir(parents=True,exist_ok=True)
        self.c=duckdb.connect();self.c.execute('SET threads=2')
        self.price_pattern=str(ROOT/'data/interim/reconstruction_diagnostic_parts/part_*.parquet')
        self.feature_pattern=str(ROOT/'data/interim/stage2a_features/parts/part_*.parquet')
        self.forecast_pattern=str(ROOT/'data/interim/stage3a/predictions/fold_*.parquet')
        source_files=list((ROOT/'data/interim/reconstruction_diagnostic_parts').glob('*.parquet'))
        source_files+=list((ROOT/'data/interim/stage2a_features/parts').glob('*.parquet'))
        source_files += [ROOT/'data/interim/stage2a_events/stkdistributions.parquet',
            ROOT/'data/interim/stage2a_events/stkdelists.parquet',ROOT/'data/interim/stage3a/calendar.parquet']
        self.fingerprints={str(p.relative_to(ROOT)):[p.stat().st_size,p.stat().st_mtime_ns] for p in sorted(source_files)}
        self.token=hashlib.sha256(json.dumps(self.fingerprints,sort_keys=True).encode()).hexdigest()[:16]
        m=json.loads((ROOT/'data/interim/stage3a/manifest.json').read_text())
        for i in range(1,69):
            p=ROOT/f'data/interim/stage3a/predictions/fold_{i:02d}.parquet'
            assert digest(p)==m['folds'][str(i)]['hashes']['predictions']
        frozen=json.loads((ROOT/'data/interim/stage3a/source_manifest.json').read_text())
        for f in frozen['input_fingerprints']:
            p=ROOT/f['path'];assert [p.stat().st_size,p.stat().st_mtime_ns]==[f['size'],f['mtime_ns']]
        self.c.execute(f"CREATE VIEW development AS SELECT permno,signal_date::DATE signal_date,entry_date::DATE entry_date,exit_date::DATE exit_date,ridge,uni_reversal_5 FROM read_parquet('{self.forecast_pattern}') WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2019-12-31'")
        counts=self.c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)),count(DISTINCT signal_date) FROM development').fetchone()
        assert counts==(3829908,3829908,4279)
        self.counts=counts
        self.c.execute('CREATE TEMP TABLE required_permnos AS SELECT DISTINCT permno FROM development')
        self.calendar_frame=self.c.execute(f"SELECT signal_date::DATE d,td FROM read_parquet('{ROOT}/data/interim/stage3a/calendar.parquet') WHERE signal_date BETWEEN DATE '2002-12-31' AND DATE '2020-01-16' ORDER BY 1").fetchdf()
        # Date-only extension for pending development deadlines, not holdout outcomes.
        extension=self.c.execute(f"SELECT DISTINCT dlycaldt::DATE d FROM read_parquet('{self.price_pattern}') WHERE dlycaldt BETWEEN DATE '2020-01-01' AND DATE '2020-01-17' ORDER BY 1").fetchdf()
        last_td=int(self.calendar_frame.td.iloc[-1])
        extension['td']=np.arange(last_td+1,last_td+1+len(extension))
        self.calendar_frame=pd.concat([self.calendar_frame,extension],ignore_index=True)
        self.calendar_extension_dates=len(extension)
        self.calendar=self.calendar_frame.d.dt.date.tolist()
        self.index={d:i for i,d in enumerate(self.calendar)}
        self.phase={pd.Timestamp(r.d).date():int(r.td)%5 for r in self.calendar_frame.itertuples()}
        self.development=[d for d in self.calendar if 2003<=d.year<=2019]
        assert len(self.development)==4279
        self.year=None;self.records={};self.previous_tail={};self.signal_groups={}
        self.events={};self.delists={};self.cache_checksums={};self.runoff_rows=0;self.runoff_feature_rows=0

    def load(self,year,runoff_ids=None):
        if self.year==year:return
        last_date=max((d for _,d in self.records),default=None)
        self.previous_tail={key:r for key,r in self.records.items() if key[1]==last_date}
        print(f'Preparing cached {year} accounting inputs',flush=True)
        end=f'{year}-12-31';restrict=' AND d.permno IN (SELECT permno FROM required_permnos)'
        event_restrict=' AND permno IN (SELECT permno FROM required_permnos)'
        signature=self.token
        if year==2020:
            assert runoff_ids is not None and len(runoff_ids)>0
            ids=','.join(map(str,sorted(runoff_ids)))
            restrict=f' AND d.permno IN ({ids})';event_restrict=f' AND permno IN ({ids})'
            end='2020-01-16'
            signature+=hashlib.sha256(ids.encode()).hexdigest()[:8]
        else:assert 2003<=year<=2019
        cache=self.root/'source_cache';cache.mkdir(exist_ok=True)
        path=cache/f'daily_{year}_{signature}.parquet';meta=path.with_suffix('.json')
        if path.exists() and meta.exists():
            assert digest(path)==json.loads(meta.read_text())['sha256'],'Corrupt local cache'
        else:
            temp=path.with_suffix('.tmp.parquet')
            # Only raw sigma for an affected development holding's required runoff
            # dates is used after2019: no holdout forecast/target/eligibility field.
            self.c.execute(f"""COPY (SELECT d.permno,d.dlycaldt,d.dlyprc,d.dlyopen,d.adv20,
                d.dlyorddivamt,d.dlynonorddivamt,d.dlyfacprc,d.dlyprevprc,d.dlyret,
                d.dlydelflg,f.volatility_20_raw sigma20,f.max_input_date
                FROM read_parquet('{self.price_pattern}') d LEFT JOIN
                (SELECT permno,signal_date,volatility_20_raw,max_input_date FROM read_parquet('{self.feature_pattern}')
                 WHERE signal_date BETWEEN DATE '{year}-01-01' AND DATE '{end}') f
                ON d.permno=f.permno AND d.dlycaldt=f.signal_date
                WHERE d.dlycaldt BETWEEN DATE '{year}-01-01' AND DATE '{end}' {restrict})
                TO '{temp}' (FORMAT PARQUET)""")
            temp.replace(path)
            meta.write_text(json.dumps({'source_fingerprint':self.token,'sha256':digest(path),'year':year,
                'runoff_only':year==2020,'required_permno_scope':restrict})+'\n')
        self.cache_checksums[str(path.relative_to(ROOT))]=digest(path)
        f=pd.read_parquet(path)
        assert not f.duplicated(['permno','dlycaldt']).any(),'Daily/feature join duplicate keys'
        finite=np.isfinite(f.sigma20)
        assert (pd.to_datetime(f.loc[finite,'max_input_date'])<=pd.to_datetime(f.loc[finite,'dlycaldt'])).all(),'Future feature input'
        self.records={(int(r.permno),pd.Timestamp(r.dlycaldt).date()):r for r in f.itertuples()}
        if year==2020:
            self.runoff_rows+=len(f);self.runoff_feature_rows+=int(finite.sum())
        ev=self.c.execute(f"SELECT * FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdistributions.parquet') WHERE disexdt BETWEEN DATE '{year}-01-01' AND DATE '{end}' {event_restrict} ORDER BY disexdt,permno,disseqnbr").fetchdf()
        for col in ['disexdt','dispaydt','disdeclaredt']:
            ev[col]=ev[col].dt.date
        self.events={}
        for (d,p),g in ev.groupby(['disexdt','permno']):
            rows=g.to_dict('records')
            for r in rows:
                if pd.isna(r['dispermno']):r['dispermno']=None
                # Normalize missing declaration/payment metadata without filling.
                for key in ('disdeclaredt','dispaydt'):
                    if pd.isna(r[key]):r[key]=None
            self.events[(int(p),d)]=rows
        dl=self.c.execute(f"SELECT * FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdelists.parquet') WHERE (delistingdt BETWEEN DATE '{year}-01-01' AND DATE '{end}' OR deldlydt BETWEEN DATE '{year}-01-01' AND DATE '{end}' OR delamtdt BETWEEN DATE '{year}-01-01' AND DATE '{end}') {event_restrict}").fetchdf()
        self.delists={(int(p),pd.Timestamp(d).date()):g.to_dict('records') for (p,d),g in dl.groupby(['permno','deldlydt'])}
        self.signal_groups={}
        if year<=2019:
            sig=self.c.execute(f"SELECT * FROM development WHERE signal_date BETWEEN DATE '{year}-01-01' AND DATE '{year}-12-31' ORDER BY signal_date,permno").fetchdf()
            for col in ('signal_date','entry_date','exit_date'):sig[col]=sig[col].dt.date
            self.signal_groups={d:g.reset_index(drop=True) for d,g in sig.groupby('signal_date')}
        self.year=year
        print(f'{year}: {len(f):,} cached rows; {len(ev):,} effective events; {sum(map(len,self.signal_groups.values())):,} signal keys',flush=True)

    def row(self,p,d):return self.records.get((int(p),d),self.previous_tail.get((int(p),d)))
    def opening(self,p,d):
        r=self.row(p,d);return None if r is None else r.dlyopen

    def cost_inputs(self,p,decision_date):
        r=self.row(p,decision_date)
        return r is not None and all(np.isfinite(x) and x>=0 for x in (r.sigma20,r.adv20)) and r.adv20>0 and np.isfinite(r.dlyprc) and r.dlyprc>0
