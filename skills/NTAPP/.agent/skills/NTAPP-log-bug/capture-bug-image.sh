#!/usr/bin/env bash
# Helper cross-OS cho skill NTAPP-log-bug: tìm ảnh screenshot để đính vào bug.
# Chạy được trên macOS (Bash tool) và Windows (Git Bash / WSL — gọi được powershell.exe).
#
# Ưu tiên: DÒ FILE TRONG FOLDER TRƯỚC — vì 1 bug có thể kèm NHIỀU ảnh, mà clipboard chỉ giữ
# được 1 ảnh. Clipboard chỉ là FALLBACK khi không có file.
# Folder quét theo đúng nơi hot-key mặc định lưu, per-OS:
#   macOS   : ~/Desktop (default Cmd+Shift+3/4/5) + folder cấu hình qua `defaults`
#             (com.apple.screencapture location) + Downloads/Pictures/Documents.
#   Windows : %USERPROFILE%\Pictures\Screenshots (Win+PrtScn) + Downloads + Desktop.
#
# Usage:
#   capture-bug-image.sh [--minutes N]        # (default) liệt kê file ảnh mới + trạng thái clipboard
#   capture-bug-image.sh --clip <out.png>     # fallback: đổ ảnh clipboard ra file
#   capture-bug-image.sh --check              # chỉ báo clipboard có ảnh không
#
# Output --list (dễ parse):
#   === RECENT FILES (last N min) ===
#   <YYYY-MM-DD HH:MM:SS>   <bytes>   <full-path>      (mới nhất trước; tối đa 10)
#   (none)                                             (nếu không có file)
#   === CLIPBOARD ===
#   HAS_IMAGE | NONE
#
# Output --clip:  SAVED: <path> | NO_IMAGE_IN_CLIPBOARD
# Output --check: HAS_IMAGE | NO_IMAGE_IN_CLIPBOARD
set -euo pipefail

MINUTES=20
OS="$(uname -s)"

# --- stat / date flavor (GNU vs BSD) --------------------------------------
if stat -c '%Y' . >/dev/null 2>&1; then STAT=gnu; else STAT=bsd; fi
statline() {  # in ra "epoch size path" (path giữ nguyên khoảng trắng ở cuối)
    if [ "$STAT" = gnu ]; then stat -c '%Y %s %n' "$1"; else stat -f '%m %z %N' "$1"; fi
}
fmt_time() {  # epoch -> chuỗi thời gian đọc được
    if [ "$STAT" = bsd ]; then date -r "$1" +'%Y-%m-%d %H:%M:%S'; else date -d "@$1" +'%Y-%m-%d %H:%M:%S'; fi
}

# --- Windows detection + Windows-home resolve ------------------------------
is_wsl() { grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; }
is_windows() {
    case "$OS" in MINGW*|MSYS*|CYGWIN*) return 0 ;; esac
    is_wsl && return 0 || return 1
}
win_home=""
if [ -n "${USERPROFILE:-}" ]; then
    if command -v cygpath >/dev/null 2>&1;  then win_home="$(cygpath -u "$USERPROFILE" 2>/dev/null || true)"
    elif command -v wslpath >/dev/null 2>&1; then win_home="$(wslpath -u "$USERPROFILE" 2>/dev/null || true)"
    fi
fi

# --- danh sách thư mục quét (per-OS: đúng nơi hot-key mặc định lưu) ---------
SCAN_DIRS=()
add_dir() {  # chuẩn hoá bỏ '/' cuối + dedupe (vd defaults location == một static dir)
    local d="${1%/}" e
    [ -n "$d" ] || return
    for e in ${SCAN_DIRS[@]+"${SCAN_DIRS[@]}"}; do [ "$e" = "$d" ] && return; done
    SCAN_DIRS+=("$d")
}
if [ "$OS" = "Darwin" ]; then
    # macOS: Cmd+Shift+3/4/5 mặc định lưu ra ~/Desktop. Đọc luôn folder user đã đổi (nếu có)
    # qua `defaults`; rỗng nghĩa là đang dùng default (Desktop) hoặc chỉ-clipboard.
    loc="$(defaults read com.apple.screencapture location 2>/dev/null || true)"
    add_dir "${loc/#\~/$HOME}"           # rỗng → add_dir tự bỏ qua
    add_dir "$HOME/Desktop"              # default thật của macOS
    add_dir "$HOME/Downloads"
    add_dir "$HOME/Pictures/Screenshots" # nếu user tự tạo folder này
    add_dir "$HOME/Documents"
elif is_windows; then
    b="${win_home:-$HOME}"
    add_dir "$b/Pictures/Screenshots"    # Win+PrtScn / Win+Shift+S auto-save mặc định
    add_dir "$b/Downloads"
    add_dir "$b/Desktop"
