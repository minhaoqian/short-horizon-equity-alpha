# Stage 4E — quote prerequisite stopped for review

Date: 2026-10-06. RL-073–074. Conditional structure approved; feasibility NOT RUN.

## Methodology check and evidence

Read AGENTS, complete methodology, latest log and approved Stage4E proposal. Permitted: precise cached quotation/flag certification, signed accounting and execution feasibility. Prohibited: PnL, Sharpe, drawdown, candidate selection, new fitting, holdout outcomes and settlement-cap expansion. Historical Stage4D D/M remain unidentified; proposed D0/D2/D5 remain equally reported assumptions.

A narrow cached-parquet query for HSBC ADS PERMNO87033 on March28,2003 returns exactly one row with a positive finite DlyPrc and DlyPrcFlg=TR. Local official CRSP CIZ guide defines DlyPrc as the last regular-session trade (otherwise bid/ask average), and TR as closing trade. Thus the cached value is certified as a CRSP regular-session closing trade, not a bid/ask fallback. Raw data were not scanned. Private price/evidence manifest: data/interim/stage4e_scenarios/quote_certification_gate.json, ignored and not committed.

The [contemporaneous issuer circular, §2.2.2(b), printed p81](https://www1.hkexnews.hk/listedco/listconews/sehk/2003/0227/ltn20030227105.pdf) specifies the effective-date ADS closing quotation as reported in the Wall Street Journal US National Edition. TR establishes CRSP trade semantics; it does not prove the quoted publication's value is identical. No contemporaneous WSJ quote or provider equivalence evidence is present in the reviewed cache. Two narrow quotation searches recovered no qualifying corroboration; unrelated results were rejected. No further historical-settlement search was reopened.

## Explicit stop

The approved proposal requires certification of the specified quotation before implementation. Provider closing trade certification passes; specified-publication certification remains unresolved. Do not silently substitute the CRSP close or another date. No adapter, accounting tests, six-cohort valuation or scenario feasibility rerun has started. Scenario resolved/unresolved counts and operational fractions therefore remain NOT EVALUATED, not zero or failures. All Stage4A/B/C/D artifacts and frozen methodology remain unchanged.

Next review action: decide whether the hypothetical Stage4E cash convention may explicitly use the verified same-date CRSP closing trade as its named reference, rather than claiming the issuer-specified WSJ quotation. This would be a documented convention clarification/change requiring research-lead approval; no such change is applied here. Alternatively certify the specified WSJ quotation. No new data request or authentication initiated. Documentation-only QA; no new test result claimed.
