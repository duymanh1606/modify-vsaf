#!/usr/bin/env bash
# UV-PATTERN: NO-UV — Uses inline python3 for structure validation; no uv invocation.
# Root resolution goes through docs_root.sh shim (safe marker-based).
# No migration needed.
set -euo pipefail

# Validate folder/file structure for target-state docs.
# Checks:
# - architecture/insurance-*/ required docs exist
# - service-specifications/**/ required docs exist
# - each architecture service has a matching service-spec folder

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=WHO-project/vds-scripts/scripts/target-state-automation/docs_root.sh
source "$SCRIPT_DIR/docs_root.sh"

ROOT="$(resolve_repo_root)"
TARGET_STATE_ROOT="$(resolve_insurance_docs_root "$ROOT")/projects/INSURANCE/analysis/target-state"

TARGET_STATE_ROOT="$TARGET_STATE_ROOT" python3 - <<'PY'
from __future__ import annotations

import os
from pathlib import Path

root = Path(os.environ["TARGET_STATE_ROOT"]).resolve()
arch = root / 'architecture'
spec = root / 'service-specifications'

arch_required = [
    'architecture.md',
    'api-contracts.md',
    'integration-patterns.md',
    'database-target-schema.md',
]

# service-spec required (by suffix)
spec_required_suffixes = [
    '_SERVICE_SPEC.md',
    '_API_SPEC.md',
    '_DATA_MODEL.md',
    '_BUSINESS_LOGIC.md',
]

errors: list[str] = []

excluded_arch_svcs = {
    # Known non-service apps/libs (no target-state schema/spec required)
    'insurance-common',
    'insurance-insuremo-common',
    'insurance-customer-webview',
}

arch_svcs = sorted(
    [
        p
        for p in arch.iterdir()
        if p.is_dir() and p.name.startswith('insurance-') and p.name not in excluded_arch_svcs
    ]
)

# Validate architecture per service
for svc_dir in arch_svcs:
    svc = svc_dir.name
    for suf in arch_required:
        fname = f"{svc}-{suf}"
        if not (svc_dir / fname).exists():
            errors.append(f"ARCH missing: {svc}/{fname}")

# Identify service-spec dirs based on *_SERVICE_SPEC.md
spec_service_dirs = sorted({p.parent for p in spec.rglob('*_SERVICE_SPEC.md')}, key=lambda p: str(p))

# Validate service-spec required docs
for d in spec_service_dirs:
    if not (d / 'README.md').exists():
        errors.append(f"SPEC missing: {d.relative_to(spec)}/README.md")
    for suf in spec_required_suffixes:
        if not any(p.name.endswith(suf) for p in d.glob('*.md')):
            errors.append(f"SPEC missing: {d.relative_to(spec)}/*{suf}")

# Ensure each architecture service has matching spec dir (by last path segment match)
spec_paths = [str(p.relative_to(spec)) for p in spec_service_dirs]
for svc_dir in arch_svcs:
    key = svc_dir.name.replace('insurance-', '')
    found = any(s.endswith('/' + key) or s == key for s in spec_paths)
    if not found:
        errors.append(f"SPEC missing for architecture service: {svc_dir.name} (expected folder ending with '{key}')")

if errors:
    print('❌ Structure validation failed')
    for e in errors:
        print('-', e)
    raise SystemExit(1)

print('✅ Structure validation passed')
print(f"Architecture services: {len(arch_svcs)}")
print(f"Service-spec folders: {len(spec_service_dirs)}")
PY
