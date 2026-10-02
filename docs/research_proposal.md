# Research Proposal

## Working title

**Short-Horizon Equity Alpha Forecasting and Cost-Aware Market-Neutral Portfolio Construction**

## Primary research question

Can short-horizon cross-sectional equity forecasts generate economically meaningful market-neutral alpha after realistic risk controls and transaction costs?

## Motivation

The project is designed around the distinction between statistical predictability and implementable alpha. A forecast has economic value only if it survives the mapping from information to signal, from signal to portfolio weights, and from gross portfolio returns to net realised PnL.

The project therefore treats forecasting, portfolio construction, risk control, execution costs, and PnL attribution as separate but connected research layers.

## Scope

### Core study
Use point-in-time CRSP daily US equity data to study short-horizon cross-sectional return predictability using market, price, volume, volatility, and liquidity information.

### Extension study
Conditionally add Compustat/CCM firm characteristics after the CRSP-only pipeline is stable and fully audited.

### Optional implementation extensions
TAQ, I/B/E/S, or securities-lending data may be added only if they answer a clearly defined secondary research question. They are not required for the core study.

## Intended contribution

This project does not claim to invent a new machine-learning algorithm. Its contribution is an auditable, point-in-time research design that explicitly measures how much predictive information survives:

1. out-of-sample forecasting,
2. cross-sectional portfolio construction,
3. beta and industry risk controls,
4. turnover,
5. transaction costs,
6. implementation constraints.

## Primary outputs

- OOS Rank IC and IC decay
- forecast spread by cross-sectional quantile
- gross and net market-neutral portfolio returns
- turnover and cost drag
- beta / industry / style exposure diagnostics
- PnL attribution
- robustness across horizons, universes, and cost assumptions
