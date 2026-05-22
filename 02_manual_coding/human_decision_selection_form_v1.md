# Human Decision Selection Form v1

Date: 2026-05-22

Researcher confirmation: all selected expert-panel options were confirmed in the researcher decision record on 2026-05-22. These choices are frozen as `RQI_DII_v1.0`.

## How to Use

Select one option for each decision. The expert-panel recommendation is pre-marked as the default. The researcher has now confirmed the selected options, so this form is locked as the human approval record for `RQI_DII_v1.0`.

## Overall Path

- [ ] Path A: maximal conservatism; freeze only high-confidence rows and defer most interpretation.
- [x] Path B: conservative pilot primary; use current v1 rules with mandatory robustness. Expert-panel recommendation.
- [ ] Path C: broad exploratory; include more provisional rows but keep all claims exploratory.

## D001: RQI Asset Weights

- [ ] A: Use stricter primary bank cash weight 0.70.
- [x] B: Keep pilot weights; require bank cash robustness at 0.70 and 0.90.
- [ ] C: Raise primary bank cash weight to 0.90.

## D002: Early-2022 Aggregate Reports

- [ ] A: Exclude early-2022 reports from all analysis.
- [x] B: Keep for DII/timing; exclude from RQI interpretation.
- [ ] C: Impute RQI from later composition.

## D003: April 2023 USDC Report

- [ ] A: Manually reconcile reserve table and code adjusted RQI.
- [x] B: Keep DII/event timing; leave RQI missing.
- [ ] C: Use automated RQI despite component mismatch.

## D004: Auditor / Assurance Provider Coding

- [ ] A: Freeze from OCR text.
- [x] B: Keep provisional until visual or official verification.
- [ ] C: Use issuer-level transparency page as sufficient source.

## D005: Circle Weekly Disclosures

- [ ] A: Fold weekly disclosures into monthly DII.
- [x] B: Treat weekly disclosures as separate events.
- [ ] C: Ignore weekly disclosures for current analysis.

## D006: Event-Study Windows

- [ ] A: Use +/-3 only as primary.
- [x] B: Use +/-3 and +/-7 as primary; +/-14 robustness only.
- [ ] C: Use +/-14 as primary.

## D007: Stress-Regime Calendar

- [x] A: Use current windows as provisional with short-window robustness.
- [ ] B: Use only SVB banking stress for USDC pilot.
- [ ] C: Use broad stress windows without robustness.

## D008: Interpretation Boundary

- [ ] A: Allow substantive RQI/DII claims now.
- [x] B: Allow pipeline and pilot-design claims only.
- [ ] C: Pause all modeling until every source is complete.

## Researcher Notes

Add modifications here before rule freeze:

-
