# Stage 4A — proposed cost-aware portfolio protocol

Date: 2026-10-06. Status: PROPOSED / research-lead review required (RL-060).
No portfolios, weights, PnL, costs or Sharpe have been computed. Stage 1–3 contracts unchanged.

## Methodology gate and candidates

Permitted evidence: frozen timing/universe/wealth ledger, existing data definitions, cached schedule and implementation feasibility; official order/short-selling guidance. Prohibited: new model fits, holdout access, portfolio/cost performance, result-driven choice of constraints, coefficients, costs or candidate. Design constants below are proposed assumptions, not estimated transaction costs or a proven capacity claim.

Primary candidates: unchanged Stage 3A `uni_reversal_5` and `ridge`; `equal_weight` control only. Use their stored forward forecasts, quarterly coefficients and common complete-eight input policy, without sign flips or reranking on numeric-label subsets. No wider reversal-only feature sample. Retain every original eligible key with portfolio-decision reason; target status cannot select positions. Initial weights need no target join.

## Dated protocol and boundary

- Signal decisions: all global trading dates 2003-01-02–2019-12-31.
- Forecast versions: existing 68-quarter dated Stage 3A schedule; no refits.
- First scheduled entry: 2003-01-03; first exit: sixth market date after the 2003-01-02 signal, derived from the frozen calendar.
- Empty initial book; no pre-2003 candidate signals. Explicit five-day ramp-up, no fictitious full exposure initially.
- Stop new signals after 2019-12-31. Keep every already-created five-day holding and its original planned exit; no forced 2019 liquidation or removal of late development signals.
- Daily performance window: first entry through last development-sleeve exit. Report 2003–2019 calendar performance separately from the pending development-origin runoff. Trading days/cutoffs use the global market calendar, never next available security row.
- **Permission gate:** late-2019 holdings require 2020 open/ledger marks for runoff and possibly daily accounting. Existing frozen development endpoint labels are permissible; they do not supply all required daily marks. No 2020 source records are accessed in Stage 4A. Before implementation, obtain explicit approval for an isolated development-origin runoff projection if needed, with no 2020 signal/forecast/eligibility/holdout performance. Without it, record pending runoff; full-horizon evaluation remains incomplete, not silently truncated.

## Holding architecture and capital

Five overlapping sleeves, one new sleeve each trading day, each held exactly entry open t+1 to planned exit open t+6. Each phase is market-index modulo five, anchored 1993-01-04. At an opening, retire the due sleeve then open its replacement. No daily rebuilding, intermediate score-based trades, horizon shifts or retrospective eligibility re-filtering. Split/share transformations and independently measured cash termination are ledger events, not discretionary rebalances.

Fixed reference capital N=$10m per candidate; sleeve reference capital B=N/5=$2m. New sleeve target long B, short B: planned gross 200% and net zero relative to reference capital, once all five sleeves are active. Capital is not increased after gains or reduced after losses; all return/turnover figures use N. This makes capacity assumptions and cross-candidate comparisons transparent. Report daily actual NAV separately; no bankruptcy continuation if measured NAV becomes nonpositive (review gate).

At close t, calculate planned dollar positions using only through-t inputs. Orders are fixed share quantities valued with a positive observed close t, adjusted only for verified share-basis transformations effective before entry. Use fractional shares in this research simulation, no assumed auction price for sizing. Observed open t+1 measures fills; it cannot retrospectively size orders. Therefore actual opening dollar neutrality, gross and caps can drift with gaps. Do not call ex-ante dollar neutrality exact realized neutrality. Report realized gap imbalance; no same-open hindsight hedge or rescaling. A hard realized-zero-neutrality strategy would require a separately approved execution mechanism. Holdings drift between openings; no hard realized cap liquidation.

## Rank mapping, ties and caps

Same finite-score eligible pool for both candidates, at least 100 names. Average-tied percentile u=(rank-.5)/n. Long if u>=.8, short if u<=.2; exclude the middle. Require at least 25 names on each side. Constant scores, insufficient side breadth or infeasible constraints yield an explicitly unallocated sleeve for that candidate; no fallback signal. Tie blocks are never arbitrarily split; record breadth and cash. Keep the other candidate's planned trades on that date and include both books on the same calendar, no paired-date selection based on future outcomes.

