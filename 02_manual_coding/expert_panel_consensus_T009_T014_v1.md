# Expert Panel Consensus for T009/T014 v1

Date: 2026-05-22

## Executive View

The panel consensus is that the project is ready for controlled pilot empirical analysis, but not ready for final inference. The strongest current evidence is not the estimated RQI/DII coefficients; it is the reproducibility of the data pipeline from official disclosures to daily de-peg outcomes.

The panel recommends a conservative rule-freeze path:

1. Freeze RQI/DII v1 only as a documented pilot rule.
2. Keep early-2022 aggregate USDC reports in timing/DII analysis but out of RQI interpretation.
3. Treat 2023-2024 auditor/provider fields as provisional until manually verified.
4. Use +/-3 and +/-7 event-study windows as primary.
5. Treat +/-14 windows, stress interactions, and BUSD/TUSD abnormal-price results as robustness or diagnostics.

## Round 1: Independent Expert Assessments

### E1: Stablecoin Reserve/Accounting Expert

The current RQI weights are economically interpretable but should remain provisional. Treasury securities and Treasury repos can both receive high liquidity scores, but banking-system cash deserves a discount because SVB-style stress is precisely the mechanism under study. Early-2022 aggregate reports should not be forced into a detailed reserve-quality score.

Assessment level: B for current weights with robustness; C for early-2022 RQI imputation.

### E2: Empirical Finance Econometrician

The baseline model is valuable as a pipeline test, but single-issuer time-series coefficients should not be interpreted as general stablecoin evidence. Tail outcomes are rare: USDC has only 13 days above 50bp and 2 days above 100bp in the current daily panel. Event-study windows are cleaner at +/-3 and +/-7 days; +/-14 days introduces overlap concerns.

Assessment level: B for pipeline feasibility; C for substantive coefficient interpretation.

### E3: Market Microstructure/Data Expert

Daily DeFiLlama prices are sufficient for first-pass de-peg outcomes but not for intraday run dynamics. USDC's 2023-03-12 daily de-peg is visible, but intraday depth and recovery speed cannot be recovered from this panel. BUSD 2024 and TUSD deviations require separate abnormal-price handling because they may reflect lifecycle or market-quality issues rather than ordinary reserve-risk responses.

Assessment level: B for daily pilot panel; C for run-timing claims.

### E4: Disclosure/Regulatory Expert

USDC monthly assurance reports are scheduled disclosure events. The current USDC event set therefore cannot identify scheduled vs ad hoc differences. Paxos/BUSD regulatory events and Tether reserve-report releases are necessary before the analysis can make disclosure-type comparisons. Stress-regime windows are plausible as candidate windows but must be labeled provisional.

Assessment level: A for scheduled USDC classification; C for scheduled-vs-ad-hoc claims.

### E5: Reproducibility/Data-Engineering Expert

The project now has a strong audit trail: raw sources, extraction scripts, market data scripts, panel construction, baseline models, and event-study outputs. The remaining risk is rule mutability. Once the researcher chooses among the decision options, the project should create a frozen config file and rerun all downstream scripts.

Assessment level: A for reproducibility structure; B for rule-freeze readiness.

## Round 2: Cross-Examination

### Challenge 1: Should low-confidence rows enter models?

Panel answer: yes for pipeline testing, no for final interpretation unless either manually corrected or explicitly retained with robustness. Models should report high-confidence-only variants.

### Challenge 2: Should RQI missing values be imputed?

Panel answer: no for v1. Imputation would create false precision because early-2022 reports differ structurally from later detailed reports.

### Challenge 3: Are current stress windows acceptable?

Panel answer: acceptable as candidate windows, not as final causal identification. Use primary stress windows plus shorter +/-3 and +/-7 robustness windows.

### Challenge 4: Can the event study be interpreted now?

Panel answer: only as scheduled-disclosure mechanics for USDC. It cannot support a scheduled-vs-ad-hoc claim until ad hoc events are added.

### Challenge 5: Should weekly Circle disclosures be folded into monthly DII?

Panel answer: no. Weekly reserve/mint-burn disclosures should become separate disclosure events or a separate component in a composite DII.

## Round 3: Consensus Recommendations

| decision | consensus recommendation | quality level | reason |
|---|---|---|---|
| RQI weights | Keep current v1 weights, require bank-cash robustness at 0.70 and 0.90 | B | Economically interpretable, but banking cash is central to stress mechanism |
| Early-2022 aggregate reports | Use for DII/timing; exclude from RQI interpretation | A | Avoids false precision and protects comparability |
| April 2023 USDC report | Keep DII/event timing; leave RQI missing unless manually reconciled | A | Components exceed total in automated extraction |
| Auditor/provider coding | Verify manually; keep provisional flag until confirmed | A | OCR text is insufficient evidence |
| Circle weekly disclosures | Treat as separate disclosure events in a later data layer | A | Frequency and assurance differ from monthly reports |
| Event-study windows | Primary +/-3 and +/-7; +/-14 robustness only | A | +/-7 has no overlap risk; +/-14 has 10 overlap-risk events |
| Stress calendar | Use as provisional pilot calendar with robustness | B | Plausible windows, but event boundaries are contestable |
| Baseline coefficients | Report only as pilot diagnostics before T009 | A | Single-issuer and rule-provisional setting |

## Recommended Choice Set for Researcher

The panel recommends Option Set B: conservative primary rules with mandatory robustness.

This means:

1. Approve current RQI weights as v1 pilot rules.
2. Require bank-cash sensitivity at 0.70 and 0.90.
3. Exclude early-2022 rows from RQI interpretation.
4. Treat April 2023 RQI as missing until manual reconciliation.
5. Use +/-3 and +/-7 event-study windows as primary.
6. Defer scheduled-vs-ad-hoc claims until USDT/Paxos events are added.

## What the User Needs to Choose

The researcher should choose one of three paths:

| path | description | when to choose |
|---|---|---|
| Path A: maximal conservatism | Freeze only high-confidence rows; defer most model interpretation | Choose if the priority is publication-grade defensibility |
| Path B: conservative pilot primary | Use current v1 rules with explicit robustness and warnings | Recommended for continuing the project efficiently |
| Path C: broad exploratory | Include more provisional rows and interpret only as exploratory | Choose if the priority is rapid discovery over defensibility |

Panel recommendation: Path B.
