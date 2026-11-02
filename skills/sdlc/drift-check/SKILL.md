---
name: drift-check
description: Kiểm tra drift giữa các artifact SDLC theo cạnh depends_on của workflow, ghi điểm ra .vsaf/telemetry/drift.json
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Drift Check

Bạn kiểm tra artifact downstream (vd: architecture) có còn nhất quán với artifact upstream mà nó phụ thuộc (vd: prd), theo cạnh `depends_on` của workflow đang chạy. v1 chỉ xét 3 node sinh artifact doc: `prd`, `architecture`, `srs`.

Bạn (agent) tự thực hiện toàn bộ thuật toán bên dưới bằng Read/Bash — không có script nào bắt buộc phải chạy. Skill này được deploy tới `.claude/skills/sdlc-drift-check/` trong project của người dùng, nơi KHÔNG có `node_modules` (không resolve được `js-yaml`) và KHÔNG có thư mục `skills/sdlc/workflows/` nguồn — chỉ có `.vsaf/workflows/`. Vì vậy không gọi CLI resolver như bước bắt buộc.

## Các bước

### 1. Xác định workflow đang chạy và đọc file YAML

File workflow đang chạy nằm ở `<projectRoot>/.vsaf/workflows/<workflow>.yaml` (ví dụ `.vsaf/workflows/master-sdlc.yaml`) — đây là vị trí đã deploy, KHÔNG phải `skills/sdlc/workflows/` (đường dẫn đó chỉ tồn tại trong source tree của repo vsaf). Nếu không rõ đang chạy workflow nào, mặc định dùng `.vsaf/workflows/master-sdlc.yaml`.

Đọc file này bằng Read tool và tự parse cấu trúc YAML (mỗi node có `id`, `depends_on`, `type`/`command`...). Bạn là LLM, đọc YAML trực tiếp được, không cần thư viện parser.

### 2. Xác định node sinh artifact doc

v1 cố định tập node: `prd`, `architecture`, `srs`. Bỏ qua mọi node khác (gate, bash, implement, test-gate, review, ship, ...) — chúng chỉ là trạm trung gian trong đồ thị phụ thuộc.

### 3. Giải các cạnh (resolve edges) bằng thuật toán sau

Với mỗi node artifact, đi ngược `depends_on` xuyên qua các node KHÔNG phải artifact (gate/bash/...) tới (các) tổ tiên artifact gần nhất, rồi phát ra cặp `(downstream, upstream)`:

- Với node artifact `N`, khởi tạo ngăn xếp = `N.depends_on`.
- Lặp: lấy `depId` ra khỏi ngăn xếp.
  - Nếu `depId` là node artifact → phát cạnh `(N, depId)`.
  - Nếu không → đẩy `depId.depends_on` vào ngăn xếp (tiếp tục đi ngược qua gate/bash).
- Dừng khi ngăn xếp rỗng. Bỏ qua id đã thăm để tránh lặp vô hạn nếu đồ thị có chu trình bất thường.

Ví dụ trên `master-sdlc.yaml`: `architecture depends_on: [prd-gate]`, `prd-gate depends_on: [prd]` → `prd-gate` không phải artifact nên đi tiếp tới `prd` → cạnh `(architecture, prd)`. Node `srs depends_on: [architecture]` trực tiếp (không qua gate) → cạnh `(srs, architecture)`.

**Fallback (v1):** nếu workflow đang chạy KHÔNG chứa node artifact nào (ví dụ workflow chỉ có một node `drift-check`, dùng để kiểm drift lặp lại), thì bỏ qua việc parse depends_on và dùng thẳng **chuỗi chuẩn v1 cố định**: cạnh `(architecture, prd)` và `(srs, architecture)`. Chỉ giữ cạnh nào có đủ 2 file artifact tồn tại trên đĩa (bước 4).

### 4. Map node id → file artifact

Mỗi node id ứng với file dưới `.vsaf/docs/features/{feature-name}/` theo đúng quy ước hiện có của repo (xem `skills/sdlc/{prd,architecture,srs}/SKILL.md` §Output):

| node id        | file                                              |
|----------------|----------------------------------------------------|
| `prd`          | `.vsaf/docs/features/{feature-name}/02-prd.md`     |
| `architecture` | `.vsaf/docs/features/{feature-name}/03-adr.md`     |
| `srs`          | `.vsaf/docs/features/{feature-name}/05-srs.md`     |