else
    # Linux / khác — đoán chung
    add_dir "$HOME/Pictures/Screenshots"
    add_dir "$HOME/Pictures"
    add_dir "$HOME/Desktop"
    add_dir "$HOME/Downloads"
fi

# --- clipboard: check + save (per-OS) --------------------------------------
clip_has_image() {
    if [ "$OS" = "Darwin" ]; then
        osascript -e 'the clipboard as «class PNGf»' >/dev/null 2>&1
    elif is_windows; then
        local r
        r="$(powershell.exe -NoProfile -Command \
            "Add-Type -AssemblyName System.Windows.Forms; if([Windows.Forms.Clipboard]::ContainsImage()){'1'}else{'0'}" \
            2>/dev/null | tr -d '\r\n ')"
        [ "$r" = "1" ]
    else
        return 1
    fi
}
clip_save() {  # $1 = out path (unix)
    local out="$1"; mkdir -p "$(dirname "$out")"
    if [ "$OS" = "Darwin" ]; then
        osascript >/dev/null 2>&1 <<EOF
set outFile to POSIX file "$out"
set pngData to (the clipboard as «class PNGf»)
set fh to open for access outFile with write permission
set eof fh to 0
write pngData to fh
close access fh
EOF
    elif is_windows; then
        local winout
        if command -v cygpath >/dev/null 2>&1;  then winout="$(cygpath -w "$out")"
        elif command -v wslpath >/dev/null 2>&1; then winout="$(wslpath -w "$out")"
        else winout="$out"; fi
        powershell.exe -NoProfile -STA -Command \
            "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; \
             \$i=[Windows.Forms.Clipboard]::GetImage(); \
             if(\$i){ \$i.Save('$winout',[System.Drawing.Imaging.ImageFormat]::Png) }" >/dev/null 2>&1 || true
    fi
    [ -s "$out" ]
}

# --- scan folders → in candidates -----------------------------------------
list_recent() {
    local files=() blocked=() dir line errf
    for dir in "${SCAN_DIRS[@]}"; do
        [ -d "$dir" ] || continue
        errf="$(mktemp 2>/dev/null || echo "/tmp/ntapp_scan_err.$$")"
        while IFS= read -r line; do files+=("$line"); done < <(
            find "$dir" -maxdepth 1 -type f -mmin -"$MINUTES" \
                \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \
                   -o -iname '*.bmp' -o -iname '*.webp' \) 2>"$errf"
        )
        # macOS TCC: Desktop/Documents có thể bị chặn (Operation not permitted) → báo rõ,
        # đừng nuốt lỗi thành "(none)" khiến user tưởng không có ảnh.
        if [ -s "$errf" ] && grep -qiE 'not permitted|permission denied' "$errf"; then
            blocked+=("$dir")
        fi
        rm -f "$errf"
    done

    echo "=== RECENT FILES (last $MINUTES min) ==="
    if [ "${#files[@]}" -eq 0 ]; then
        echo "(none)"
    else
        local f
        # uniq: bỏ file trùng khi 1 folder xuất hiện ở 2 nguồn (vd defaults location == Desktop)
        for f in "${files[@]}"; do statline "$f"; done \
            | sort -rn | uniq | head -10 \
            | while read -r epoch size path; do
                  printf '%s   %9s   %s\n' "$(fmt_time "$epoch")" "$size" "$path"
              done
    fi

    if [ "${#blocked[@]}" -gt 0 ]; then
        echo "=== BLOCKED (macOS TCC — cấp Full Disk Access cho app đang chạy để quét được) ==="
        for dir in "${blocked[@]}"; do echo "$dir"; done
    fi

    echo "=== CLIPBOARD ==="
    if clip_has_image; then echo "HAS_IMAGE"; else echo "NONE"; fi
}

# --- dispatch --------------------------------------------------------------
case "${1:-}" in
    --check)
        clip_has_image && echo "HAS_IMAGE" || echo "NO_IMAGE_IN_CLIPBOARD" ;;
    --clip)
        out="${2:-}"
        [ -n "$out" ] || { echo "USAGE: capture-bug-image.sh --clip <out.png>" >&2; exit 2; }
        if clip_save "$out"; then echo "SAVED: $out"; else echo "NO_IMAGE_IN_CLIPBOARD"; exit 1; fi ;;
    --minutes)
        MINUTES="${2:-20}"; list_recent ;;
    ""|--list)
        list_recent ;;
    *)
        echo "USAGE: capture-bug-image.sh [--minutes N] | --clip <out.png> | --check" >&2; exit 2 ;;
esac
