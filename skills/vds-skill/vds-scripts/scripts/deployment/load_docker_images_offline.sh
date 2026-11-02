#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  load_docker_images_offline.sh --images-dir <directory-with-tar-files> [--dry-run]
  load_docker_images_offline.sh --image <path-to-image.tar> [--image <path-to-image.tar> ...] [--dry-run]

Description:
  Load one or more Docker image tar archives in air-gapped/offline deployments.

Options:
  --images-dir <dir>   Directory containing *.tar Docker image archives
  --image <path>       Single Docker image tar archive (can be repeated)
  --dry-run            Print planned docker load commands without executing
  -h, --help           Show this help
USAGE
}

IMAGES_DIR=""
DRY_RUN=false
declare -a IMAGE_FILES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --images-dir)
      shift
      IMAGES_DIR="${1:-}"
      ;;
    --image)
      shift
      IMAGE_FILES+=("${1:-}")
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
  shift
done

if [[ -n "$IMAGES_DIR" && ${#IMAGE_FILES[@]} -gt 0 ]]; then
  echo "Use either --images-dir or --image, not both." >&2
  exit 2
fi

if [[ -n "$IMAGES_DIR" ]]; then
  if [[ ! -d "$IMAGES_DIR" ]]; then
    echo "Images directory not found: $IMAGES_DIR" >&2
    exit 2
  fi
  while IFS= read -r -d '' tar_file; do
    IMAGE_FILES+=("$tar_file")
  done < <(find "$IMAGES_DIR" -maxdepth 1 -type f -name '*.tar' -print0 | sort -z)
fi

if [[ ${#IMAGE_FILES[@]} -eq 0 ]]; then
  echo "No image tar files provided." >&2
  usage
  exit 2
fi

echo "Loading ${#IMAGE_FILES[@]} image archive(s)..."

loaded_count=0
for image_tar in "${IMAGE_FILES[@]}"; do
  if [[ ! -f "$image_tar" ]]; then
    echo "Missing image archive: $image_tar" >&2
    exit 2
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[dry-run] docker load -i \"$image_tar\""
  else
    echo "docker load -i \"$image_tar\""
    docker load -i "$image_tar"
  fi
  loaded_count=$((loaded_count + 1))
done

echo "Completed. Processed $loaded_count archive(s)."