Nếu có nhiều thư mục `{feature-name}` tồn tại, dùng thư mục của feature đang được làm việc trong phiên hiện tại (thường là thư mục có artifact được sửa gần nhất). Nếu file của một node chưa tồn tại (chưa chạy tới bước đó), bỏ qua cạnh liên quan.

### 5. Đọc nội dung + chấm điểm MỌI cặp

Với **mỗi** cạnh `(downstream, upstream)` có đủ cả 2 file trên đĩa (bước 4): đọc cả 2 file bằng Read tool. Đánh giá downstream có còn phản ánh đúng nội dung/quyết định của upstream không — **so về mặt ngữ nghĩa nội dung, KHÔNG dựa vào thời điểm sửa**. Chấm `score` từ 0.0 (hoàn toàn lệch) đến 1.0 (nhất quán hoàn toàn), viết `reason` ngắn gọn (1-2 câu) nêu điểm lệch chính (hoặc xác nhận vẫn nhất quán nếu score cao). Ghi `checked: true`.

> **Vì sao luôn đọc nội dung, không dùng gate git-time:** hai doc có thể được tạo/commit **cùng thời điểm** mà vẫn lệch nội dung (ví dụ architecture không phản ánh đúng prd ngay từ lúc sinh). "Mới" không đồng nghĩa "nhất quán" — git commit time chỉ bắt drift theo thời gian, bỏ sót drift nội dung có sẵn từ đầu. Nên mọi cặp đều phải chấm bằng nội dung. v1 chỉ có 2 cạnh nên chi phí nhỏ.

### 6. Ghi kết quả

Tạo thư mục `.vsaf/telemetry/` (dưới project root) nếu chưa có. Ghi đè file `.vsaf/telemetry/drift.json` (mỗi lần chạy ghi đè toàn bộ, không append) đúng schema, field name viết đúng nguyên văn (`downstreamNode`, `upstreamNode`, `score`, `reason`, `checked`):

```json
{
  "edges": [
    { "downstreamNode": "architecture", "upstreamNode": "prd", "score": 0.8, "reason": "...", "checked": true }
  ]
}
```

(MCP layer đọc file này để gắn Langfuse score theo từng node.)

### 7. Tóm tắt cho người dùng

In ngắn gọn từng cặp đã chấm: `downstream ← upstream`, điểm, và 1 câu lý do. Nêu rõ cặp nào điểm thấp (drift).

## Ràng buộc

- Chỉ xét cạnh **doc↔doc** (v1: prd, architecture, srs). Bỏ qua cạnh có đầu là node code/implement/test-gate.
- **Không sửa bất kỳ artifact nào** — chỉ đọc `.vsaf/docs/**` và ghi ra `.vsaf/telemetry/drift.json`.
- **Luôn chấm bằng nội dung** mọi cặp có đủ 2 file — không dùng git commit time / mtime làm cổng bỏ qua (drift nội dung có thể tồn tại ngay cả khi 2 file cùng thời điểm).

## Optional accelerator (chỉ khi chạy trong source tree của repo vsaf)

Nếu bạn đang chạy TRONG repo nguồn `vsaf` (không phải bản đã deploy) — tức `skills/sdlc/workflows/*.yaml` và `node_modules/js-yaml` đều tồn tại — có thể dùng script đã test sẵn để tăng tốc bước 3+5 thay vì tự làm bằng tay:

```bash
node skills/sdlc/drift-check/lib/resolve-drift-edges.mjs \
  skills/sdlc/workflows/master-sdlc.yaml \
  prd,architecture,srs \
  .
```

In ra JSON array `{ downstream, upstream, stale }` cho từng cạnh — chỉ dùng phần `downstream`/`upstream` (danh sách cạnh) để đỡ tự resolve; **bỏ qua field `stale`** (v1 không dùng gate git-time nữa, luôn chấm nội dung ở bước 5). Đây CHỈ là tiện ích tăng tốc bước 3 khi dogfeed trong chính repo vsaf — KHÔNG phải đường dẫn chính, không được giả định tồn tại trong project đã deploy skill này. Nếu không chắc mình đang ở đâu, hoặc script/`js-yaml` không resolve được, cứ dùng thuật toán ở bước 1-5 (đọc YAML trực tiếp).
