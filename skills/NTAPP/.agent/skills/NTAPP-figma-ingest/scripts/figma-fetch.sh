#!/usr/bin/env bash
# figma-fetch.sh — network layer duy nhất của /ntapp-figma-ingest.
#
# Tại sao là script chứ không để agent tự curl:
#   1. U7 context hygiene — response Figma (hàng trăm KB → chục MB) KHÔNG được vào
#      context window. Script ghi ra file, agent chỉ đọc bản đã `jq` prune.
#   2. U4 determinism — chunk/retry/sort ổn định, cùng input ra cùng output.
#   3. U6 secret hygiene — PAT chỉ đọc từ env, không bao giờ in ra stdout/stderr.
#
# Usage:
#   figma-fetch.sh whoami
#   figma-fetch.sh file-meta  --out F
#   figma-fetch.sh file-tree  [--depth N] --out F
#   figma-fetch.sh nodes      --ids "1:2,3:4" [--depth N] --out F
#   figma-fetch.sh images     --ids "1:2,3:4" [--scale N] [--format png]
#                             --dest DIR [--name-map F]
#   figma-fetch.sh variables  --out F        # Enterprise only; 403 → caller fallback
#   figma-fetch.sh styles     --out F
#
# Global flags: --file-key K   (default $FIGMA_FILE_KEY)
#               --version V    (default $FIGMA_FILE_VERSION — PIN cả run, xem U4)
# Env:          FIGMA_TOKEN    (bắt buộc; scope file_content:read)
#
# Exit: 0 ok | 1 usage/precondition | 2 auth (401/403) | 3 not found (404)
#       4 rate-limit hết retry (429) | 5 lỗi khác

set -euo pipefail

API="https://api.figma.com"
MAX_RETRY=3
CHUNK=40               # ids/request — chặn URL quá dài
UA="ntapp-figma-ingest/1.0"

die()  { echo "[figma-fetch] ERROR: $1" >&2; exit "${2:-5}"; }
warn() { echo "[figma-fetch] WARN: $*" >&2; }
info() { echo "[figma-fetch] $*" >&2; }

need() { command -v "$1" >/dev/null 2>&1 || die "thiếu '$1' — cài rồi chạy lại" 1; }
need curl
need jq

[[ -n "${FIGMA_TOKEN:-}" ]] || die "env FIGMA_TOKEN chưa set (Figma → Settings → Security → Personal access tokens). KHÔNG đặt PAT vào .bmm-config.yaml." 1

# ─── arg parse ──────────────────────────────────────────────────────
CMD="${1:-}"; shift || true
[[ -n "$CMD" ]] || die "thiếu command. Xem header file để biết usage." 1

FILE_KEY="${FIGMA_FILE_KEY:-}"
VERSION="${FIGMA_FILE_VERSION:-}"
OUT=""; DEST=""; IDS=""; DEPTH=""; SCALE="2"; FORMAT="png"; NAME_MAP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file-key) FILE_KEY="${2:-}"; shift 2 ;;
    --version)  VERSION="${2:-}";  shift 2 ;;
    --out)      OUT="${2:-}";      shift 2 ;;
    --dest)     DEST="${2:-}";     shift 2 ;;
    --ids)      IDS="${2:-}";      shift 2 ;;
    --depth)    DEPTH="${2:-}";    shift 2 ;;
    --scale)    SCALE="${2:-}";    shift 2 ;;
    --format)   FORMAT="${2:-}";   shift 2 ;;
    --name-map) NAME_MAP="${2:-}"; shift 2 ;;
    *) die "flag không nhận diện: $1" 1 ;;
  esac
done

# ─── atomic write helper (U1) ───────────────────────────────────────
# Mọi output đi qua tmp → rename. Không partial write.
finalize() {  # finalize <tmp> <dest>
  local tmp="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  mv -f "$tmp" "$dest"
}

