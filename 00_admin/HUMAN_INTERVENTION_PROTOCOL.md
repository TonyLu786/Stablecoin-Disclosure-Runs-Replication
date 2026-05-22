# Researcher Review Protocol

Date: 2026-05-22

This protocol identifies the points at which researcher judgment is required before source records, coding decisions, empirical outputs, or public claims can be treated as release-ready.

## C0. Research Boundary

Researcher confirmation is required for:

- the issuer sample and exclusion rules;
- whether non-fiat-backed or algorithmic stablecoins are background cases or appendix cases;
- the analysis window and market-data coverage;
- the scope of the public replication package.

Acceptance standard:

- sample boundaries are written down before analysis;
- excluded cases have a short rationale;
- claim scope matches the available source and market data.

## C1. Primary Source Review

Researcher confirmation is required for:

- whether issuer pages, reserve reports, attestations, and regulator pages are official sources;
- the difference between report date, coverage date, publication date, and access date;
- whether a source is suitable for descriptive use or exclusion;
- whether raw third-party documents can be redistributed.

Acceptance standard:

- each source row has URL, access date, source status, and event relation;
- low-confidence or missing sources remain in a review queue;
- public releases exclude raw third-party captures unless redistribution is permitted.

## C2. Reserve-Asset Classification

Researcher confirmation is required for:

- cash, Treasury, repo, secured-loan, money-market-fund, and other reserve categories;
- conservative treatment of opaque or residual reserve lines;
- whether a component mismatch should leave RQI missing;
- rule-version changes to RQI/DII definitions.

Acceptance standard:

- low-confidence reserve items have notes;
- frozen rules are recorded in the codebook and configuration file;
- downstream outputs record the active rule version.

## C3. Disclosure-Quality Coding

Researcher confirmation is required for:

- distinctions among audit, assurance, attestation, reserve assertion, and issuer self-reporting;
- scheduled versus ad hoc disclosure status;
- treatment of crisis reassurance statements;
- final event-classification decisions.

Acceptance standard:

- DII components have explicit scoring rules;
- event rows include confidence and review flags;
- coding disputes remain visible until closed.

## C4. Market-Data Treatment

Researcher confirmation is required for:

- preferred price and supply data sources;
- abnormal-price handling;
- de-peg threshold definitions;
- stress-regime calendar choices.

Acceptance standard:

- market-data provenance is recorded;
- abnormal observations are flagged rather than silently dropped;
- robustness outputs report threshold and calendar variants.

## C5. Empirical Specification

Researcher confirmation is required for:

- baseline model families;
- scheduled/ad hoc event separation;
- stress interactions and robustness specifications;
- wording of any causal or policy-adjacent interpretation.

Acceptance standard:

- outputs are described as pilot diagnostics unless stronger identification is documented;
- unsupported causal language is revised or removed;
- tables and figures can be regenerated from scripts.

## C6. Public Release

Researcher confirmation is required for:

- data and code availability wording;
- final README, license, citation, and release manifest;
- exclusion of raw source captures and private notes.

Acceptance standard:

- claims stay inside the audited evidence boundary;
- public documentation reads as a standard scholarly replication package;
- release checks pass before upload or push.
