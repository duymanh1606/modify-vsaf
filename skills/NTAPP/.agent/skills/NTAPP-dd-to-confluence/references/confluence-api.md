# Confluence REST API — GET / POST / PUT / duyệt cây

Skill dùng REST API của Confluence (Server/DC). Chạy trong Git Bash trên Windows; ưu tiên `curl` + `python3` để build/parse JSON an toàn (XHTML lớn dễ vỡ nếu escape tay trong shell).

## Credentials

Đọc từ `{env_file}` — đường dẫn được resolve theo thứ tự ưu tiên ở `workflow.md` §2 (config key `confluence.env_file` → biến môi trường `CONFLUENCE_ENV_FILE` → các vị trí tương đối `.env/env.md`, `.env`, `env.md` tính từ project root → `$HOME/.env/env.md`; không tìm thấy → DỪNG hỏi user). KHÔNG hardcode đường dẫn tuyệt đối theo máy cụ thể.
- `CONFLUENCE_URL` — base URL (vd `http://10.254.136.35:8090`).
- `CONFLUENCE_TOKEN` — Bearer token (Personal Access Token).
- (tuỳ chọn) host thứ hai nếu env khai báo.

Quy tắc host: **dùng đúng host của link/URL đang xử lý** (`10.254.136.32:8090` hoặc `10.254.136.35:8090`), cùng token. **Không** tự thử host còn lại khi lỗi — DỪNG hỏi user. **Không in token** ra output/log.

```bash
# Ví dụ nạp biến (không echo token)
CONFLUENCE_TOKEN="$(grep -E '^CONFLUENCE_TOKEN' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d ' "')"
```

## Đọc trang (GET storage-format)

```bash
curl -s -H "Authorization: Bearer $CONFLUENCE_TOKEN" -H "Accept: application/json" \
  "$HOST/rest/api/content/$PAGE_ID?expand=body.storage,version,ancestors,space" \
  > page.json
# Trích các trường cần
python3 - <<'PY'
import json
d=json.load(open('page.json'))
print("TITLE:", d.get('title'))
print("VERSION:", d.get('version',{}).get('number'))
print("SPACE:", d.get('space',{}).get('key'))
# body.storage.value chứa XHTML storage-format
open('page_body.xhtml','w',encoding='utf-8').write(d.get('body',{}).get('storage',{}).get('value',''))
PY
```

Từ URL dạng `.../pages/viewpage.action?pageId=NNN` → `PAGE_ID=NNN`. Từ URL dạng `/display/SPACE/Title+With+Plus` → GET theo title:
```bash
curl -s -H "Authorization: Bearer $CONFLUENCE_TOKEN" \
  "$HOST/rest/api/content?spaceKey=$SPACE&title=$TITLE_ENCODED&expand=body.storage,version"
```

## Duyệt cây trang con (đệ quy)

Trang quản lý DD có thể chứa nhiều tầng thư mục con. Duyệt BFS/DFS qua `child/page`:

```bash
curl -s -H "Authorization: Bearer $CONFLUENCE_TOKEN" \
  "$HOST/rest/api/content/$PARENT_ID/child/page?limit=100&expand=version" > children.json
# Lấy id + title; nếu 'size' == limit thì phân trang tiếp bằng ?start=
```

Đệ quy: với mỗi child, lại GET `child/page` của nó cho tới khi hết. Match title gần giống tên feature (so khớp không dấu, lowercase, chứa mã ID hoặc tên tính năng) → GET body kiểm chứng nội dung đúng feature trước khi quyết định UPDATE.

Ghi chú phân trang: response có `_links.next` khi còn trang; lặp cho tới khi hết.

## Tạo trang mới (POST)

Build payload bằng python để tránh vỡ escape (đọc XHTML từ file):

```bash
python3 - "$SPACE" "$PARENT_ID" "$TITLE" body.xhtml payload.json <<'PY'
import json,sys
space,parent,title,bodyfile,out=sys.argv[1:6]
body=open(bodyfile,encoding='utf-8').read()
payload={"type":"page","title":title,"space":{"key":space},
 "ancestors":[{"id":int(parent)}],
 "body":{"storage":{"value":body,"representation":"storage"}}}
json.dump(payload,open(out,'w',encoding='utf-8'))
PY

curl -s -X POST -H "Authorization: Bearer $CONFLUENCE_TOKEN" \
  -H "Content-Type: application/json" \
  --data @payload.json "$HOST/rest/api/content" > created.json
python3 -c "import json;d=json.load(open('created.json'));print(d.get('id'), d.get('_links',{}).get('base','')+d.get('_links',{}).get('webui',''))"
```

## Cập nhật trang (PUT)

Bắt buộc `version.number = version_cũ + 1`.

```bash
python3 - "$PAGE_ID" "$TITLE" "$NEW_VERSION" body.xhtml payload.json <<'PY'
import json,sys
pid,title,ver,bodyfile,out=sys.argv[1:6]
body=open(bodyfile,encoding='utf-8').read()
payload={"id":pid,"type":"page","title":title,
 "version":{"number":int(ver)},
 "body":{"storage":{"value":body,"representation":"storage"}}}
json.dump(payload,open(out,'w',encoding='utf-8'))
PY

curl -s -X PUT -H "Authorization: Bearer $CONFLUENCE_TOKEN" \
  -H "Content-Type: application/json" \
  --data @payload.json "$HOST/rest/api/content/$PAGE_ID" > updated.json
```

## Upload attachment (chỉ khi cần)

```bash
curl -s -X POST -H "Authorization: Bearer $CONFLUENCE_TOKEN" \
  -H "X-Atlassian-Token: nocheck" \
  -F "file=@diagram.png" \
  "$HOST/rest/api/content/$PAGE_ID/child/attachment"
```

## Bảng lỗi

| Mã | Nguyên nhân | Xử lý |
|:---|:---|:---|
| 401 | Token sai/hết hạn | DỪNG, báo user kiểm tra `CONFLUENCE_TOKEN` trong env |
| 403 | Không đủ quyền ghi/không gian bị khoá | DỪNG, báo user liên hệ admin / kiểm tra quyền space |
| 404 | pageId/space/title sai | DỪNG, hỏi user (không thử host khác) |
| 409 | Version conflict (PUT sai số version) | GET lại version mới → rebuild → preview lại |
| Body rỗng/parse fail | Response lỗi | Chạy lại curl bỏ pipe python để xem raw; DỪNG báo user |

## Lưu ý an toàn

- Mọi POST/PUT chỉ chạy **sau** khi user xác nhận ở Bước 7.
- Dọn file tạm (`*.json`, `*.xhtml`) vào thư mục scratchpad, không để rác trong repo.
- Không log token; log chỉ ghi host/pageId/version/action.
