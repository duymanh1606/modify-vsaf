## Summary

<!-- What does this PR change and why? -->

## Change type

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring / cleanup
- [ ] Documentation
- [ ] CI / infrastructure

---

## CLI Standards Checklist

> Required for all PRs that touch CLI surfaces (orchestrators, commands, docs, skills).

<!--
If your PR does NOT touch CLI surfaces, write "N/A" below and skip this section.
-->

- [ ] **N/A** (my PR does not touch CLI surfaces)
- [ ] New commands exposed through `vds-cli` router (not direct entry points)
- [ ] `pyproject.toml` does NOT add aliases (`[project.scripts]` has one name per target)
- [ ] Docs/skills show `vds-cli` only (zero direct executable examples)
- [ ] Tests use `CliRunner` and mock externals (no real API calls in tests)
- [ ] Follows `typer.Typer()` pattern (or `make_vds_app()` for new CLIs)
- [ ] `validate-cli-standardization.sh` passes locally
- [ ] `_validate_alias_phase2.py` passes locally

---

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Or: "No behavior changes — existing test coverage sufficient"

## Verification

```bash
# Paste command(s) used to verify this PR
# Example:
# uv run pytest vds_cli/tests/ -q
# bash scripts/validate-cli-standardization.sh
# uv run python scripts/_validate_alias_phase2.py
```
