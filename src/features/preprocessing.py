"""Date-local finite-value clipping and population standardization, no imputation."""
from math import isfinite, sqrt
from statistics import mean


def quantile(values, q):
    ordered = sorted(values)
    h = (len(ordered)-1)*q
    i = int(h)
    return ordered[i] + (h-i)*(ordered[min(i+1,len(ordered)-1)]-ordered[i])


def preprocess(records):
    """Records keyed by permno/date/feature; preserve every row and input reason.

    Caller supplies all close-date eligible keys, independently of label status.
    Groups are date x feature. No target/status columns are consulted.
    """
    groups = {}
    keys = set()
    for row in records:
        key = row['permno'],row['signal_date'],row['feature']
        if key in keys:
            raise ValueError('Duplicate feature key')
        keys.add(key)
        groups.setdefault((row['signal_date'],row['feature']),[]).append(row)
    result = []
    for group in groups.values():
        valid = [r['raw'] for r in group if isinstance(r['raw'],(int,float)) and isfinite(r['raw'])]
        enough = len(valid) >= 30
        lo, hi = (quantile(valid,.01),quantile(valid,.99)) if enough else (None,None)
        clipped = [min(hi,max(lo,x)) for x in valid] if enough else []
        mu = mean(clipped) if enough else None
        sd = sqrt(mean((x-mu)**2 for x in clipped)) if enough else None
        for row in group:
            raw = row['raw']
            finite = isinstance(raw,(int,float)) and isfinite(raw)
            raw_reason = row.get('reason','observed') if finite else (
                row.get('reason','missing_raw') if raw is None else 'nonfinite_or_invalid_raw')
            clip = min(hi,max(lo,raw)) if finite and enough else None
            z = (0.0 if sd == 0 else (clip-mu)/sd) if clip is not None else None
            reason = ('constant_cross_section' if sd == 0 else 'observed') if finite and enough else (
                'insufficient_cross_section' if finite else raw_reason)
            result.append({**row,'clipped':clip,'standardized':z,'raw_missing':not finite,
                'processed_missing':z is None,'raw_reason':raw_reason,
                'processed_reason':reason,'cross_section_n':len(valid),'clip_lower':lo,'clip_upper':hi,
                'clipped_mean':mu,'clipped_population_sd':sd,'constant_cross_section':enough and sd == 0})
    return result
