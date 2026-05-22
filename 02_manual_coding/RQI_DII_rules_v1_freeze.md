# RQI/DII Rules v1.0 Freeze Memo

Date: 2026-05-22

## Freeze Status

The RQI/DII coding rules are frozen as `RQI_DII_v1.0` for the next research stage. The researcher confirmed all expert-panel default selections in the researcher decision record.

The selected strategy is **Path B: conservative pilot primary with mandatory robustness**. This permits continued empirical pipeline development while keeping all substantive claims inside a pilot-design boundary.

## Confirmed Decisions

| decision_id | topic | frozen choice | implementation consequence |
|---|---|---|---|
| D001 | RQI asset weights | Keep pilot primary weights; require bank cash robustness at 0.70 and 0.90. | Primary RQI uses Treasury 0.95, repo 0.95, reserve-fund cash 1.00, bank cash 0.80, residual other 0.20. Robustness profiles are stored in config. |
| D002 | Early-2022 aggregate reports | Keep for DII/timing; exclude from RQI interpretation. | Early aggregate disclosures can anchor publication timing and disclosure intensity, but should not support RQI composition claims. |
| D003 | April 2023 USDC report | Keep DII/event timing; leave RQI missing. | The event remains in event-study timing, but automated RQI is not used until manual table reconciliation is complete. |
| D004 | Auditor/provider coding | Keep provisional until visual or official verification. | OCR-derived auditor fields remain review flags and should not become final issuer-quality evidence. |
| D005 | Circle weekly disclosures | Treat weekly disclosures as separate events. | Weekly disclosures are not folded into monthly assurance DII; they become a future event layer. |
| D006 | Event-study windows | Use +/-3 and +/-7 as primary; +/-14 as robustness only. | Event-study scripts should treat 3-day and 7-day windows as primary pilot windows. |
| D007 | Stress-regime calendar | Use current windows as provisional with short-window robustness. | Stress interactions may be used diagnostically, but calendar sensitivity remains required. |
| D008 | Interpretation boundary | Allow pipeline and pilot-design claims only. | No final causal, policy, or cross-issuer substantive conclusion is allowed at this stage. |

## Machine-Readable Rule File

The script-readable version is stored at:

`00_admin/rqi_dii_rules_v1_config.json`

All downstream outputs generated after this freeze should carry:

- `rule_version = RQI_DII_v1.0`
- `rule_status = frozen_confirmed_by_researcher`

## Remaining Human Review Flags

Rule freeze does not mean all evidence is final. The following review gates remain active:

1. Visual or official-source verification of 2023-2024 Circle assurance provider names.
2. Manual reconciliation of low-confidence or component-mismatch reserve tables.
3. Event-classification expansion for ad hoc issuer events and weekly disclosures.
4. Market-data abnormal-price decisions, especially lifecycle or exchange-source artifacts.
5. Multi-issuer source expansion before any generalizable stablecoin-market claim.

## Research Implication

The project is now ready for substantive **pilot empirical work** under a stable rule set. It is not yet ready for final release-level empirical inference. The correct next stage is to rerun the P0-C, P0-D, P1-A, and P1-B pipeline under `RQI_DII_v1.0`, then execute robustness and source-expansion tasks.
