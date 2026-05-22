# Data Provenance

This repository releases derived research data and provenance metadata. It does not redistribute raw issuer reports or saved web pages.

## Source Classes

- Issuer disclosure pages and reserve reports are identified by URL, source status, publication date fields, and event identifiers.
- Market price and supply panels are derived from public stablecoin market endpoints and stored as CSV files.
- Researcher-reviewed coding files document RQI/DII rules, manual review flags, source gaps, and event-readiness decisions.

## Raw Source Boundary

The `01_raw_sources/` folder intentionally contains only a notice. Raw PDFs, HTML captures, and third-party source extracts remain outside the public release. Reusers should retrieve source documents from the recorded URLs and verify publication dates before expanding body claims.

## Derived Data

Key derived datasets include:

- `03_market_data/price_supply_panel_raw_v1.csv`
- `03_market_data/stablecoin_market_metadata_v1.csv`
- `04_processed_data/minimum_viable_panel_v1.csv`
- `02_manual_coding/rqi_dii_pilot_coding_v1.csv`
- `02_manual_coding/multi_issuer_disclosure_event_index_v1.csv`
- `06_outputs/variable_dictionary_v1.csv`

## Provenance Fields

Common provenance fields include `source_url`, `source_origin`, `source_status`, `access_date`, `rule_version`, `rule_status`, `manual_review_required`, and `provisional_flag`.
