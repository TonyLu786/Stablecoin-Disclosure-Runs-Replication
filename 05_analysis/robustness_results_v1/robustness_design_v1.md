# Robustness Design v1

Date: 2026-05-22

## Purpose

This document translates the expert-panel review into robustness work for T015. It is a design file, not a completed robustness result.

## Required Robustness Families

### R1: RQI Asset-Weight Sensitivity

Primary rule being checked:

- Treasury securities: 0.95
- Treasury repos: 0.95
- Circle Reserve Fund cash: 1.00
- Bank cash: 0.80
- Residual/other: 0.20

Required alternatives:

- Bank cash = 0.70
- Bank cash = 0.90
- Treasury repo = 0.90 as a conservative repo haircut variant

Output expected:

- Alternative RQI variables.
- Baseline model rerun for each RQI variant.
- Coefficient comparison table.

### R2: Event-Study Window Sensitivity

Primary windows:

- [-3,+3]
- [-7,+7]

Robustness window:

- [-14,+14], explicitly marked as overlap-risk.

Output expected:

- Event-level pre/post deltas by window.
- Relative-day average paths.
- Summary excluding overlap-risk events.

### R3: Sample Confidence Sensitivity

Required samples:

- all provisional rows;
- rows with RQI available;
- manual-review-free rows;
- non-stress rows only;
- stress rows only as diagnostics.

Output expected:

- Sample diagnostics.
- Baseline coefficient comparison.

### R4: Market Abnormal-Price Handling

Required checks:

- Exclude BUSD wind-down/lifecycle period from cross-coin analysis.
- Flag TUSD large-deviation days for manual review.
- Compare daily DeFiLlama prices with CoinGecko or exchange candles for major de-peg days when feasible.

Output expected:

- Market QC addendum.
- Abnormal-price exclusion flag.

### R5: Stress-Regime Calendar Sensitivity

Required variants:

- current provisional windows;
- short windows around anchor dates;
- SVB-only banking stress for USDC-only analysis.

Output expected:

- Stress-window coefficient/event comparison.

## Execution Boundary

Robustness scripts can be prepared now, but final robustness results should be interpreted only after:

1. T009 RQI/DII rules are frozen.
2. Event classification is approved.
3. Market abnormal-price rules are approved.
