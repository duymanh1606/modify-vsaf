<!-- diátaxis: tutorial -->

<!-- TODO: translate — Vietnamese translation pending -->

# WHO Skills And Scripts Onboarding

This tutorial gives new human contributors and AI agents a fast orientation to the current WHO ecosystem.

## 1. Understand the canonical model

`WHO-project` is the authoritative home for:
- reusable skills in `WHO-project/vds-skills/skills/`
- routed scripts and orchestrators in `WHO-project/vds-scripts/`

## 2. Know the two main entry styles

- use `vds-scripts-skill` to route platform tasks and command-family selection
- use specialist skills for deep workflow guidance

## 3. Install and bootstrap first

Before deeper task routing, follow `../how-to/install-and-bootstrap-who-scripts-and-skills.md` so both the scripts workspace and the skills catalog are verifiably ready.

## 4. Start with these commands

If you are inside a dedicated `vds-scripts` worktree, prefer the worktree-safe wrapper:

- `./scripts/worktree_uv.sh run --project vds_cli vds-cli --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli env status`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli spec --help`

## 5. Edit only canonical sources

- edit skills under `WHO-project/vds-skills/skills/`
- keep `.agent/skills/` as mirror/symlink-only
- sync generated agent surfaces from the monorepo root after skill changes

## 6. Learn the routing model

If the task is broad and platform-oriented, start with `vds-scripts-skill`.
If the task is specialist or phase-sensitive, route to the appropriate specialist skill.
