---
name: CLI Change
description: Request a change to the vds-cli surface (commands, orchestrators, or documentation)
title: "[service] "
labels: ["cli", "standardization"]
assignees: []
body:
  - type: markdown
    attributes:
      value: |
        Use this template when proposing changes to the vds-cli command surface,
        adding new orchestrators, fixing CLI bugs, or updating CLI documentation.

  - type: input
    id: service-name
    attributes:
      label: Service name
      description: Which orchestrator service is affected? (e.g. audit, memory, research)
      placeholder: e.g. memory
    validations:
      required: true

  - type: dropdown
    id: command-type
    attributes:
      label: Command type
      description: What kind of CLI change is this?
      options:
        - New subcommand
        - New orchestrator
        - Bug fix
        - Documentation
        - Breaking change
    validations:
      required: true

  - type: checkboxes
    id: routing-confirmation
    attributes:
      label: Routing confirmation
      description: Confirm the command is exposed through the unified CLI router.
      options:
        - label: CLI commands are exposed through `vds-cli <service>` (not direct entry points)
          required: true

  - type: checkboxes
    id: alias-check
    attributes:
      label: Alias check
      description: Confirm no direct executables or aliases are added outside the router.
      options:
        - label: No new direct executables or aliases added to pyproject.toml `[project.scripts]`
          required: true

  - type: textarea
    id: test-coverage
    attributes:
      label: Test coverage
      description: Describe tests added (CliRunner, mocked externals); link to test files.
      placeholder: |
        - Added `test_memory_search.py` with `CliRunner` and mocked Postgres
        - Link: `vds_cli/tests/memory/test_memory_search.py`
    validations:
      required: false

  - type: checkboxes
    id: standards-review
    attributes:
      label: Standards review
      description: Confirm compliance with the CLI development standards.
      options:
        - label: Verified against `vds-scripts/docs/agents/reference/cli-development-standards.md`
          required: true

  - type: textarea
    id: breaking-changes
    attributes:
      label: Breaking changes
      description: Any changes to command signatures or JSON output shapes?
      placeholder: |
        - `--output` flag renamed to `--format`
        - JSON shape of `vds-cli audit list` changed from `{...}` to `[...]`
    validations:
      required: false

  - type: textarea
    id: additional-context
    attributes:
      label: Additional context
      description: Anything else reviewers should know.
    validations:
      required: false
