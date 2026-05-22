# Research Governance and Replication Workflow

Date: 2026-05-22

This file defines the workflow used to keep source collection, manual coding, derived data, analysis scripts, exported figures, and review records aligned. The workflow is designed for a public replication repository: every substantive output should be traceable to a script, a structured input, and a documented researcher decision where judgment is required.

## Research Responsibilities

The researcher is responsible for:

- research design and contribution boundary;
- issuer and event sample definitions;
- interpretation of ambiguous reserve disclosures;
- final RQI/DII coding decisions;
- source-status closure and citation readiness;
- claim scope and limitations;
- final review before public release.

Scripts and structured logs are used for:

- deterministic data assembly;
- table and figure regeneration;
- rule-version tracking;
- row-count and schema checks;
- source-review queue construction;
- claim-boundary inventory;
- release auditing.

## Standard Work Cycle

Each project stage follows the same documented cycle:

1. Define the input files, output files, and acceptance criteria.
2. Freeze or record the relevant coding rules before downstream reruns.
3. Run the applicable data-support script.
4. Save generated outputs in the project directory structure.
5. Route low-confidence rows, source gaps, and interpretive choices to researcher review.
6. Record the decision in the appropriate queue, memo, or audit table.
7. Re-run downstream scripts only after the decision record is in place.

This cycle keeps the replication chain auditable without treating script output as a substitute for source judgment.

## Rule Freezing

The RQI/DII rule set is frozen under `RQI_DII_v1.0`. Changes to the rule set require:

- a new version label;
- a short decision memo;
- a list of affected variables or rows;
- a rerun of downstream panels, diagnostics, and figures;
- a note in the relevant progress record.

No script should silently overwrite a frozen empirical decision.

## Source Review Gates

Source rows move through four gates:

1. **Indexed**: a source URL, access date, issuer, and event relation are recorded.
2. **Archived or Not Redistributed**: local capture status is documented; third-party files are not redistributed in the public package unless licensing permits.
3. **Researcher Reviewed**: the source identity, visible date basis, event classification, and citation readiness are checked.
4. **Closed for Use**: the source is approved for descriptive use with the appropriate claim boundary.

Rows that do not clear these gates remain in source-gap or manual-review tables.

## Claim-Boundary Review

Claims are reviewed before public release. The review distinguishes:

- measurement-design claims;
- descriptive source-quality claims;
- reproducibility claims;
- pilot diagnostic findings;
- unsupported causal, policy, market-wide, legal, or investment claims.

Unsupported claims are revised or removed before release.

## Directory Roles

| Directory | Public role |
|---|---|
| `00_admin/` | Governance, rule configuration, and review protocols. |
| `01_raw_sources/` | Public notice that raw third-party source captures are not redistributed. |
| `02_manual_coding/` | Researcher-reviewed coding files, event indexes, and decision records. |
| `03_market_data/` | Derived daily stablecoin market panels. |
| `04_processed_data/` | Merged analysis panel. |
| `05_analysis/` | Reproducible Python scripts and generated model-output folders. |
| `06_outputs/` | Data dictionary, figure data, and exported figures. |

## Release Rule

A public release is ready only when:

- the public release audit passes;
- README integrity checks pass;
- the smoke replication path runs from the public files;
- raw third-party source captures are excluded;
- temporary build files and interpreter caches are absent;
- repository documentation has been manually reviewed.
