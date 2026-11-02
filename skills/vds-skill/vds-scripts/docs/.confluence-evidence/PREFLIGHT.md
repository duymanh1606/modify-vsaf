# Docs Confluence Evidence — Pre-flight Checklist

A maintainer walks through this checklist before flipping `ALLOW_EVIDENCE_PUSH=true`
in [`../../.github/workflows/docs-confluence-evidence.yml`](../../.github/workflows/docs-confluence-evidence.yml).
For the runtime description of what the workflow writes, see the sibling
[`README.md`](./README.md).

---

## 1. Why the flag exists

`ALLOW_EVIDENCE_PUSH` is the one-line kill switch between "workflow runs daily
and records evidence as a workflow artifact" (safe, read-only) and "workflow
also commits and pushes the snapshot to the default branch" (mutates history).
It exists because scheduled workflows pushing to a protected default branch is
organization-policy-dependent and the wrong default for a freshly-landed
workflow — we want observable runs before we trust auto-commits.

---

## 2. Organization policy checks

Verify each item before enabling push. Each bullet names the concern plus a
one-liner for how to verify it.

- **Scheduled-workflow push permissions** — org may block `GITHUB_TOKEN` from
  pushing on `schedule` triggers.
  *Verify:* Org Settings → Actions → General → "Workflow permissions" shows
  "Read and write" for the repo, or repo-level override is enabled.
- **Protected-branch rules on default branch** — a branch-protection rule may
  reject direct pushes from the bot identity.
  *Verify:* Repo Settings → Branches → rule for default branch; confirm either
  bypass for `github-actions[bot]` or that "Restrict who can push" excludes it.
- **Required status checks** — required checks on the default branch will
  block the bot's push if the evidence commit is expected to satisfy them.
  *Verify:* Same Branch rule panel; confirm required checks list does not
  include checks that can only run on PRs.
- **Code-owner approvals** — CODEOWNERS-enforced review on `docs/**` would
  require a human approval on every bot commit.
  *Verify:* `grep -R 'docs/\.confluence-evidence' CODEOWNERS .github/CODEOWNERS`
  returns no required-review owners, OR the bot identity is exempted.
- **Signed-commit requirement** — if the branch demands signed commits, native
  `git commit` from the runner will be rejected (the previous third-party
  action did not sign either — see limitations below).
  *Verify:* Branch rule panel → "Require signed commits" is OFF, or wire up a
  commit-signing step before enabling push.

---

## 3. Workflow self-test (push still disabled)

Walk through this with `ALLOW_EVIDENCE_PUSH=false` before flipping it to true.

1. Actions tab → "Docs Confluence Evidence Log" → "Run workflow" → `main`.
2. Wait for the run to finish green. The commit step must be **skipped** (grey),
   not executed.
3. On the run page, confirm the `docs-confluence-evidence-<date>` artifact is
   attached. Download and inspect it — it should contain a single
   `<date>.json` with a `validate` and `quality_score` object.
4. Confirm the workflow **Summary** tab shows validator status, issue count,
   and quality-score average.
5. Only after two or three healthy manual runs: flip `ALLOW_EVIDENCE_PUSH` to
   `'true'` in the workflow `env:` block (or define repo variable
   `ALLOW_EVIDENCE_PUSH=true`).
6. Re-run `workflow_dispatch`. The commit step should now run and produce a
   commit on the default branch. Inspect the commit — it must only touch
   `docs/.confluence-evidence/<date>.json`.

---

## 4. Retention & pruning — TODO

`docs/.confluence-evidence/` grows one JSON per day unbounded once push is
enabled. At ~5-30 KB/file that is manageable for a year, but the directory
will eventually bloat the repo and slow `git clone`.

**TODO (before enabling push for >90 days):** add a pruning workflow.
Suggested filename and shape:

- `.github/workflows/confluence-evidence-prune.yml`
- Schedule: quarterly (`0 4 1 */3 *`) or monthly with a 90-day retention
  window.
- Logic: `find docs/.confluence-evidence -name '*.json' -mtime +90 -delete`
  then commit + push using the same native-git pattern as this workflow.
- Alternative: keep the newest N daily snapshots plus month-end snapshots.

Do not enable push without a pruning plan filed as a follow-up issue.

---

## 5. Rollback

If an enabled push causes issues (bad commits, branch-protection violations,
noisy history):

1. **Disable immediately.** Flip the flag back:
   `env: ALLOW_EVIDENCE_PUSH: 'false'` in
   [`../../.github/workflows/docs-confluence-evidence.yml`](../../.github/workflows/docs-confluence-evidence.yml),
   merge as a hotfix. (Repository-variable override takes effect on the next
   run without a code change.)
2. **Delete offending snapshots.** Single targeted commit:
   `git rm docs/.confluence-evidence/<dates>.json && git commit -m "revert(docs): drop bad evidence snapshots"`.
   Do not rewrite history unless the branch allows it.
3. **Confirm quiet.** Re-run the workflow via `workflow_dispatch` with the
   flag off. The run should upload the artifact and skip the commit step — a
   quiet no-op against the repo.
4. Only re-enable after addressing the root cause and re-walking sections 2–3.

---

## 6. Observability

Where evidence from a healthy run shows up:

- **GitHub Actions run logs** — Actions tab → "Docs Confluence Evidence Log"
  → pick a run. Each step emits `validator status:` / `quality average:`
  lines.
- **Workflow step summary** — "Summary" tab on the run page renders a
  markdown table with validator status, issue count, and quality-score
  average for that date.
- **Workflow artifact** — `docs-confluence-evidence-<date>` artifact is
  retained for 90 days and contains the raw JSON snapshot.
- **Repo files (once push is enabled)** — `docs/.confluence-evidence/<date>.json`
  is a dated snapshot. A healthy snapshot has:
  - `validate.status == "pass"` and `validate.issue_count == 0` (or a small,
    steady-state non-blocking count).
  - `quality_score.average` is a number in the expected band (compare
    against the prior day's file).
  - `generated_at` is within an hour of the 03:00 UTC scheduled trigger.

Cross-reference: sibling [`README.md`](./README.md) describes the snapshot
shape and downstream reviewers' expectations.
