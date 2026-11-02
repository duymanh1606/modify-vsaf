# BRD Coverage Orchestrator

Validates Business Requirements Document (BRD) coverage across VDS Insurance documentation.

## Usage

```bash
# Default validation (writes report to scripts/brd_coverage_report.json)
./scripts/worktree_uv.sh run --project vds_cli vds-cli brd -- validate

# Custom docs root + report path
./scripts/worktree_uv.sh run --project vds_cli vds-cli brd -- validate \
  --root WHO-project/insurance-document \
  --report /tmp/brd_coverage_report.json \
  --min-coverage 100
```

## Output

The report includes:
- coverage percentage and missing sections
- covered sections
- file-level BRD references
- high-priority service mappings

## Notes

- Default docs root prefers `VDS_INSURANCE_DOCS_ROOT`, then `WHO-project/insurance-document`, then the first `*-project/insurance-document` match.
- Report path defaults to `WHO-project/vds-scripts/scripts/brd_coverage_report.json`.
