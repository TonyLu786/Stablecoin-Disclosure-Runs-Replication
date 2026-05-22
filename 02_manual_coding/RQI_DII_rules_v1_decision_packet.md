# RQI/DII Rules v1 Decision Packet

Date: 2026-05-22

## Purpose

This packet prepares the human T009 checkpoint. It does not freeze rules. It identifies the decisions required before baseline or event-study results can be interpreted as academic evidence.

## Current Coding Status

- USDC monthly assurance events coded: 36.
- RQI computable in pilot coding: 29 events.
- DII computable in pilot coding: 24 events.
- USDC daily market rows with RQI as-of available: 830.
- USDC daily market rows with DII as-of available: 1041.
- Rows inheriting manual-review flags in the minimum viable panel: 851.

## Decision 1: RQI Asset Weights

Current pilot weights:

| asset class | pilot weight | rationale | decision needed |
|---|---:|---|---|
| U.S. Treasury securities | 0.95 | high liquidity and sovereign credit quality, with small valuation/operational discount | approve or revise |
| Treasury repo | 0.95 | collateralized short-term liquidity, but counterparty/settlement structure still matters | approve or revise |
| Circle Reserve Fund cash | 1.00 | money-market-fund cash line treated as highest liquidity in the current pilot | approve or revise |
| regulated-institution cash | 0.80 | liquidity exposed to banking stress and custodian concentration | approve or revise |
| residual/other assets | 0.20 | conservative treatment of uncoded or less transparent residual assets | approve or revise |

Recommended v1 choice: keep the current pilot weights for v1, but require robustness checks with bank cash at 0.70 and 0.90.

## Decision 2: Early-2022 Aggregate Reports

Issue: January-June 2022 USDC reports do not expose the same detailed reserve categories as later reports.

Recommended v1 choice:

- Keep these rows in DII coding.
- Do not impute RQI from later composition.
- Code granularity below CUSIP-level detail.
- Use them in disclosure-timing analysis but exclude them from RQI coefficient interpretation unless robustness requires a balanced sample.

## Decision 3: April 2023 Stress-Period USDC Report

Issue: April 2023 contains large timing/settlement adjustment lines; automated component extraction exceeds total reserve assets.

Recommended v1 choice:

- Keep DII and event timing.
- Leave RQI missing until manual visual verification.
- Add a separate `manual_component_adjustment` note if the researcher manually reconciles the table.

## Decision 4: Auditor / Assurance Provider Coding

Issue: 2023-2024 auditor identity is not always visible in extracted text.

Recommended v1 choice:

- Do not rely on OCR text alone.
- Verify auditor/provider from PDF visual inspection or official Circle transparency page.
- Until verified, code `assurance_score` as provisional and retain `manual_review_required=1`.

## Decision 5: Circle Weekly Reserve and Mint/Burn Disclosures

Issue: Weekly disclosures are not identical to monthly assurance reports and should not be silently folded into monthly DII.

Recommended v1 choice:

- Treat weekly reserve/mint-burn disclosures as separate disclosure events.
- Monthly assurance reports retain high assurance score but lower frequency score than weekly disclosures.
- DII as-of value can later be constructed as a composite of latest monthly assurance plus latest weekly transparency data.

## Decision 6: Stress-Regime Calendar

Current provisional windows:

| regime_id | type | start | end | status |
|---|---|---|---|---|
| CRYPTO_TERRA_2022 | crypto_native_stress | 2022-05-07 | 2022-05-20 | provisional |
| CRYPTO_FTX_2022 | crypto_native_stress | 2022-11-06 | 2022-11-20 | provisional |
| BANKING_SVB_SIGNATURE_2023 | banking_stress | 2023-03-10 | 2023-03-20 | provisional |
| BUSD_PAXOS_2023 | regulatory_issuer_stress | 2023-02-13 | 2023-03-31 | provisional |

Recommended v1 choice: approve these as candidate windows for pilot heterogeneity, but require event-study robustness with shorter +/-3 day and +/-7 day windows.

## Decision 7: Interpretation Rule

Recommended v1 rule:

No RQI/DII coefficient should be interpreted as evidence of causal effect until:

1. RQI/DII rules are frozen.
2. Market-data abnormal-price handling is approved.
3. USDT and Paxos disclosure coding are added or the release documentation explicitly states that the first empirical exercise is USDC-only.
4. Event-study results are checked against the baseline time-series model.

## Human Approval Checklist

- [ ] Approve or revise RQI asset weights.
- [ ] Approve treatment of early-2022 aggregate USDC reports.
- [ ] Decide April 2023 manual component treatment.
- [ ] Verify 2023-2024 assurance provider coding.
- [ ] Decide whether weekly Circle disclosures enter DII as separate events.
- [ ] Approve stress-regime calendar for pilot analysis.
- [ ] Approve interpretation boundary before any release-level results language.
