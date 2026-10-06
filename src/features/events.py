"""Outcome-independent effective-date event evidence with explicit REVIEW state.

Complete dated histories establish scope, not historical revision-free vintages.
A timing conflict never silently becomes a missing-feature policy. No payment,
settlement, target or exception-membership field is used for admissibility.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from bisect import bisect_right
from math import isfinite


@dataclass(frozen=True)
class EventDecision:
    gap_admissible: object
    return_admissible: object
    event_type: str
    reason: str
    distribution_count: int
    delisting_return_count: int


def day(value):
    if value is None:
        return None
    if isinstance(value,date):
        return value.date() if hasattr(value,'date') else value
    raise ValueError('Expected parsed date')


class EventLayer:
    def __init__(self,distributions,delists,coverage=(date(1993,1,1),date(2025,12,31))):
        self.coverage=coverage
        self.distributions={}
        self.delists={}
        for row in distributions:
            # Allowlist: omit later payment/settlement fields and all outcome data.
            fields={k:row.get(k) for k in ('disexdt','disdeclaredt','dispaymenttype','distype',
                'disdetailtype','disordinaryflg','disdivamt','disfacpr','disfacshr','dispermno')}
            fields['disexdt']=day(fields['disexdt']);fields['disdeclaredt']=day(fields['disdeclaredt'])
            if fields['disexdt'] is None:
                raise ValueError('Undated distribution cannot certify dated coverage')
            self.distributions.setdefault(int(row['permno']),[]).append(fields)
        for row in delists:
            # DelistingDt is the last followed-exchange price, not a public
            # notice timestamp. Do not retrospectively mask that earlier day.
            stored=day(row.get('deldlydt'))
            if stored is not None:
                self.delists.setdefault(int(row['permno']),[]).append(stored)
        for permno,rows in self.distributions.items():
            rows.sort(key=lambda r:r['disexdt'])
        self.date_index={p:[r['disexdt'] for r in rows] for p,rows in self.distributions.items()}
        for dates in self.delists.values():
            dates.sort()

    def interval(self,permno,start,end,as_of,daily_evidence=None):
        if end>as_of or start>end:
            raise ValueError('Interval cannot extend beyond as-of date')
        lo,hi=self.coverage
        if start<lo-timedelta(days=1) or end>hi:
            return EventDecision(None,None,'unknown','outside_global_event_coverage',0,0)
        dates=self.date_index.get(permno,[])
        records=self.distributions.get(permno,[])[bisect_right(dates,start):bisect_right(dates,end)]
        stored=self.delists.get(permno,[])
        n_del=bisect_right(stored,end)-bisect_right(stored,start)
        # Declaration chronology is QA only. Conflicts require effective-date
        # daily-term reconciliation, never a declaration-date availability gate.
        conflicting=any(r['disdeclaredt'] is not None and r['disdeclaredt']>r['disexdt'] for r in records)
        if conflicting:
            from .timing_qa import reconcile
            for d in {r['disexdt'] for r in records}:
                group=[r for r in records if r['disexdt']==d]
                daily=(daily_evidence or {}).get(d)
                if not reconcile(group,daily)[0]:
                    return EventDecision(False,False,'timing_ambiguous','timing_ambiguous',len(records),n_del)
        if n_del:
            return EventDecision(False,False,'delisting_return','stored_delisting_return_interval',len(records),n_del)
        if not records:
            return EventDecision(True,True,'none','globally_verified_event_absence',0,0)
        kinds=[]
        for r in records:
            def finite(v):
                return isinstance(v,(int,float)) and isfinite(v)
            if (r['dispaymenttype']=='SS' and r['distype']=='FRS'
                and r['disdetailtype'] in ('STKSPL','STKDIV') and finite(r['disfacshr'])
                and r['disfacshr']>-1 and (r['dispermno'] is None or r['dispermno']==0)):
                if not finite(r['disfacpr']) or abs(r['disfacpr']-r['disfacshr'])>1e-6:
                    return EventDecision(False,None,'review','same_security_split_factor_conflict',len(records),n_del)
                kinds.append('pure_split')
            elif (r['dispaymenttype']=='USD' and r['disordinaryflg']=='Y' and r['distype'] in ('CD','SD','ROC','CG')
                and r['disdetailtype'] in ('CDIV','SDIV','SDROC','ROC','CAPG','CDPSR')
                and finite(r['disdivamt']) and r['disdivamt']>=0
                and r['disfacpr']==0 and r['disfacshr']==0
                and (r['dispermno'] is None or r['dispermno']==0)):
                kinds.append('ordinary_cash')
            else:
                return EventDecision(False,False,'unsupported_event','rights_received_asset_or_ambiguous_terms',len(records),n_del)
        kind='ordinary_cash_and_split' if len(set(kinds))>1 else kinds[0]
        return EventDecision(False,True,kind,'supported_dated_event_terms',len(records),n_del)
