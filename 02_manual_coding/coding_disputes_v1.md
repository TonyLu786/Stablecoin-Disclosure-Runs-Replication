# Coding Disputes v1

Date: 2026-05-22

## Scope

This file lists source-level items from the USDC extraction that remain under human review after `RQI_DII_v1.0` rule freeze.

## Disputes and Review Items

- USDC_assurance_2022_April.pdf: asset_extraction_low, rqi_missing
- USDC_assurance_2022_February.pdf: asset_extraction_low, rqi_missing
- USDC_assurance_2022_January.pdf: asset_extraction_low, rqi_missing
- USDC_assurance_2022_June.pdf: asset_extraction_low, rqi_missing
- USDC_assurance_2022_March.pdf: asset_extraction_low, rqi_missing
- USDC_assurance_2022_May.pdf: no_report_date, asset_extraction_low, rqi_missing
- USDC_assurance_2023_April.pdf: asset_extraction_low, auditor_name_not_text_visible, rqi_missing, components_exceed_total
- USDC_assurance_2023_August.pdf: auditor_name_not_text_visible
- USDC_assurance_2023_December.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2023_February.pdf: auditor_name_not_text_visible
- USDC_assurance_2023_January.pdf: auditor_name_not_text_visible
- USDC_assurance_2023_July.pdf: auditor_name_not_text_visible
- USDC_assurance_2023_June.pdf: auditor_name_not_text_visible
- USDC_assurance_2023_March.pdf: auditor_name_not_text_visible
- USDC_assurance_2023_May.pdf: asset_extraction_low, auditor_name_not_text_visible
- USDC_assurance_2023_November.pdf: auditor_name_not_text_visible
- USDC_assurance_2023_October.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2023_September.pdf: auditor_name_not_text_visible
- USDC_assurance_2024_April.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2024_August.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2024_December.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2024_February.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2024_January.pdf: auditor_name_not_text_visible
- USDC_assurance_2024_July.pdf: auditor_name_not_text_visible
- USDC_assurance_2024_June.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2024_March.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2024_May.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2024_November.pdf: auditor_name_not_text_visible
- USDC_assurance_2024_October.pdf: no_publication_date, auditor_name_not_text_visible
- USDC_assurance_2024_September.pdf: no_publication_date, auditor_name_not_text_visible

## Remaining Human Review Gates

1. Verify whether 2023-2024 Circle assurance provider names should be coded from PDF visual review or official issuer source.
2. Reconcile low-confidence or component-mismatch reserve tables before using affected rows for final RQI interpretation.
3. Add Circle weekly reserve/mint-burn disclosures as separate future event-layer observations.
4. Preserve bank-cash robustness checks at 0.70 and 0.90 as required by the frozen rule file.
5. Preserve March/April 2023 banking-stress coding as provisional pending stress-window robustness.