# ─── HTTP GET với retry/backoff ─────────────────────────────────────
# api_get <path-with-query> <outfile>   (outfile = body; return code = exit status)
api_get() {
  local path="$1" outfile="$2"
  local attempt=0 code tmp
  tmp="$(mktemp)"
  while :; do
    attempt=$((attempt + 1))
    code="$(curl -sS -o "$tmp" -w '%{http_code}' \
              -H "X-Figma-Token: ${FIGMA_TOKEN}" \
              -H "User-Agent: ${UA}" \
              "${API}${path}" || echo "000")"
    case "$code" in
      200)
        mv -f "$tmp" "$outfile"; return 0 ;;
      401|403)
        rm -f "$tmp"
        die "HTTP $code — PAT không hợp lệ hoặc account không có quyền (file private? org khác? PAT thiếu scope?)" 2 ;;
      404)
        rm -f "$tmp"
        die "HTTP 404 — file_key/node không tồn tại. Dán link từ thanh địa chỉ khi mở file ở chế độ Design." 3 ;;
      429|500|502|503|504|000)
        if [[ $attempt -gt $MAX_RETRY ]]; then
          rm -f "$tmp"
          [[ "$code" == "429" ]] && die "HTTP 429 — hết $MAX_RETRY lần retry. Chờ vài phút rồi chạy lại (re-ingest sẽ skip phần đã xong nhờ checksum)." 4
          die "HTTP $code — hết $MAX_RETRY lần retry" 5
        fi
        local backoff=$((2 ** attempt))
        warn "HTTP $code — retry ${attempt}/${MAX_RETRY} sau ${backoff}s"
        sleep "$backoff" ;;
      *)
        rm -f "$tmp"
        die "HTTP $code (không xử lý được)" 5 ;;
    esac
  done
}

require_key() { [[ -n "$FILE_KEY" ]] || die "thiếu --file-key (hoặc env FIGMA_FILE_KEY)" 1; }
require_out() { [[ -n "$OUT" ]]      || die "thiếu --out" 1; }
require_ids() { [[ -n "$IDS" ]]      || die "thiếu --ids" 1; }

# version param dùng chung — PIN toàn run (U4)
vparam() { [[ -n "$VERSION" ]] && printf '&version=%s' "$VERSION" || true; }

# chunk_ids <csv> → in từng chunk 1 dòng
chunk_ids() {
  printf '%s' "$1" | tr ',' '\n' | sed '/^[[:space:]]*$/d' \
    | awk -v n="$CHUNK" 'NR%n==1{if(s!="")print s; s=$0; next}{s=s","$0}END{if(s!="")print s}'
}

