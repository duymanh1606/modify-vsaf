# VDS Evolution Loop: Auto-Run Rollout Guide

> **Canonical Spec:** [.gpt-5.4/specs/who-ecosystem-evolution-loop/SPEC.md](../.gpt-5.4/specs/who-ecosystem-evolution-loop/SPEC.md)

## Overview

This guide covers deploying the VDS Evolution Loop as an auto-running daemon that monitors for pending verdicts and automatically promotes eligible skills.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Auto-Run System                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │ launchd     │    │ systemd     │    │ cron        │             │
│  │ (macOS)     │    │ (Linux)     │    │ (fallback)  │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                   │                   │                    │
│         ▼                   ▼                   ▼                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              evolution-auto-run.sh                             │  │
│  │   - Validates OPENSPACE_AUTONOMOUS_ENABLED=true               │  │
│  │   - Sets up environment variables                             │  │
│  │   - Runs vds-cli evolution auto-promote daemon                   │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              vds-cli evolution auto-promote                       │  │
│  │   - Polls for pending verdicts                               │  │
│  │   - Signs with HMAC                                          │  │
│  │   - Verifies signature                                       │  │
│  │   - Promotes eligible verdicts                               │  │
│  │   - Marks as processed                                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              promote.py (Git Workflow)                       │  │
│  │   - Creates evolution-promote/{skill}-{timestamp} branch    │  │
│  │   - Cherry-picks skill changes                              │  │
│  │   - Opens PR or merges directly                              │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Environment Variables

```bash
# Required for auto-run
OPENSPACE_AUTONOMOUS_ENABLED=true
OPENSPACE_WORKSPACE=/path/to/vds-scripts
OPENSPACE_HOST_SKILL_DIRS=/path/to/vds-skills/skills
OPENSPACE_TRANSPORT=stdio

# Optional for Gate 3
ANTHROPIC_API_KEY=sk-ant-...
```

### Kill Switch

The system respects the kill switch. If `OPENSPACE_AUTONOMOUS_ENABLED != true`, the daemon will not make any changes:

```python
# From switch.py
def is_enabled(self) -> bool:
    value = os.environ.get("OPENSPACE_AUTONOMOUS_ENABLED", "false").lower()
    return value in ("true", "1", "yes")
```

## Deployment Options

### Option 1: macOS launchd (Recommended for macOS)

```bash
# Install
./scripts/install-evolution-auto.sh

# Status
launchctl list com.vds-ai.vds-cli evolution-auto

# Logs
tail -f ~/.evolution-log/daemon.log

# Stop
./scripts/install-evolution-auto.sh --uninstall

# Manual start/stop
launchctl start com.vds-ai.vds-cli evolution-auto
launchctl stop com.vds-ai.vds-cli evolution-auto
```

### Option 2: systemd (Linux)

```bash
# Install
sudo cp vds-cli evolution-auto.service /etc/systemd/system/
sudo cp vds-cli evolution-auto.timer /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable vds-cli evolution-auto
sudo systemctl start vds-cli evolution-auto

# Status
sudo systemctl status vds-cli evolution-auto

# View logs
journalctl -u vds-cli evolution-auto -f
```

### Option 3: cron (Fallback)

```bash
# Install crontab
crontab -e
# Paste contents from crontab-evolution-auto.txt

# View
crontab -l
```

### Option 4: Manual

```bash
# Direct invocation
OPENSPACE_AUTONOMOUS_ENABLED=true ./scripts/evolution-auto-run.sh

# With options
./scripts/evolution-auto-run.sh --poll-interval 30 --dry-run
```

## Configuration

### AutoPromoteConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `poll_interval` | 60.0 | Seconds between polling cycles |
| `dry_run` | false | If true, only logs actions without promoting |
| `verdict_root` | auto | Verdict file directory |
| `max_failures` | 3 | Consecutive failures before backoff |
| `backoff_multiplier` | 2.0 | Multiplier for exponential backoff |
| `max_backoff` | 600.0 | Maximum backoff in seconds (10 min) |

