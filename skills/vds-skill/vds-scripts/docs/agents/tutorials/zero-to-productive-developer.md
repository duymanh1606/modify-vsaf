<!-- diátaxis: tutorial -->
# Zero To Productive Developer

A week-long guided walkthrough for new human contributors joining the VDS WHO ecosystem. By the end of Day 7 you will build, validate, and land a real docs or runbook patch in a dedicated worktree with `vds-cli` and `vds-spec` gates passing.

## Prerequisites

- Git, `uv` (latest), and a supported shell (zsh or bash)
- Editor with Markdown support (VS Code, Vim, etc.)
- Basic Python familiarity (reading CLI output, editing `.env` files)

---

## Day 0 — Get the monorepo

### 1.1 Ensure you can access VDS code surfaces

The VDS monorepo lives at the workspace root. If you already have the folder, open a terminal inside the root directory:

```bash
cd "/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds"
ls WHO-project/
```

You should see directories such as `vds-scripts`, `vds-skills`, and `worktrees`.

### 1.2 Set up your shell helper environment

```bash
# Add to ~/.zshrc or ~/.bashrc (once)
export PATH="${PATH}:$(pwd)/WHO-project/vds-scripts/scripts"
```

Close and reopen your terminal so the new PATH is active. You do not need to install anything else today.

### 1.3 Verify the entry points exist

```bash
ls WHO-project/vds-scripts/vds_cli/
ls WHO-project/vds-scripts/scripts/worktree_uv.sh
```

### 1.4 Signpost

- This is a **tutorial**, not a reference. Exact configurations change; always read the current `AGENTS.md` if you are unsure.
- Every numbered step is designed to be run in sequence. Do not skip ahead until the step passes for you.

---

## Day 1 — Run your first CLI command

### 2.1 Open a worktree-safe shell

All WHO workspace commands are run through `uv`. Inside the `vds-scripts` directory you should avoid bare `python` or `pip`. The worktree-safe wrapper path is:

```bash
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh --help
```

If the help banner prints, your environment is aligned.

### 2.2 Ask for directions

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli --help
```

Read the top-level command list. Notice that actions are grouped: `audit`, `spec`, `memory`, `progress`, `confluence`, `bitbucket`.

### 2.3 Check environment health

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status
```

This prints:
- Which `VDS_ENV_FILE` is being loaded
- Current `VDS_SCRIPTS_PATH`
- Quick observability of whether the CLI can reach its own workspace

### 2.4 Read the baseline rules

Open `WHO-project/vds-scripts/AGENTS.md` in your editor. Focus on these sections:
- Path and search rules (quoting paths, iCloud space escaping)
- Entry points (run an example command)
- Testing rules (mock externals)

**Checkpoint**: Before moving to Day 2, verify that you can run `vds-cli --help` and `env status` without import or path errors.

---

## Day 2 — Understand the Diátaxis docs layout

### 3.1 Tour existing docs

```bash
find docs/agents -type f -name "*.md" | sort
```

Notice the four directories:
- `tutorials/` — step-by-step learning
- `how-to/` — goal-oriented recipes
- `reference/` — fact-oriented lookup
- `explanation/` — understanding-oriented deep dives

### 3.2 Pick one doc from each quadrant and read it

Suggested set:
- Tutorial: `docs/agents/tutorials/who-skills-and-scripts-onboarding.md`
- How-to: `docs/agents/how-to/install-and-bootstrap-who-scripts-and-skills.md`
- Reference: `docs/agents/reference/cli-commands.md`
- Explanation: `docs/agents/explanation/who-ecosystem-model.md`

### 3.3 Practice identifying the quadrant of a file

Before a doc is machine-readable, it must declare its quadrant. The doc header is a single HTML comment:

```markdown
<!-- diátaxis: tutorial -->
```

Valid values: `tutorial`, `how-to`, `reference`, `explanation`.

**Checkpoint**: You can look at any `.md` file under `docs/agents/` and state which quadrant it belongs to.

---

## Day 3 — Edit a doc and validate locally

### 4.1 Make a targetable change

Pick a small improvement to a how-to guide, for example:
- Add a clarifying sentence to `docs/agents/how-to/first-audit-run.md`
- Fix a broken relative link in `docs/agents/reference/search-tools.md`

### 4.2 Run the docs validator

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli docs validate
```

This checks:
- All `.md` files under `docs/` are linked from `llms.txt` (no orphans)
- Required headings exist in known doc types
- Freshness tracking metadata is present when expected

### 4.3 Fix any validation feedback

If the validator reports orphans, add the missing file path to `llms.txt` under the `## Docs Index` section.

### 4.4 Stage, commit, and push to a branch in your own fork or worktree

