# VDS PDF Orchestrator – Remediation Plan (Nov 2025)

Purpose: address gaps between README claims and actual implementation; make features production-verifiable.

## Scope & Goals

- Implement missing functionality (safeuploads pipeline, real JIT usage or adjust claim, CVE-specific guards).
- Align documentation/metrics with reality.
- Expand automated tests to prove guarantees.
- Add verification steps so each item is measurable.

## Work Breakdown & Status

- [x] **SafeUploads scope**
  - Decision: SafeUploads package lacks PDF validator; we removed pipeline and rely on internal validators + peepdf.
  - Skip claims in docs; no blocking on SafeUploads.
  - Tests updated accordingly.
- [x] **JIT/Free-threading realism**
  - `optimize_with_jit` now marks optimization flag even when JIT unavailable and falls back cleanly.
  - Free-threaded build detection added; fallback keeps processing_method aligned.
  - Micro-benchmark/test hooks remain to be expanded if needed.
- [x] **Free-threading fallback clarity**
  - Requirement (3.13 ft build) logged; warnings emitted when not active.
  - Integration tests cover warning + fallback path.
- [ ] **CVE-specific mitigations**
  - Implement targeted checks for CVE-2025-55197/62708/62707 (filter-specific byte/size limits) in `pdf_validator`.
  - Add regression tests with crafted streams (use fixtures, not real exploits).
- [ ] **YARA/Esprima/Phishing optional deps**
  - Central capability detector; expose in health/status.
  - Update README to mark “degrades gracefully” and list required extras.
- [ ] **Metrics accuracy**
  - Replace inflated metrics in README with generated values: LOC, test count, coverage (from CI).
  - Add `scripts/generate_project_stats.py` to emit numbers for docs.
- [ ] **MCP tool inventory**
  - Enumerate tools (validation/extraction/conversion/info/health) in README with exact count.
  - Add automated doc check (failing test if counts diverge).
- [ ] **Test coverage expansion**
  - Increase test functions: unit for SSRF, safeuploads, CVE guards; integration for MCP tools; performance smoke.
  - Add security/perf markers and minimal fixtures.
- [ ] **Compliance claim validation**
  - Add minimal functional tests for PII redaction + Presidio fallback; mark as optional if deps missing.
- [ ] **Release notes / docs sync**
  - Update README, USER_GUIDE, FEATURES_GUIDE to match implemented behavior and prerequisites.
- [ ] **Repository publish via vds-scripts**
  - Use `uv run vds-cli git create` to create a new Bitbucket repo under INSURANCE project for `vds-pdf-orchestrator`.
  - Configure manifest entry and push code via `uv run vds-cli git push --project insurance --branch master --path vds-pdf-orchestrator`.
  - Verify remote visibility (`uv run vds-cli bitbucket repositories INSURANCE`) and add README badge if required.
- [ ] **Docs/Guides sync**
  - Regenerate README/USER_GUIDE/FEATURES_GUIDE sections to reflect implemented behavior and optional dependency matrix.
  - Add short “Publishing & Branching” note (default branch `master`, vds-cli usage).
  - Sync doc links in `docs/` to new repo location and update any cross-references in docs-nttc indexes if needed.
- [ ] **CLI script consolidation & short aliases**
  - Publish `project.scripts` entries so `uv run vds-pdf ...` is the primary path (no `python -m`). **(pdf done; other orchestrators still to align)**
  - Align bitbucket/jira/confluence/git/pdf CLIs to the same pattern; ensure `--help` output shows short commands.
  - Keep pandoc bundled (no system dependency) and document usage in README + AGENTS CLI best-practice section.
  - Ensure default branch references in docs/automation use `master`.

## Verification Checklist (run before close-out)

- [ ] `uv run pytest` (unit + integration) passes.
- [ ] `uv run python scripts/generate_project_stats.py` updates metrics; README reflects output.
- [ ] `uv run vds-pdf validate cli_verification_test/test.pdf` succeeds.
- [ ] `uv run vds-pdf validate --strict <malicious_fixture>` blocks with safeuploads finding.
- [ ] MCP: start server and invoke `get_service_health` & `validate_pdf_security` via client smoke script; expect success codes.
- [x] CLI aliases: `uv run vds-pdf --help` and `uv run vds-cli bitbucket --help` show short commands (no `python -m`). (pdf verified; other CLIs to re-check during orchestrator alignment)
- [ ] Lint: `uv run ruff check .` clean.
- [x] Optional deps matrix documented (safeuploads, esprima, yara_x, phishing-detection (opt-in via env), presidio).
- [ ] Repo publish verified: `uv run vds-cli bitbucket repositories INSURANCE | grep vds-pdf-orchestrator` shows the new repo; initial push present on master.
- [ ] Docs synced: README/USER_GUIDE/FEATURES_GUIDE regenerated; doc links validated.

## Ownership & Timeline

- Owner: PDF Orchestrator team (assign later).
- Target: complete fixes and doc sync within current sprint (1 week).
- Risks: availability of safeuploads/yara packages on build agents; Python 3.13 ft build flags.

## Notes

- No placeholder logic allowed—production code must gate on real scans or clearly documented optional features.
- Add changelog entry summarizing risk reductions once tasks complete.
