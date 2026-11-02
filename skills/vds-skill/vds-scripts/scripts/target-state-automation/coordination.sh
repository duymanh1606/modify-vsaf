#!/usr/bin/env bash
# UV-PATTERN: NO-UV — This script uses only curl and inline python3 to call
# the multi-agent coordination HTTP API.  It has no uv dependency and does not
# need to be migrated to the worktree wrapper pattern.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SESSION_ID="${SESSION_ID:-multi_agent_session_$(date +%Y%m%d)}"
USER_ID="${USER_ID:-multi_agent_coordinator}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <command> [args]"
  echo "Commands:"
  echo "  init-tasks <tasks.json>"
  echo "  register <agent_id> <capabilities_csv>"
  echo "  heartbeat <agent_id>"
  echo "  acquire <agent_id>"
  echo "  progress <agent_id> <task_id> <progress>"
  echo "  complete <agent_id> <task_id> <result_json>"
  echo "  list-tasks"
  echo "  list-agents"
  echo "  lock <agent_id> <file_path> <operation>"
  echo "  unlock <agent_id> <file_path>"
  exit 1
fi

cmd="$1"
shift

case "$cmd" in
  init-tasks)
    tasks_file="$1"
    curl -sS -X POST "$BASE_URL/api/v1/coordination/tasks/initialize" \
      -H "Content-Type: application/json" \
      -d @"$tasks_file"
    ;;
  register)
    agent_id="$1"
    capabilities_csv="$2"
    IFS=',' read -r -a caps <<< "$capabilities_csv"
    payload=$(python3 - <<'PY'
import json, os
agent_id = os.environ["AGENT_ID"]
caps = os.environ["CAPS"].split(",") if os.environ["CAPS"] else []
payload = {
  "session_id": os.environ["SESSION_ID"],
  "user_id": os.environ["USER_ID"],
  "agent_id": agent_id,
  "capabilities": [c.strip() for c in caps if c.strip()],
  "max_concurrent_tasks": 1,
  "metadata": {"org_id": "vds-internal"},
}
print(json.dumps(payload))
PY
)
    AGENT_ID="$agent_id" CAPS="$capabilities_csv" SESSION_ID="$SESSION_ID" USER_ID="$USER_ID" \
      curl -sS -X POST "$BASE_URL/api/v1/coordination/agents/register" \
        -H "Content-Type: application/json" \
        -d "$payload"
    ;;
  heartbeat)
    agent_id="$1"
    curl -sS -X POST "$BASE_URL/api/v1/coordination/agents/heartbeat" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\":\"$SESSION_ID\",\"agent_id\":\"$agent_id\"}"
    ;;
  acquire)
    agent_id="$1"
    curl -sS -X POST "$BASE_URL/api/v1/coordination/tasks/acquire" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\":\"$SESSION_ID\",\"user_id\":\"$USER_ID\",\"agent_id\":\"$agent_id\"}"
    ;;
  progress)
    agent_id="$1"
    task_id="$2"
    progress="$3"
    curl -sS -X POST "$BASE_URL/api/v1/coordination/tasks/progress" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\":\"$SESSION_ID\",\"user_id\":\"$USER_ID\",\"task_id\":\"$task_id\",\"agent_id\":\"$agent_id\",\"progress\":$progress}"
    ;;
  complete)
    agent_id="$1"
    task_id="$2"
    result_json="$3"
    curl -sS -X POST "$BASE_URL/api/v1/coordination/tasks/complete" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\":\"$SESSION_ID\",\"user_id\":\"$USER_ID\",\"task_id\":\"$task_id\",\"agent_id\":\"$agent_id\",\"result\":$result_json}"
    ;;
  list-tasks)
    curl -sS "$BASE_URL/api/v1/coordination/tasks?session_id=$SESSION_ID"
    ;;
  list-agents)
    curl -sS "$BASE_URL/api/v1/coordination/agents?session_id=$SESSION_ID"
    ;;
  lock)
    agent_id="$1"
    file_path="$2"
    operation="$3"
    curl -sS -X POST "$BASE_URL/api/v1/coordination/locks/acquire" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\":\"$SESSION_ID\",\"user_id\":\"$USER_ID\",\"file_path\":\"$file_path\",\"agent_id\":\"$agent_id\",\"operation\":\"$operation\"}"
    ;;
  unlock)
    agent_id="$1"
    file_path="$2"
    curl -sS -X POST "$BASE_URL/api/v1/coordination/locks/release" \
      -H "Content-Type: application/json" \
      -d "{\"session_id\":\"$SESSION_ID\",\"user_id\":\"$USER_ID\",\"file_path\":\"$file_path\",\"agent_id\":\"$agent_id\"}"
    ;;
  *)
    echo "Unknown command: $cmd"
    exit 1
    ;;
esac