case "$CMD" in

  whoami)
    tmp="$(mktemp)"
    api_get "/v1/me" "$tmp"
    jq -r '"[figma-fetch] auth OK — handle=\(.handle // "?")"' "$tmp" >&2
    rm -f "$tmp"
    ;;

  file-meta)
    require_key; require_out
    # depth=1 → chỉ document + children cấp 1 (tên page). Đủ cho provenance, không kéo cả file.
    tmp="$(mktemp)"
    api_get "/v1/files/${FILE_KEY}?depth=1$(vparam)" "$tmp"
    jq -S '{name, version, lastModified, role, editorType,
            document: {children: [.document.children[]? | {id, name, type}]}}' "$tmp" > "${tmp}.j"
    rm -f "$tmp"; finalize "${tmp}.j" "$OUT"
    info "file-meta → $OUT"
    ;;

  file-tree)
    require_key; require_out
    d="${DEPTH:-3}"
    tmp="$(mktemp)"
    api_get "/v1/files/${FILE_KEY}?depth=${d}$(vparam)" "$tmp"
    jq -S '.' "$tmp" > "${tmp}.j"
    rm -f "$tmp"; finalize "${tmp}.j" "$OUT"
    info "file-tree (depth=$d) → $OUT"
    ;;

  nodes)
    require_key; require_out; require_ids
    d="${DEPTH:-12}"
    workdir="$(mktemp -d)"; i=0
    while IFS= read -r chunk; do
      [[ -z "$chunk" ]] && continue
      i=$((i + 1))
      # ids có ':' — an toàn trong query string; encode qua --get để chắc chắn
      enc="$(printf '%s' "$chunk" | jq -sRr @uri)"
      api_get "/v1/files/${FILE_KEY}/nodes?ids=${enc}&depth=${d}$(vparam)" "${workdir}/c${i}.json"
    done < <(chunk_ids "$IDS")
    [[ $i -gt 0 ]] || die "chunk_ids không sinh chunk nào từ --ids" 1
    tmp="$(mktemp)"
    jq -s -S '{ name: (.[0].name // null),
                version: (.[0].version // null),
                nodes: (map(.nodes // {}) | add) }' "${workdir}"/c*.json > "$tmp"
    rm -rf "$workdir"
    finalize "$tmp" "$OUT"
    info "nodes ($i chunk, depth=$d) → $OUT"
    ;;

  images)
    require_key; require_ids
    [[ -n "$DEST" ]] || die "thiếu --dest" 1
    mkdir -p "$DEST"
    workdir="$(mktemp -d)"; i=0
    while IFS= read -r chunk; do
      [[ -z "$chunk" ]] && continue
      i=$((i + 1))
      enc="$(printf '%s' "$chunk" | jq -sRr @uri)"
      api_get "/v1/images/${FILE_KEY}?ids=${enc}&format=${FORMAT}&scale=${SCALE}$(vparam)" \
              "${workdir}/r${i}.json"
    done < <(chunk_ids "$IDS")

    # Gộp map node_id → signed URL. URL này HẾT HẠN và TUYỆT ĐỐI không được lưu
    # vào artifact nào (U6) — chỉ tồn tại trong workdir tạm, xoá ở cuối.
    jq -s -S '{ err: (map(.err) | map(select(. != null)) | first),
                images: (map(.images // {}) | add) }' "${workdir}"/r*.json > "${workdir}/merged.json"

    err="$(jq -r '.err // empty' "${workdir}/merged.json")"
    [[ -n "$err" ]] && warn "Figma trả err='$err' — một số node có thể không render được"

    fail=0; okc=0
    while IFS=$'\t' read -r node url; do
      [[ -z "$node" ]] && continue
      base=""
      if [[ -n "$NAME_MAP" && -f "$NAME_MAP" ]]; then
        base="$(jq -r --arg n "$node" '.[$n] // empty' "$NAME_MAP")"
      fi
      [[ -n "$base" ]] || base="node_${node//:/-}"
      target="${DEST}/${base}.${FORMAT}"

      if [[ -z "$url" || "$url" == "null" ]]; then
        printf 'fail\t%s\t%s\n' "$node" "no-render-url"
        fail=$((fail + 1)); continue
      fi
      if curl -sS --fail -o "${target}.part" "$url"; then
        # verify magic bytes PNG (89 50 4E 47) trước khi rename
        if [[ "$FORMAT" == "png" ]] \
           && [[ "$(head -c 4 "${target}.part" | od -An -tx1 | tr -d ' \n')" != "89504e47" ]]; then
          rm -f "${target}.part"
          printf 'fail\t%s\t%s\n' "$node" "not-a-png"
          fail=$((fail + 1)); continue
        fi
        finalize "${target}.part" "$target"
        printf 'ok\t%s\t%s\n' "$node" "$target"
        okc=$((okc + 1))
      else
        rm -f "${target}.part"
        printf 'fail\t%s\t%s\n' "$node" "download-failed"
        fail=$((fail + 1))
      fi
    done < <(jq -r '.images | to_entries[] | "\(.key)\t\(.value)"' "${workdir}/merged.json")

    rm -rf "$workdir"     # signed URL biến mất cùng workdir (U6)
    info "images: ok=$okc fail=$fail → $DEST"
    [[ $okc -gt 0 || $fail -eq 0 ]] || exit 5
    ;;

  variables)
    require_key; require_out
    # Enterprise-only. 403 ở đây KHÔNG phải lỗi cấu hình — caller (step-01t) fallback /styles.
    tmp="$(mktemp)"
    code="$(curl -sS -o "$tmp" -w '%{http_code}' \
              -H "X-Figma-Token: ${FIGMA_TOKEN}" -H "User-Agent: ${UA}" \
              "${API}/v1/files/${FILE_KEY}/variables/local" || echo "000")"
    case "$code" in
      200) jq -S '.' "$tmp" > "${tmp}.j"; rm -f "$tmp"; finalize "${tmp}.j" "$OUT"
           info "variables → $OUT" ;;
      403) rm -f "$tmp"
           warn "403 — /variables/local yêu cầu Figma Enterprise. Fallback /styles hoặc Tokens Studio export."
           exit 2 ;;
      404) rm -f "$tmp"; warn "404 — file không có variable"; exit 3 ;;
      *)   rm -f "$tmp"; die "HTTP $code khi lấy variables" 5 ;;
    esac
    ;;

  styles)
    require_key; require_out
    tmp="$(mktemp)"
    api_get "/v1/files/${FILE_KEY}/styles" "$tmp"
    jq -S '.' "$tmp" > "${tmp}.j"
    rm -f "$tmp"; finalize "${tmp}.j" "$OUT"
    info "styles → $OUT"
    ;;

  *)
    die "command không nhận diện: $CMD" 1 ;;
esac