```bash
git checkout -b feat/docs-day3-example
git add docs/agents/ llms.txt
git commit -m "docs: clarify first-audit-run prerequisites"
```

**Checkpoint**: `vds-cli docs validate` reports 0 errors and 0 orphans before you push.

---

## Day 4 — Run an audit command end-to-end

### 5.1 Choose a safe lane

Do not run on production audit targets yet. Choose a command that only reads:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli audit doctor --help
```

### 5.2 Run the doctor command against the workspace itself

The `doctor` subcommand inspects the current workspace without mutating state:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli audit doctor profiles
```

This lists the known profiles and their availability. It will print a short table.

### 5.3 Read the audit triage playbook

Open `docs/agents/reference/audit-triage-playbook.md`. This is a reference doc. Read through the "Run Preparation Checks" section. It maps exactly onto what you just ran.

### 5.4 Try a spec command

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli spec --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli spec validate
```

If validation passes, your workspace spec is aligned with the canonical triplet.

**Checkpoint**: You can run `vds-cli audit doctor profiles` and `vds-cli spec validate` with clean output and understand what each command is for.

---

## Day 5 — Write a how-to guide

### 6.1 Pick a micro-workflow you completed this week

Examples:
- "How to add a new doc and prevent orphan warnings"
- "How to switch from mainline to a dedicated worktree safely"
- "How to read a skill file without OpenSkills installed"

### 6.2 Use the how-to template

A how-to guide:
- Has a clear goal in the title
- Assumes prerequisites (Day 0–4 material)
- Uses numbered steps
- Uses code blocks for exact commands
- Ends with a "Related" section linking to tutorials and reference

Place the new file under `docs/agents/how-to/` and add its link to `llms.txt`.

### 6.3 Run the validator

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli docs validate
```

### 6.4 Open a draft PR or request review from a team member

Keep the change small (under 80 lines if possible). Small changes are faster to review and merge.

**Checkpoint**: Your new how-to is under 100 lines, linked from `llms.txt`, and passes the validator.

---

## Day 6 — Explore a skill and write a test plan

### 7.1 Load a skill

Choose a skill you expect to use often, for example `audit-orchestrator-skill`.

```bash
cat "WHO-project/vds-skills/skills/audit-orchestrator-skill/SKILL.md"
```

Read the canonical file directly:

```bash
cat "WHO-project/vds-skills/skills/audit-orchestrator-skill/SKILL.md"
```

### 7.2 Read the skill's `SKILL.md` up to the workflow section

Skills typically contain:
1. Title and description
2. When to use the skill
3. Workflow steps
4. References

### 7.3 Write a short test plan for the skill workflow

In a scratch file or local note, write:
- What commands the skill recommends
- Which of those commands you can safely run in a test context
- What output you will look for to confirm success

### 7.4 Sketch the test as a dry-run

For example, if the skill says to run `vds-cli audit dispatch --profile default-all --dry-run`, write that step into your test plan and execute it:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli audit dispatch --profile default-all --dry-run
```

Read the output and reflect: did it match the skill's stated expectations?

**Checkpoint**: You can read a skill, map it to three concrete commands, and confirm at least one of them runs safely in your workspace.

---

## Day 7 — Land a patch with spec alignment

### 8.1 Pick the final patch

Choose a real improvement, for example:
- Correct an outdated command in an existing doc
- Add a new `how-to` guide
- Update the `llms.txt` index to include a missing file

### 8.2 Write the change in a dedicated worktree branch

```bash
cd WHO-project/vds-scripts
git checkout -b feat/docs-day7-final
git add ...
git commit -m "docs(agents): add how-to for X" -m "- Problem: ..." -m "- Solution: ..."
```

### 8.3 Run spec alignment

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli spec validate
```

### 8.4 Run the docs validator

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli docs validate
```

### 8.5 Push and open a merge request

```bash
git push -u origin feat/docs-day7-final
```

Include:
- What changed
- Which files it touched
- Validator output (0 errors)

### 8.6 Prepare for next week

After the merge:
1. Return to `master`/`main`
2. Pull the latest changes
3. Delete your local feature branch if the merge succeeded
4. Read the next-wave spec in `.gpt-5.4/specs/`

**Checkpoint**: You have at least one merged patch that started from the docs and passed both spec and doc validation gates.

---

## Recurring reminders

- Quote all paths that contain spaces (`cd "..."`).
- Use `./scripts/worktree_uv.sh` when in a dedicated worktree.
- Never put secrets in `.md` files, use `~/.vds/.env` instead.
- Every new doc must: declare its Diátaxis quadrant, link from `llms.txt`, and pass `vds-cli docs validate`.
- Prefer small changes over large ones. Each day above is designed to take under sixty minutes.