### Environment Variables

```bash
# Poll every 30 seconds
export POLL_INTERVAL=30

# Use specific log file
export LOG_FILE=/path/to/log

# Dry-run mode (safe for testing)
./scripts/evolution-auto-run.sh --dry-run
```

## Monitoring

### Status Check

```bash
# CLI status
vds-cli evolution status

# Show pending verdicts
vds-cli evolution list --filter pending
```

### Logs

```
.evolution-log/
├── daemon.log          # Daemon output
├── daemon-error.log    # Error output
└── verdicts/           # Individual verdict files
    ├── verdict-xxx-001.json
    ├── verdict-xxx-002.json
    └── ...
```

### Health Checks

```bash
# OpenSpace doctor
vds-cli evolution openspace-doctor

# Queue depth
vds-cli evolution status | grep "Queue"

# Recent verdicts
vds-cli evolution list | head -20
```

## Troubleshooting

### Daemon not starting

```bash
# Check environment
echo $OPENSPACE_AUTONOMOUS_ENABLED
echo $OPENSPACE_WORKSPACE

# Check service status
launchctl list | grep vds-cli evolution

# View error logs
cat .evolution-log/daemon-error.log
```

### No verdicts being found

```bash
# Check verdict directory
ls -la ~/.evolution-log/verdicts/

# Check OpenSpace store
vds-cli evolution openspace-doctor

# Manually run route
vds-cli evolution route path/to/SKILL.md
```

### Promotion failures

```bash
# Check git status
git status

# Dry-run to see what would happen
./scripts/evolution-auto-run.sh --dry-run

# View promotion logs
grep -i promote .evolution-log/daemon.log
```

### Backoff triggered

The daemon implements exponential backoff on consecutive failures:

```
Failure 1: Sleep 60s (1x poll_interval)
Failure 2: Sleep 120s (2x)
Failure 3: Sleep 240s (4x)
... max 600s (10x)
```

After max failures, the daemon continues with max backoff but logs warnings.

## Security

### HMAC Verification

Before any promotion, the system verifies the HMAC signature:

```python
def _verify_before_promote(self, verdict_path: Path) -> bool:
    signed = json.loads(verdict_path.read_text())
    verified = verify_and_detach(signed)
    return verified.valid
```

### No Direct Writes

The system never writes to skill directories directly. All changes go through:
1. Git branch creation
2. Cherry-pick
3. PR/merge workflow

### Audit Trail

All promotions are logged:
- Verdict JSON with HMAC signature
- Daemon log with timestamps
- Git history with branch names

## Rollout Checklist

- [ ] Environment variables configured
- [ ] Kill switch state verified (`vds-cli evolution status`)
- [ ] OpenSpace store accessible (`vds-cli evolution openspace-doctor`)
- [ ] Test dry-run mode (`./scripts/evolution-auto-run.sh --dry-run`)
- [ ] Install service (launchd/systemd/cron)
- [ ] Verify service running
- [ ] Monitor logs for first 24 hours
- [ ] Set up alerts for promotion failures

## Emergency Shutdown

```bash
# Stop all promotions
export OPENSPACE_AUTONOMOUS_ENABLED=false

# Or uninstall service
./scripts/install-evolution-auto.sh --uninstall

# Or kill daemon
pkill -f "vds-cli evolution auto-promote"
```

## Performance

### Resource Usage

- **CPU**: Minimal (sleeps between polls)
- **Memory**: ~50MB for daemon + Python runtime
- **Disk**: Log rotation recommended
- **Network**: Only if OpenSpace MCP is remote

### Scaling

For multiple workspaces:
```bash
# Workspace 1
OPENSPACE_WORKSPACE=/path/to/workspace1 ./scripts/evolution-auto-run.sh &

# Workspace 2
OPENSPACE_WORKSPACE=/path/to/workspace2 ./scripts/evolution-auto-run.sh &
```
