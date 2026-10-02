# Sample Construction Protocol

## Objective

Construct an investable point-in-time daily US equity universe without survivorship bias.

## Stage 1A — raw coverage audit

Before applying final thresholds, report by calendar year:

- number of securities
- number of trading observations
- share with valid close / CRSP price
- share with valid open
- share with valid returns
- share with valid market capitalisation
- share with valid volume
- delisting incidence

Also report opening-price coverage by:
- exchange
- market-cap bucket
- ADV bucket

This diagnostic determines whether next-open execution is methodologically defensible.

## Stage 1B — security eligibility

Final filters will be coded from point-in-time security metadata. Candidate criteria include:

- ordinary common equity
- relevant US exchanges
- positive / valid security price
- price above candidate floor
- minimum market capitalisation
- minimum trailing ADV
- sufficient trailing history

The exact CRSP security-type fields will be documented once the CIZ schema is confirmed.

## Stage 1C — liquidity thresholds

Candidate baseline:
- price > $5
- market cap > $1bn
- ADV_20 > $20m

These are starting hypotheses, not final choices.

Final thresholds must be justified by:
- implementability,
- sample breadth,
- stability through time,
- data coverage.

Thresholds must never be selected to maximise backtest performance.

## Survivorship and delistings

The sample must retain securities that later delist. Historical eligibility is determined using information available on each historical date.

## Warm-up

Observations lacking sufficient lagged history for a feature are excluded from that feature/model at that date rather than backfilled with future information.

## Output of this stage

A daily security-level eligibility table:

```
date
permno
eligible
price
market_cap
adv_20
eligibility_reason / exclusion_reason
```

No predictive model may be trained before this stage passes QA.
