# Stage 1G — Next-open target boundary proposal (OPEN)

This is a proposed accounting specification plus a coverage audit, not a frozen
primary target. No models, IC, Sharpe, PnL, or performance evidence were used.
The official definition changes below correct the interpretation of older QA,
not the locked universe or execution time.

## Economic interval and event rights

Let a be market trading date t+1 and b be t+6. A valid fill buys one post-event
share at the first regular-session open a and plans sale at open b. Eligibility
is evaluated only at signal close t; do not re-filter holdings by eligibility on
future dates.

CRSP CIZ User Guide July 2026, pages 11–13 and 17–18, defines DisExDt as the
first trading date without the distribution right. Hence ownership entitlement
is `a < DisExDt <= b`: entry-date rights belong to the seller; exit-date rights
remain with this holding. This also means an exit-day distribution is retained
without including the subsequent exit-day intraday return. Actual ex-dates,
not record/payment dates or a fixed settlement lag, determine rights.

Sources:
- [Official CIZ User Guide](https://indexes.morningstar.com/docs/guide/crsp-us-stock-databases-guide-for-flat-file-format-2-0?isRdp=true), pages 11–13 and 17–18.
- [SEC ex-dividend guidance](https://www.investor.gov/introduction-investing/investing-basics/glossary/ex-dividend-dates-when-are-you-entitled-stock-and).
- [FINRA Rule 11140](https://www.finra.org/rules-guidance/rulebooks/finra-rules/11140).
- CRSP Calculations Guide July 2026, pages 6–7 and 11; local copy and URLs in `stage1g_return_reconstruction.md`.

Special distributions may use delayed ex-dates and due bills. No historical
record-date rule is substituted for DisExDt. The daily amount fields aggregate
the source return interval; a multi-period amount cannot establish an individual
ex-date. The cache audit finds zero observed multi-period amount/factor events
in offsets 2–6, but this does not identify payment type or successor securities.

## Explicit proposal: preserve assets and claims through b

Candidate accounting convention, not yet locked: cash proceeds and fixed cash
receivables earn zero interest and are not reinvested. This avoids assuming
cash received at ex-date or an additional financed close-price reinvestment.
CRSP's close-to-close reinvested return remains a source consistency check;
it is not automatically the next-open holding return.

Maintain quantity q, parent/successor security positions, cash, and receivables
from actual events. Start q=1 at a only with a verified positive finite entry
open. Use actual event payment type, amounts and share factors. Apply eligible
split/share transformations before the relevant opening transaction, including
an exit-day split; entry-day transformations precede buying and do not create
an entitlement to pre-entry distributions. For a pure split, verify the quantity
ratio against DlyCumFacShr. Never use DlyCumFacPr as a share-count factor.

At b, value/sell every retained tradable security at its valid b open, add fixed
cash claims already earned, and value other outstanding claims only with a
justified b-time value. Proposed total return is:

```
y = (parent/successor liquidation value at b
     + cash + earned receivable value at b) / entry_open - 1
```

With no action or distribution, this is `exit_open/entry_open-1`.
For a verified cash-only ordinary-distribution path with no share change, it is
`(exit_open + sum(cash amounts with a < ex_date <= b))/entry_open-1`.
Amounts must be on the actual owned-share basis; do not add source previous-share
amounts without accounting for intervening transformations.

Nonordinary amounts alone do not identify whether the shareholder receives
cash, rights, another security, or a mixed payment. Do not convert stock/rights
to invented cash at an unavailable ex-date/open. Need StkDistributions fields
DisExDt, DisSeqNbr, DisOrdinaryFlg, DisPaymentType, DisType, DisDetailType,
DisDivAmt, DisFacPr, DisFacShr, DisPayDt, DisPERMNO/DisPERMCO and relevant
linked-security prices. Boundary events require their actual legal ex-date and
valuation basis. An unpriceable claim remains unresolved, not zero.

## Delisting: actual event date and valuation time matter

DlyDelFlg marks a stored delisting return, not the actual delisting date.
DelDlyDt is conventionally the next market trading date after DelistingDt;
DelAmtDt dates the amount used, which need not coincide with the storage date.
Therefore prior RL-024 / Stage 1E counts of 8,416 are return-flag-window counts,
not a verified census of actual delistings during ownership.

Need StkDelists: DelistingDt, DelDtPrc, DelDtPrcFlg, DelActionType,
DelStatusType, DelReasonType, DelPaymentType, DelPERMNO/DelPERMCO,
DelRet, DelRetMissType, DelNextDt/Prc/PrcFlg, DelAmtDt, DelDivAmt,
DelDisType and DelDlyDt. These are absent from current local extracts.

When delisting occurs after entry, retain the position and track the cash,
security or outstanding claim it becomes. A completed, date-consistent cash
settlement can become cash through b; a share exchange becomes a successor
position; confirmed worthless holdings can be zero only with supporting event
status/value evidence. Unresolved delisting claims or after-b amount dates
cannot be assigned their later settlement value at b. Missing delisting returns
cannot be assigned -100%, zero, or an optimized estimate.

Use an incorporated daily CIZ return once if its entire actual price/amount
interval and distribution treatment match ownership. Alternatively use the
explicit event ledger. Do not append DelRet again to a DlyRet that already
contains it. A daily return stored at the conventional date can use a later
settlement value and is not, by itself, a five-day terminal valuation.

## Missing endpoints and censoring

- Right-censoring: planned b lies beyond the extraction calendar. Mark
  administratively censored; exclude from observed-label evaluation only,
  retaining signal keys. Do not call it a market failure.
- Missing entry: no verified next-open fill value. Mark entry-price unavailable;
  keep the signal key without a return label. Only verified execution failure
  may become a no-fill status. Missing open with observed trades is a data
  failure, not proof of no trade. No invented opening fill or zero return.
- Missing exit after an entry: preserve inventory and any claims; missing price
  cannot mean disappearance or loss of all capital. Recover an actual b fill /
  claim value from valid event/price data; otherwise leave the five-day return
  unresolved. Moving exit to the next observed security row changes the horizon
  and is not allowed as the baseline.

No survivor-only complete-case target is approved. Cases excluded from label
availability must remain in an auditable ledger; a later modelling sample must
not silently hide attrition related to distress or delisting.

## Cache audit — denominator 6,699,101 locked signal observations

All keys remain present exactly once. Positive finite openings reproduce prior
null-open counts; no nonpositive opening endpoints add extra failures.

Mutually exclusive diagnostic paths use priority censoring, missing entry,
return-flag delisting review, missing exit, corporate-factor review, other event
field review, ordinary cash candidate, price-only candidate. These are review
paths, not proof that all event cases are irreducibly unlabelable. Corporate
review conservatively includes entry-boundary events even though their rights
are excluded; event details may clear some of these cases.

| Path | Count | Percent |
|---|---:|---:|
| Price-only candidate | 6,363,239 | 94.986462% |
| Ordinary-cash candidate | 299,291 | 4.467629% |
| Nonordinary/factor review | 12,586 | 0.187876% |
| Right-censored | 8,686 | 0.129659% |
| Missing entry | 7,596 | 0.113388% |
| Return-flag delisting review after entry | 6,916 | 0.103238% |
| Missing exit without return flag | 787 | 0.011748% |

Noncandidate paths total 36,571 (0.545909%); removing deterministic right
censoring leaves 27,885 (0.416250%) historical review/availability cases.
This is not a count of physically proven no-fills or unpriceable delisting claims.
Price-only and cash candidates have zero detected factor/event-field integrity
issues; they are not yet an approved complete modelling sample.

Overlapping endpoint/event counts:
- missing exit, any entry status, noncensored: 14,566 (0.217432%)
- missing exit after valid entry: 7,703 (0.114986%); 6,916 with a return flag,
  787 without; both entry/exit missing: 6,863 (0.102447%)
- daily return flags offsets 1–6: 8,416 (0.125629%); entry 1,468,
  interior 5,563, exit 1,385
- return flags offsets 2–6: 6,948 (0.103715%), the convention-based timing proxy
  corresponding to actual delisting dates offsets 1–5, not a verified event census
- ordinary amounts any offsets 1–6: 360,788 (5.385618%); entry 60,316
  (0.900360%), exit 60,020 (0.895941%), interior 240,523 (3.590377%)
- ordinary amounts offsets 2–6: 300,514 (4.485885%), an entitlement proxy
- nonordinary amounts any offsets 1–6: 8,446 (0.126077%); entry 1,472
  (0.021973%), exit 1,390 (0.020749%), interior 5,584 (0.083354%)
- nonordinary amounts offsets 2–6: 6,974 (0.104104%), an entitlement proxy
- period-factor events: 12,617 (0.188339%); cumulative-factor changes:
  21,030 (0.313923%)

Counts overlap; entry/interior/exit sums are not mutually exclusive event
ownership paths. Daily amounts/return-storage dates remain proxies where event
history is missing.

Entry missing-open causes: 6,012 TR rows with positive volume, 1,461 DA rows,
71 BA rows, 40 MP rows, 7 DP rows, and 5 NT rows. All entry rows exist. TR includes
seven rows with a return flag. Exit failures after valid entry: 5,531 absent
rows, 1,378 DA, 639 TR, 72 BA, 56 MP, 20 NT, 7 DP. Historical metadata and
return-flag overlaps are retained locally; no physical halt cause is invented.

## Gate decision and reproduction

Stage 1G remains OPEN. Event history, delisting history and some endpoint quotes
are missing. The current daily extract lacks DlyPrevDt and DlyRetMissFlg, which
are also needed for authoritative source-date/missing-return attribution.
The scalar amount/daily return fields cannot resolve all ownership and
b-time asset values. No target was built, no exceptional observation was removed,
and no new research stage or model was started.

`scripts/15_audit_target_boundaries.py` / `src/data/target_boundary_qa.py` reuse
fingerprinted partitions; no raw daily-file rescan. Local outputs include
`target_boundary_counts.csv`, `target_boundary_primary_paths.csv`,
`target_endpoint_causes.csv`, `target_endpoint_metadata.csv`, and examples.
Five focused tests check entry/exit rights, global-calendar horizon, censoring
and output count identities. Row-level licensed outputs remain uncommitted.

One next action: obtain compact CRSP CIZ StkDelists and StkDistributions histories
for the flagged securities, including dates, payment types and successor links,
then re-audit this same Stage 1G proposal before any target freeze. Opening-price
measurement gaps must subsequently be resolved or explicitly remain unlabeled;
event extraction alone cannot promise full endpoint coverage.
