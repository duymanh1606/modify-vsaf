#!/bin/bash
# Shared credential helper for vds-skill-* skills.
# Sourced by skill scripts to lazy-prompt + persist credentials.
# Config file: ~/.vds/sdlc-config.env (chmod 600)
#
# Portable across bash and zsh (uses eval for indirect expansion).

VSAF_CONFIG_FILE="${VSAF_CONFIG_FILE:-$HOME/.vds/sdlc-config.env}"
readonly VSAF_CONFIG_FILE

# Load existing config if present
if [[ -f "$VSAF_CONFIG_FILE" ]]; then
    # shellcheck source=/dev/null
    source "$VSAF_CONFIG_FILE"
fi

# Also load vds-cli's own env if present (for token reuse)
if [[ -f "$HOME/.vds/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$HOME/.vds/.env"
    set +a
fi

# ensure_env VAR_NAME "Prompt message" [is_secret]
# Prompts user if VAR is empty, persists to config file.
# Re-persists if VAR is pre-set (supports token rotation).
ensure_env() {
    local var="$1"
    local prompt="${2:-Enter $var}"
    local is_secret="${3:-true}"

    # Portable indirect expansion (works in both bash and zsh)
    local value
    eval "value=\${$var:-}"

    if [[ -z "$value" ]]; then
        # Prompt user
        if [[ "$is_secret" == "true" ]]; then
            read -rsp "$prompt: " value
            echo "" >&2
        else
            read -rp "$prompt: " value
        fi

        if [[ -z "$value" ]]; then
            echo "ERROR: $var is required" >&2
            return 1
        fi

        export "$var=$value"
    fi

    # Persist to config file (idempotent — replace existing entry or append)
    mkdir -p "$(dirname "$VSAF_CONFIG_FILE")" || { echo "ERROR: Cannot create config dir $(dirname "$VSAF_CONFIG_FILE")" >&2; return 1; }

    if grep -q "^${var}=" "$VSAF_CONFIG_FILE" 2>/dev/null; then
        # Update in place (BSD/GNU sed compatible via tmp file)
        local tmp
        tmp=$(mktemp) || { echo "ERROR: mktemp failed" >&2; return 1; }
        trap 'rm -f "$tmp"' EXIT INT TERM
        grep -v "^${var}=" "$VSAF_CONFIG_FILE" > "$tmp"
        printf '%s=%q\n' "$var" "$value" >> "$tmp"
        mv "$tmp" "$VSAF_CONFIG_FILE"
        trap - EXIT INT TERM
    else
        printf '%s=%q\n' "$var" "$value" >> "$VSAF_CONFIG_FILE"
    fi
    chmod 600 "$VSAF_CONFIG_FILE" || echo "WARN: Could not set chmod 600 on $VSAF_CONFIG_FILE" >&2
}

# require_command COMMAND_NAME — exits 127 if missing
require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: Required command '$1' not found in PATH" >&2
        echo "       Install it before running this skill." >&2
        return 127
    fi
}
