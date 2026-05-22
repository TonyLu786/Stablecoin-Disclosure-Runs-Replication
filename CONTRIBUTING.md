# Contributing

Contributions should preserve the repository's evidence boundary.

## Preferred Workflow

1. Open an issue describing the proposed data, code, or documentation change.
2. Identify the affected source rows, scripts, and output files.
3. Rerun the relevant replication stage.
4. Run `python scripts/check_public_release.py`.
5. Document any source-status or claim-boundary changes.

## Coding Standards

- Keep scripts readable and explicit.
- Use stable file paths relative to the repository root.
- Do not add raw third-party PDFs, saved web pages, credentials, local absolute paths, or personal notes.
- Preserve manual review flags when source identity, dates, or coding confidence remain uncertain.
