# Stage 1G — Return reconstruction closure

This closes only the close-to-close reconstruction sub-gate. It does not freeze
the five-day next-open target or authorize modelling. No strategy-performance
statistics enter this decision.

## Definition sources and timing

Official July 2026 CRSP documents, obtained through the Morningstar CRSP document
library:

- [Calculations & Index Methodologies Guide](https://assets.contentstack.io/v3/assets/bltabf2a7413d5a8f05/blt948fb9dd4aff01a3/6a454f3183e511651648cf28/CRSP_US_Stock_Databases_Calculations_and_Index_Methodologies_Guide.pdf), pages 5–7 and 11.
- [CIZ User Guide](https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true), pages 13, 18, 33, and 90–91.
- [Official return-duration flag table](https://www.crsp.org/wp-content/uploads/appendix/FlagType_RD.html).

Nonordinary distributions include capital-return amounts and remain in price
return; DlyRetX excludes ordinary dividends, not all distributions. Both amount
fields aggregate distributions with ex-dates after the source previous-price
date and through the current date, on the previous-price basis. Daily
reinvestment follows ex-dates, not payment dates. The source previous price may
precede the immediately previous trading day. P1/P2 denote two/three trading
periods. Cumulative price adjustment also covers some non-split distributions;
it is not a share-count series. These historical label fields do not establish
advance availability of corporate-action information for features.

The new guide's page 11 also contains legacy monthly-return wording. This audit
uses its daily formula and timing, not that monthly description.

## Validated reconstruction

Let P = DlyPrc, P0 = DlyPrevPrc, F = DlyFacPrc, N = DlyNonOrdDivAmt,
and O = DlyOrdDivAmt. For the CRSP source interval t' to t:

```
R_X = (P * F + N) / P0 - 1
R_T = (P * F + N + O) / P0 - 1
```

These formulas do not use observed DlyRet or DlyRetX to construct the output.
Require finite observed inputs, a positive previous price, nonnegative prices
and period factor, and explicit interval timing. Missing amounts are not set to
zero.

For cumulative factors C at t and C0 at the source price date t', define
A = P/C, A0 = P0/C0 and K = F*C/C0. The equivalent common-basis expression is:

```
R_X = (A * K + N/C0) / A0 - 1
R_T = (A * K + (N+O)/C0) / A0 - 1
```

K must not be silently set to one. This equivalence is an algebraic basis check,
not an independent validation. In the original comparable population P0 equals
the previous observed raw price in every row. For the 45 missing-lag cases the
source date is independently matched by duration and earlier valid price; its
cumulative factor equals the lag-row factor in all 45.

Rejected formulas retained: adjusted-price ratio alone omits nonordinary cash
in some events; adding all nonordinary amounts to that ratio without K double
counts some other events. The latter produces a maximum eligible nonordinary
price-return error of 0.7284507. Neither can replace the validated accounting.

## Coverage and error QA

Errors below are absolute return errors. Cumulative-basis and raw-field outputs
agree to within 1.78e-15 in the original comparable population.

| Population | Return | Count | Maximum | P99 | Median |
|---|---|---:|---:|---:|---:|
| Original comparable | Price | 64,056,350 | 1.3200e-4 | 4.94382e-7 | 2.22222e-7 |
| Original comparable | Total | 64,056,350 | 1.3200e-4 | 4.94382e-7 | 2.22222e-7 |
| Entire locked eligible | Price/Total | 6,699,101 | 4.78846e-6 | 4.95050e-7 | 2.45902e-7 |
| Eligible nonordinary | Price | 10 | 4.66205e-7 | 4.62500e-7 | 2.22972e-7 |
| Eligible nonordinary | Total | 10 | 4.26343e-7 | 4.26226e-7 | 2.77597e-7 |
| Eligible missing lag | Price/Total | 45 | 5.00000e-7 | 4.86928e-7 | 2.09147e-7 |

All ten eligible nonordinary rows are exported with both observed/reconstructed
returns, both errors, cumulative factors, and per-row rounding bounds to local
`results/tables/stage1g/eligible_nonordinary_reconstruction.csv`. All ten are
single-trading-period returns (including weekend D3/D4 durations). None is
excluded. No raw daily-file rescan was required.

### Precision rather than an arbitrary error cutoff

All relevant original-comparable input values conform to six-decimal export
precision. With delta = 0.5e-6, m = 1 amount for price return or 2 amounts for
total return, and reconstructed gross return g, the conservative rounding bound
is:

```
b = delta + (abs(P)*delta + abs(F)*delta + delta**2
             + m*delta + abs(g)*delta) / (P0-delta)
```

This propagates rounding of prices, period factor, distribution amounts, and
observed return. It applies only for P0 > delta; undefined bounds must not be
counted as passes. The original comparable and eligible populations contain no
such undefined cases. A fixed 1e-10 arithmetic allowance is added for checking.
No errors exceed this bound and no reconstructed outputs are nonfinite.

The full-market largest errors arise in small-price/factor cases, where rounded
factors and fractional previous prices magnify the absolute error. Seven
eligible returns exceed 1e-6; all are within the same precision bound. This is
consistency with exported precision, not proof of each unrounded source value.
The first provisional bound omitted previous-price rounding and failed for
nine low-price rows; that incomplete bound is rejected and preserved in RL-033.

## The 45 missing previous prices

All 45 have a row on the immediately preceding market trading date with MP
(Missing Price), missing DlyPrc and DlyOpen, and zero volume. None is a missing
row or a listing-start case: earlier valid observations exist, and the source
price matches them exactly. There are 41 P1 cases with one intervening missing
price and four P2 cases with two intervening missing prices. All relevant
intervening prices are absent; no valid price is skipped.

Historical metadata records Active for each immediately previous day, with no
recorded Halt/Suspended status. No current/previous-day factor/distribution
or delisting event explains the gaps. This does not prove absence of an
intraday halt or identify the physical cause of the vendor's missing quote;
the documented observable cause is MP on an existing row. No speculative
causal label is required for the following timing-safe disposition.

- Retain the eligible signal observations and a missing-price/multi-period flag.
- DlyPrevPrc safely reconstructs the source two/three-period return, available
  at the current close; it does not reconstruct a one-period return or a price
  on the missing date.
- Do not interpolate, forward-fill, or spread the multi-period return over
  days. It cannot be used across an execution boundary without checking its
  actual source interval.
- Do not blanket-exclude these signal dates because an earlier price is missing.
  Missing execution endpoints or incompatible holding intervals require separate
  treatment in the still-unstarted endpoint/delisting target sub-gate. No target
  fallback or execution price is approved by this reconstruction closure.

Local per-case evidence is retained in `missing45_full_context.csv` and
`missing45_source_anchor.csv`. Row-level licensed outputs and caches are not
committed.

## Reproduction and controls

Run `scripts/14_validate_distribution_reconstruction.py` against the existing
fingerprinted caches. Reusable accounting and diagnostics are in `src/data/`.
Six focused unit tests cover distribution classification, split neutrality,
cumulative-basis double counting, missing-input handling, fractional-price
rounding, and multi-period timing. Full-cache integrity reproduces all original
counts and locked eligibility, with complete formula coverage and no nonfinite
outputs. No next target sub-gate was executed.
