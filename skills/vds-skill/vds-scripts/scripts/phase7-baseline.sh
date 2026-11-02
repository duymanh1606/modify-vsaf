#!/usr/bin/env bash
# Phase 7 pre-flight: lock baselines for LOC reduction acceptance.
# Run from WHO-project/vds-scripts/ (or its worktree).
set -euo pipefail

echo "=== Phase 7 Baseline (commit: $(git rev-parse --short HEAD)) ==="
echo "## Client LOC"
for f in sonarqube_orchestrator/src/vds_sonarqube_orchestrator/client.py \
         elastic_orchestrator/src/vds_elastic_orchestrator/client.py \
         grafana_orchestrator/src/vds_grafana_orchestrator/client.py \
         bitbucket_orchestrator/src/vds_bitbucket_orchestrator/async_client.py \
         confluence_orchestrator/src/confluence_orchestrator/http.py \
         jira_orchestrator/src/vds_jira_orchestrator/adapter.py; do
  printf "%6d  %s\n" "$(wc -l < "$f")" "$f"
done

echo ""
echo "## SecretStr unwrap sites (mainline src only)"
rg "get_secret_value\(\)" --glob '*.py' --glob '!worktrees/**' --glob '!tests/**' \
   --glob '**/src/**' -c | sort

echo ""
echo "## Retry patterns per client"
for pkg in sonarqube_orchestrator elastic_orchestrator grafana_orchestrator \
           bitbucket_orchestrator confluence_orchestrator; do
  count=$(rg "tenacity|@retry|wait_exponential|stop_after_attempt|record_retry_event" \
              "$pkg/src/" --glob '*.py' 2>/dev/null | wc -l | tr -d ' ')
  echo "  $pkg: $count"
done

echo ""
echo "## Test counts per client"
for pkg in sonarqube_orchestrator elastic_orchestrator grafana_orchestrator \
           bitbucket_orchestrator confluence_orchestrator jira_orchestrator \
           audit_orchestrator platform_core; do
  count=$(./scripts/worktree_uv.sh run --project "$pkg" pytest --collect-only -q 2>/dev/null \
            | grep -c "::test_" || true)
  echo "  $pkg: $count"
done

echo ""
echo "## SDK-adoption gap baselines (Phase 7 v24.0.0; per ADR-T7.16)"
echo "# These counts must drop to the targets specified in FR-7.12-7.19 by Wave 5."

# 1. Bespoke SettingsError classes (target: 0; FR-7.12)
echo "## (1) bespoke 'class SettingsError(RuntimeError)' definitions"
rg "^class SettingsError\(RuntimeError\)" --glob '*_orchestrator/src/**/*.py' -c | sort

# 2. Bespoke settings_customise_sources overrides (target: 0; FR-7.12)
echo "## (2) bespoke 'def settings_customise_sources' overrides"
rg "def settings_customise_sources" --glob '*_orchestrator/src/**/*.py' -c | sort

# 3. SettingsConfigDict literal usage (target: 0 outside platform_core; FR-7.12)
echo "## (3) 'SettingsConfigDict(env_file_encoding' literals (should consolidate to VDS_BASE_SETTINGS_CONFIG)"
rg "SettingsConfigDict\(env_file_encoding" --glob '*_orchestrator/src/**/*.py' -c | sort

# 4. connect_timeout/read_timeout/etc inline in service Settings (target: 0; FR-7.13)
echo "## (4) inline connect_timeout/read_timeout/max_retries fields in service Settings (should use HTTPClientSettings mixin)"
rg "^\s*(connect_timeout|read_timeout|max_retries|retry_backoff_initial|retry_backoff_multiplier|retry_max_wait)\s*:\s*" \
   --glob '*_orchestrator/src/**/config.py' -c | sort

# 5. @dataclass *CLIContext + module-level _state (target: 0; FR-7.14)
echo "## (5) bespoke '@dataclass \\w+CLIContext' + module-global _state patterns"
rg "@dataclass\s*\nclass \w+CLIContext" --multiline --glob '*_orchestrator/src/**/cli.py' -c | sort
rg "^_state\s*[:=]" --glob '*_orchestrator/src/**/cli.py' -c | sort

# 6. Bespoke _output_json / _output_error helpers (target: 0; FR-7.15)
echo "## (6) bespoke '_output_json' and '_output_error' helpers in cli.py (should use OutputManager)"
rg "^def _output_(json|error)\b" --glob '*_orchestrator/src/**/cli.py' -c | sort

# 7. Ad-hoc structlog.configure(...) call sites (target: 0; FR-7.16)
echo "## (7) ad-hoc 'structlog.configure(' calls in service trees (should use configure_structlog())"
rg "structlog\.configure\(" --glob '*_orchestrator/src/**/*.py' -c | sort

# 8. settings.model_dump() at diagnostic call sites (target: 0; FR-7.17)
echo "## (8) raw 'settings.model_dump()' calls in service trees (should use safe_dump / SafeDumpMixin)"
rg "settings\.model_dump\(" --glob '*_orchestrator/src/**/*.py' -c | sort
