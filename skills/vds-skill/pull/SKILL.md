---
name: vds-skill-pull
description: Pull latest code via `git pull` then detect stale local knowledge index (`.gitnexus/`, `graphify-out/graph.json`) by comparing mtime with `.git/FETCH_HEAD`. Suggest `/sdlc-onboard-code` if stale. Use instead of bare `git pull` for projects using SDLC pack.
---

# /vds-skill-pull

Wrapper for `git pull` that detects stale local knowledge index after pull and suggests rebuild.

## Usage

```bash
/vds-skill-pull              # equivalent to `git pull`
/vds-skill-pull --rebase     # forwards args to git pull
/vds-skill-pull origin main  # also forwards
```

## Behavior

1. Run `git pull` with all passed args
2. If pull succeeds, check `.gitnexus/` and `graphify-out/graph.json` mtime vs `.git/FETCH_HEAD`
3. If any stale → print suggestion to run `/sdlc-onboard-code`
4. Exit 0 (advisory, does not block workflow)

## Implementation

Invoke the bundled script:

```bash
bash .claude/skills/vds-skill-pull/scripts/pull.sh "$@"
```

## Notes

- Works for both Viettel and non-Viettel projects (no vds-cli dependency).
- If `.gitnexus/` or `graphify-out/` does not exist, that's OK — only flagged if present-but-stale.
- Skill exits 0 even when knowledge is stale (advisory only — user decides whether to onboard now or later).
- `.gitnexus/` staleness uses directory mtime — this catches new files but may miss in-place edits. If GitNexus rewrites files without re-creating them, the check could give a false "fresh" reading. Acceptable for advisory mode.