Within each selected side, desired equal dollar allocation, deterministically capped and redistributed only among the originally selected names. Maximum per-name absolute sleeve weight =2% of B ($40k at full deployment). Sum five co-directional sleeve caps =2% of N at decision-price basis. No relaxation or moving quantile thresholds. Compute each side's feasible capacity, choose common deployed amount L=min(B,long capacity,short capacity); water-fill capped equal allocations to L on both sides. Unallocated capital is cash at zero interest. No volatility/risk optimization or score-magnitude leverage. All constants identical for both candidates/control.

## Liquidity and execution

Keep locked price/size/ADV20/classification universe unchanged; ADV20 uses the existing through-t dollar-volume calculation with 15 valid of20, not future volume or an exponentiated clipped feature. Cache field provenance must be checked before implementation. Close t inputs size entry and constrain orders; decision on t+1 cannot use that day's full volume.

Opening-auction assumption: pre-submitted market-on-open style orders, filled at a positive observed regular-session open plus explicit modeled costs, conditional on assumed auction/borrow access. CRSP open is a benchmark, not evidence of available auction depth or guaranteed fill.

Aggregate gross planned same-security entry and scheduled exit flow across sleeves, do not net it for capacity or baseline cost. Limit new entries so total modeled flow valued at close t is <=1% ADV20_t: new entry allowance=max(0,.01*ADV20_t-|scheduled exit shares|*Pclose_t). Share-adjust existing orders consistently. If required closing flow alone exceeds the limit, honor the scheduled exit in the benchmark simulation, flag breach and report an implementability exception; do not cap mandatory exits and silently extend the horizon. Missing valid sizing/ADV evidence cannot create an entry. Missing price/ADV evidence for an existing holding remains an unresolved trade/valuation issue. No intraday volume-derived fill decisions.

No cross-sleeve netting in the primary calculation; charge both retirement and replacement transactions to avoid assuming free internal execution. Opposite virtual sleeve positions may coexist and receive gross borrowing/cost charges. Report gross virtual exposures and consolidated legal/net-share exposures separately. An explicitly labeled internal-crossing sensitivity may charge actual net external flow; it cannot replace the conservative primary result.

## Neutrality and exposures

Baseline: ex-ante dollar neutrality per new sleeve, report actual dollar net/gross, imbalance and drift for the combined book. Beta neutrality and sector/industry neutralization deferred; baseline is a dollar-neutral design, not certified beta/sector neutrality. No unavailable risk-data source introduced at this gate. Report through-t sector weights if cached point-in-time classifications exist; otherwise explicit unavailable diagnostics. Historical/static classifications cannot backfill sectors.

For beta diagnostics, use a cached officially defined CRSP US broad-market total-return series only after schema/through-t calendar QA. If unavailable, stop for a narrow separate data request before claiming beta neutrality. Ex-post full-development OLS net daily return on matched market daily return is diagnostic, not a sizing input; report intercept/beta HAC20 and fixed4 sensitivity. No resulting beta estimate changes positions. Cash/receivables and unresolved exposure shown separately. Do not construct a hindsight benchmark from future-surviving constituents.

## Proposed transaction-cost assumptions (not empirical calibration)

For every executed leg k, opening benchmark notional V_k=|q_k|*Popen_k. Cash charge rather than altered share price avoids double counting. Missing benchmark/fill => unknown transaction charge, not zero.

Baseline one-way charge:

c_k = .0005 + .0001 + .10*sigma20_t*sqrt(p_k)

cost_k=V_k*c_k; p_k=aggregate gross planned security flow at close t / ADV20_t. sigma20_t is the unchanged finite raw Stage2A twenty-return sample volatility (decimal daily units), not its z-score. At planned exits use close-before-exit information; no future volume, price range or spread. New-entry complete-eight pool supplies sigma; if it later becomes missing for a scheduled exit, impact is unresolved, no fill or substitute. Formula applies to all flow including flagged participation breaches; it is a scenario, not observed impact.

