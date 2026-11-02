# Confluence Evidence Log

Runtime proof that the VDS docs health gates (validator + quality score) are
running outside of PR-time checks. Populated daily by the
[`docs-confluence-evidence.yml`](../../.github/workflows/docs-confluence-evidence.yml)
GitHub Actions workflow.

This is **validation-only evidence** — the workflow does not invoke actual
Confluence sync (sync requires secrets and could mutate pages). The purpose is
to answer the question *"is our docs pipeline healthy today?"* without needing
a human to open a PR.

## Filename convention

```
docs/.confluence-evidence/YYYY-MM-DD.json
```

One snapshot per UTC calendar day. The workflow runs at `03:00 UTC`.

## Snapshot schema

Each file is a JSON object with the following shape:

```json
{
  "generated_at": "2026-04-23T03:00:12+00:00",
  "date": "2026-04-23",
  "workflow": "docs-confluence-evidence",
  "validate": {
    "status": "pass",
    "issue_count": 0,
    "issues": []
  },
  "quality_score": {
    "average": 0.78,
    "docs": {
      "docs/README.md": { "total": 0.82, "...": "..." }
    }
  }
}
```

### How to interpret a snapshot

- `validate.status` — `pass` means the day's run of `vds-cli docs validate`
  with `--check-vi --check-diataxis --check-orchestrators --check-skills`
  returned zero issues. `fail` means issues were detected; the first 50 are
  captured in `validate.issues`.
- `validate.issue_count` — total issues (not capped at 50).
- `quality_score.average` — corpus-wide average doc quality score; the PR gate
  in `docs-quality.yml` enforces `>= 0.6`.
- `quality_score.docs` — per-document scores. Useful for spotting slow drift
  even when the average is still above the threshold.

A `status: error` in `validate` (or `average: null`) means the evidence step
itself failed to run — inspect the workflow logs for that day.

## Retention

**TODO**: add a pruning workflow that deletes snapshots older than 90 days.
For now, snapshots accumulate. Each file is small (< 50 KB) so the immediate
cost is low, but we should not let the directory grow unbounded.

GitHub Actions artifact uploads (see the `Upload evidence artifact` step in
the workflow) already use a 90-day retention; the in-repo copy is the
long-lived audit trail.

## Why the directory is git-tracked but starts empty

The `.gitkeep` file ensures the directory exists before any real evidence has
landed. The commit-back step of the workflow is **disabled by default**
(`ALLOW_EVIDENCE_PUSH=false`) because pushing from scheduled workflows is
org-policy-dependent. Enable it by setting the repository variable
`ALLOW_EVIDENCE_PUSH=true` once the policy is confirmed.

Until commit-back is enabled, daily evidence is still produced — just as a
workflow artifact instead of a committed file.

## See also

- Workflow: [`.github/workflows/docs-confluence-evidence.yml`](../../.github/workflows/docs-confluence-evidence.yml)
- PR-time gate: [`.github/workflows/docs-quality.yml`](../../.github/workflows/docs-quality.yml)
- Spec gap: `.gpt-5.4/specs/ARCHIVE/who-project-documentation-enhancement/tasks.md` (Gap 3 — Confluence auto-sync runtime proof)
