# vds-vidp-orchestrator

VIDP third-party gateway orchestrator for the VDS scripts ecosystem.

Wraps two VIDP endpoints:

- `POST /third-party/v2/start/{workflowId}` — trigger a workflow action
- `GET /third-party/v2/status/{jobId}?full=true` — fetch full job/stage detail

## Usage

```bash
# CLI
vds-cli vidp trigger <workflowId> --payload '{"key":"value"}'
vds-cli vidp status <jobId>

# Direct
uv run vds-vidp trigger <workflowId> --payload-file ./payload.json
```

## Environment

Loaded from the shared VDS env file (`~/.vds/.env`). Settings use prefix
`VDS_VIDP_` but legacy `VIDP_*` names are accepted as fallbacks.

| Variable                          | Required | Notes                                  |
| --------------------------------- | -------- | -------------------------------------- |
| `VDS_VIDP_BASE_URL` / `VIDP_BASE_URL` | yes      | Base URL of the VIDP gateway           |
| `VDS_VIDP_USERNAME` / `VIDP_USERNAME` | yes      | Basic-auth username                    |
| `VDS_VIDP_PASSWORD` / `VIDP_PASSWORD` | yes      | Basic-auth password                    |
| `VDS_VIDP_TIMEOUT_MS`             | no       | Request timeout in ms (default `30000`) |