5bp represents combined half-spread/opening slippage; 1bp is an all-in commission/regulatory fee allowance. Do not add observed spread again. These constants are symmetric by side and fixed across1993–2019; not claimed to reproduce historical broker fees, changing fee schedules or auction spreads. Market impact coefficient .10 is a fixed assumption, with no local-performance calibration.

Borrow fee baseline100bp annual ACT/365 on original short-entry notional, accruing calendar days from entry through before cover; weekends included. Splits do not alter that basis; verified partial corporate repayment reduces the basis proportionally. This fixed-basis convention is an approximation, not historical securities-loan quotes. Short dividend/corporate obligations are debited via the same signed economic ledger, not a second borrowing expense. Cash, margin balances and short proceeds earn/pay zero baseline financing interest/rebate; gross200% is not a claim of unrestricted margin availability.

Prespecified independent sensitivities, all shown without best-case selection: linear execution allowance3/6/12bp; impact coefficient0/.10/.25; borrow100/300/500bp; additional financing drag200bp/year on N using ACT/365. Baseline6bp/.10/100bp/zero-financing kept headline assumption. No combinatorial optimization, changing AUM or ADV limit after observed returns. Historical borrow/recall, short-sale restrictions and auction depth are not certified by CRSP. Both candidates evaluated under the same assumptions; present scenario-net simulated performance, never claim proven executable net alpha absent evidence of these frictions.

Turnover: traded-notional turnover T_d=sum_all_legs V_k/N (both buys and sells). Conventional one-way turnover=T_d/2, reported with that label; charge c*T_d, not c*T_d/2. Corporate asset conversion/payment is not a market trade; verified liquidation trade is. Borrow/time charges separate from traded turnover. Show gross flows before any optional netting, cost components, participation breaches and utilization against ADV.

## Corporate actions, execution ambiguity and ledger

Apply frozen entry<ex-date<=exit entitlement, entry-day rights excluded, exit-day included; no reinvestment, zero cash interest, verified share quantities and established measurable receivables only. Preopening split transformations preserve dollar/share bases; no double addition of DelRet to incorporated wealth. Positive observed parent/successor prices required. Cash delistings can terminate security holdings into cash/claims if independently measurable at that time. Short positions owe corresponding cash/assets; nonnegative long-wealth bounds do not bound a short loss from below.

Maintain sleeve-level signed asset/claim/cash inventories and scheduled orders, with candidate-independent measurement statuses. Pay-date moves receivable to cash without a new return. Each measurable single-security sleeve endpoint must reproduce the frozen target before trading/borrow expenses (signed liability for shorts). Endpoint labels alone are not a daily portfolio path.

Missing entry open: record planned order, unknown fill/price, unresolved exposure; never infer no-fill from CRSP missingness or volume. Only independently verified nonexecution cancels the order; no immediate replacement/reallocation using future opens. An optional explicitly hypothetical missing-open=no-fill scenario may be reported as sensitivity, not the primary ledger.

Missing exit/delist/successor valuation: retain holdings/obligations and known components, planned exit remains t+6, unresolved wealth/actual liquidation cannot be repaired using later prices. Do not route residuals into a new tradable sleeve or sell on the first later available open as if the horizon had changed. Unknown quantities, rights/property and unresolved corporate terms remain explicit. No imputed zero, -100%, interpolation or forward-fill. Unobserved daily marks likewise make NAV/exposure unknown; do not bridge a gap and treat a multi-day move as a daily return.

**Headline gate:** full daily gross/net performance, volatility/Sharpe/drawdown and candidate selection require a complete valid portfolio ledger over the stated performance interval. If any traded unresolved component prevents that, headline quantities remain unavailable or explicit bounds. Report affected orders/dates/notional/counts and measurement-conditioned diagnostics only, never silent deletion or a zero contribution. No arbitrary de-minimis threshold to ignore unknown wealth. Known-component PnL is not total portfolio PnL. Bounds assumptions need review if economic claim quantities/upper bounds cannot be established. No new extraction authorized by this proposal.

Borrow/locate availability: absent contemporaneous records, short fills are an explicit conditional assumption. CRSP active/common/liquid status is not evidence of a locate. No future event/target flag supplies that evidence. A deployable implementation needs separate availability/recall/short-sale restriction evidence; failures trigger review, not retrospective security filtering.

