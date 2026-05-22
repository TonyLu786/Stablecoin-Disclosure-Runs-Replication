# Event Classification Review Queue v1

Date: 2026-05-22

## Purpose

This file prepares the human review required for T014. It does not freeze event-study classification.

## Current Event-Study Coverage

- USDC disclosure rows reviewed: 36.
- Events included in event study: 24.
- Rows excluded because `publication_date` is missing: 12.
- Included events requiring manual review: 18.
- Included events with RQI available: 18.
- Included events with DII available: 24.
- Events with +/-7 day overlap risk: 0.
- Events with +/-14 day overlap risk: 10.

## Excluded Events: Missing Publication Date

These events cannot enter publication-date event study until the publication date is manually verified.

| event_id | report_date | issue |
|---|---|---|
| USDC_ASSURANCE_2022_05 |  | no report date and no publication date |
| USDC_ASSURANCE_2023_10 | 2023-10-31 | no publication date extracted |
| USDC_ASSURANCE_2023_12 | 2023-12-29 | no publication date extracted |
| USDC_ASSURANCE_2024_02 | 2024-02-29 | no publication date extracted |
| USDC_ASSURANCE_2024_03 | 2024-03-29 | no publication date extracted |
| USDC_ASSURANCE_2024_04 | 2024-04-30 | no publication date extracted |
| USDC_ASSURANCE_2024_05 | 2024-05-31 | no publication date extracted |
| USDC_ASSURANCE_2024_06 | 2024-06-28 | no publication date extracted |
| USDC_ASSURANCE_2024_08 | 2024-08-30 | no publication date extracted |
| USDC_ASSURANCE_2024_09 | 2024-09-30 | no publication date extracted |
| USDC_ASSURANCE_2024_10 | 2024-10-31 | no publication date extracted |
| USDC_ASSURANCE_2024_12 | 2024-12-31 | no publication date extracted |

## Manual Review Priorities

1. Verify missing publication dates for 2024 reports by visual PDF inspection or official Circle transparency archive.
2. Verify 2023-2024 assurance provider coding; OCR extraction is insufficient.
3. Decide whether April 2023 should receive manual reserve-component reconciliation or remain RQI-missing.
4. Approve scheduled monthly assurance classification for all included USDC events.
5. Decide whether +/-14 day event-study windows are acceptable despite 10 overlap-risk events.

## Current Recommendation

For the next pilot run:

- Use +/-3 and +/-7 day windows as primary.
- Treat +/-14 day windows as robustness only.
- Keep all current event-study outputs provisional until this review queue is resolved.
- Do not present scheduled vs ad hoc comparisons until USDT, Paxos/BUSD, or other ad hoc disclosure events are coded.
