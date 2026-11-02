# Offline Docker Image Load (Air-Gapped)

This guide defines the standard process to deploy container images in environments without direct registry access.

## Scope

- Deploy pre-exported Docker images from `.tar` archives.
- Validate loaded images before starting `docker compose`.
- Keep an auditable, repeatable script for operations teams.

## Prerequisites

- Docker Engine available on target host.
- Image archives prepared from a connected environment (for example: `docker save -o vds-cli.tar vds-cli:2026.02.23`).
- Access to this script:
  - `scripts/deployment/load_docker_images_offline.sh`

## Procedure

1. Copy image archives to the target host, for example:
   - `/opt/vds/images/vds-cli.tar`
   - `/opt/vds/images/mcp-server.tar`
2. Load all archives in one command:

```bash
./scripts/deployment/load_docker_images_offline.sh \
  --images-dir /opt/vds/images
```

3. Verify images are available:

```bash
docker images | rg 'vds-cli|mcp-server'
```

4. Start services from local images:

```bash
cd docker
docker compose up -d
```

## Rollback

If an image is invalid or incorrect:

1. Stop dependent services: `docker compose down`
2. Remove incorrect image tags: `docker image rm <image:tag>`
3. Reload the correct tar archives with the same script.

## Operational Controls

- Always pin explicit image tags in offline export artifacts.
- Record archive checksums and load timestamp in deployment notes.
- Use `--dry-run` before maintenance windows to validate input paths:

```bash
./scripts/deployment/load_docker_images_offline.sh --images-dir /opt/vds/images --dry-run
```