## Evaluation, inference and selection rule proposed before results

All candidates/control use identical dates, common signal pool, capital, order/ledger/cost rules. No result-based override. Separate structural zero-position days from unknown measurement days; never manufacture zero PnL on an unknown day. Candidate-specific unavailable marks do not select favorable dates for paired comparison; common-date conditional diagnostics explicitly report original-denominator attrition and its nonrandom nature.

At consecutive opening boundaries d,d+1, track signed holdings and established claims, cash and executed costs. Gross PnL is change in total wealth before transaction/borrow/financing expenses, excluding internal transfers; cash principal is not income. Net PnL subtracts all charges. Fixed-capital returns r_d=PnL_d/N; annual mean=252*mean(r), volatility=sqrt(252)*sampleSD(r), nominal Sharpe=sqrt(252)*mean(r)/sampleSD(r), zero reference cash rate. These are fixed-capital arithmetic ratios, not compounded investment returns. Also report actual NAV=N+cumulative net PnL, peak-to-trough relative NAV drawdown and calendar-day drawdown duration only when the path is completely measured. No average of overlapping five-day target returns masquerading as daily portfolio PnL.

Report total/annual gross and net PnL, daily/annual returns, volatility, Sharpe, drawdown, gross/one-way turnover, each cost drag, dollar/beta/sector exposures, realized position concentration, participation, missing execution/valuation and borrowing qualifications. Date/year/status denominators include all original eligible signals. Five sleeves generate serial dependence; primary mean-return inference Bartlett HAC20, fixed4 sensitivity, original calendar positions. Nominal Sharpe is not accompanied by IID t-stat. Paired net-return difference uses same HAC20/4. No performance-driven lag/phase selection. Report all five separate sleeve-phase daily paths as fixed robustness, not independent samples. No new forecast horizon.

Selection is deferred until data/execution/measurement gates pass. Precommit: reversal is simpler default; choose Ridge only if (i) all applicable accounting/capacity gates pass for both; (ii) its baseline annual arithmetic net mean exceeds reversal; (iii) paired mean net difference nominal95% HAC20 lower bound>0; (iv) Ridge-minus-reversal annual net means positive in at least9/17 full signal-year cohorts; and (v) paired net mean remains positive under each one-at-a-time high-cost sensitivity above. Cohort statistics attribute each sleeve's complete lifetime PnL to signal year; daily calendar results reported separately. No benchmark becomes a primary candidate. If neither baseline net mean is positive, recommend neither; if evidence incomplete, declare selection indeterminate. No holdout used to break ties, choose costs, or repair this rule. These selection thresholds are proposed for review, not chosen from portfolio evidence.

## Implementation approval gates and reproducible output plan

Before real portfolios: approve this protocol and scenario assumptions; resolve required runoff permission; audit existing daily/ledger/sizing/market-index schemas and point-in-time flags without performance. Synthetic QA must verify phase timing, fixed shares, capped two-side allocation, dollar planning versus opening-gap drift, duplicate/key preservation, gross flow/cost identities, splits/ex-date/payment timing, short obligations, and unknown measurements propagating to portfolio NAV. Do not silently implement a different rule if constraints/data are infeasible.

Later authorized reusable code under src/portfolio/, entry under scripts/, licensed order/holdings/marks local in data/interim/stage4/. Public aggregates under results/tables/stage4/ and figures under results/figures/stage4/, with conditional qualifications. Expected tables: decisions/coverage, exposures/capacity, cost assumptions/decomposition, ledger QA, annual/paired candidate statistics and all phase/sensitivity results. Expected figures after authorization: gross/net equity and drawdown, turnover/cost drag, exposures, capacity and unresolved-notional paths. No performance figure now; the assumption table is the useful auditable artifact at this review gate.

Official context (no numeric cost calibration): FINRA explains MOO orders and cancellation of unfilled opening portions: https://www.finra.org/investors/insights/time-parameters-qualifiers-stock-orders . SEC Regulation SHO guidance explains locate obligations and dividend compensation by short sellers: https://www.sec.gov/investor/pubs/regsho.htm . These do not establish historical auction fills, borrow availability or the proposed numerical cost assumptions.
