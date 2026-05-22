# Expert Panel Review Protocol v1

Date: 2026-05-22

## Purpose

This protocol converts the remaining human review items into a structured expert-panel process. It is designed to support objective selection by the researcher, not to replace researcher judgment.

## Scope

The protocol covers:

1. T009: RQI/DII rule freeze.
2. T014: event classification and event-study admissibility.
3. T015 preparation: robustness checks required before substantive claims.

## Expert Roles

| role_id | expert role | primary responsibility |
|---|---|---|
| E1 | Stablecoin reserve/accounting expert | Assess reserve asset classification, cash treatment, assurance-provider coding, and report comparability |
| E2 | Empirical finance econometrician | Assess identification, sample restrictions, event-study windows, rare-event risks, and interpretation boundaries |
| E3 | Market microstructure/data expert | Assess de-peg measurement, daily vs intraday limitations, price-source risks, and abnormal-price handling |
| E4 | Disclosure/regulatory expert | Assess scheduled vs ad hoc disclosure classification, regulatory stress windows, and policy-context coding |
| E5 | Reproducibility/data-engineering expert | Assess audit trail, missingness flags, script reproducibility, and rule-freeze implementation |

## Multi-Round Review Method

### Round 1: Independent Assessment

Each role evaluates the decision using only the existing evidence:

- `rqi_dii_pilot_coding_v1.csv`
- `coding_disputes_v1.md`
- `RQI_DII_rules_v1_decision_packet.md`
- `event_classification_table_v1.csv`
- `event_classification_review_queue_v1.md`
- baseline and event-study pilot outputs

### Round 2: Cross-Examination

Each role challenges one assumption from another role:

- E1 challenges econometric use of low-confidence accounting rows.
- E2 challenges whether single-issuer USDC evidence can support broad claims.
- E3 challenges daily price data for de-peg event measurement.
- E4 challenges whether stress windows are too broad or too narrow.
- E5 challenges whether the selected rule can be implemented reproducibly.

### Round 3: Consensus and Options

The panel assigns each decision:

- recommended option;
- acceptable alternative;
- rejected option;
- rationale;
- implementation consequence;
- residual risk.

## Decision Quality Scale

| level | meaning | implication |
|---|---|---|
| A | Strongly defensible | Can be used in v1 after documentation |
| B | Defensible with robustness | Use as primary only with planned sensitivity checks |
| C | Pilot-only | Use for pipeline testing, not for claims |
| D | Not defensible | Exclude or recode before analysis |

## Output Files

This protocol produces:

- `expert_panel_consensus_T009_T014_v1.md`
- `human_decision_options_v1.csv`
- `robustness_design_v1.md`

## Governance Rule

No rule is frozen by this panel. The panel provides ranked professional choices for the researcher to approve, revise, or reject.
