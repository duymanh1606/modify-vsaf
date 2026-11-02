# Mermaid → PlantUML (house-style) + PlantUML Macro

DD spec chứa sơ đồ ` ```mermaid `. Confluence của dự án có **PlantUML Macro** (đã xác nhận). Convert Mermaid → PlantUML, nhúng vào PlantUML Macro.

## Xác định đúng tên macro (probe trước khi build)

Tên macro trong storage-format khác nhau tuỳ plugin. **Không đoán** — lấy mẫu thật:

1. GET storage của một trang DD hiện có đang dùng PlantUML (vd trang trong `9.3.4. Reconcile Service`), tìm `<ac:structured-macro ac:name="...">` bao quanh code `@startuml`.
2. Lấy `ac:name` (vd `plantuml`, `plantumlcloud`, `plantuml-render`...) và tên tham số body (thường `<ac:plain-text-body><![CDATA[ ... ]]></ac:plain-text-body>`).
3. Dùng đúng `ac:name` + cấu trúc body đó khi build. Nếu không probe được → DỪNG hỏi user, hoặc fallback Code Block (xem cuối file).

Khung điển hình:
```xml
<ac:structured-macro ac:name="PLANTUML_MACRO_NAME">
  <ac:plain-text-body><![CDATA[@startuml
... nội dung PlantUML ...
@enduml]]></ac:plain-text-body>
</ac:structured-macro>
```

## House-style preamble (bắt buộc cho sequence)

Theo mẫu DD của tổ chức, mỗi sequence PlantUML mở đầu bằng:

```
@startuml
skinparam sequence {
    ArrowThickness 2
    ParticipantBorderColor #2c3e50
    ParticipantBackgroundColor #ecf0f1
    LifeLineBorderColor #7f8c8d
    LifeLineBackgroundColor #bdc3c7
    ArrowColor #2980b9
    ParticipantFontColor #2c3e50
}
skinparam titleFontSize 18

title <tiêu đề sơ đồ>
```
và kết bằng `@enduml`.

## Ánh xạ cú pháp — sequenceDiagram

| Mermaid | PlantUML |
|:---|:---|
| `sequenceDiagram` | (bỏ — dùng preamble ở trên) |
| `actor A as Tên` | `actor "Tên" as A` |
| `participant P as Tên` | `participant "Tên" as P` |
| (queue/topic) | `queue "Tên" as X` |
| (DB/redis) | `database "Tên" as X` |
| `A->>B: msg` | `A -> B : msg` |
| `A-->>B: msg` (dashed reply) | `A --> B : msg` |
| `Note over A: text` | `note over A : text` |
| `Note right of A: text` | `note right of A : text` |
| `activate A` / `deactivate A` | `activate A` / `deactivate A` |
| `alt/else/end` | `alt/else/end` |
| `opt/end` | `opt/end` |
| `loop X/end` | `loop X/end` |
| `par/and/end` | `par/and/end` |
| `autonumber` | `autonumber` |
| `<br/>` trong label | `\n` |

Giữ nguyên thứ tự khai báo participant như Mermaid để layout ổn định.

## Ánh xạ cú pháp — flowchart

| Mermaid | PlantUML (dùng activity mới) |
|:---|:---|
| `flowchart TD` / `graph TD` | `@startuml` + `start` ... `stop` |
| `A[Việc]` | `:Việc;` |
| `A{Điều kiện}` | `if (Điều kiện?) then (yes) ... else (no) ... endif` |
| `A --> B` | thứ tự tuần tự các `:...;` |
| nhánh label `-->|yes|` | nhánh `then (yes)` / `else (no)` |

Flowchart phức tạp (nhiều nhánh chéo, subgraph) khó map 1-1 → nếu không chắc chính xác thì **fallback Code Block** thay vì vẽ sai.

## Fallback — Code Block macro

Áp dụng khi: không probe được tên PlantUML macro, hoặc diagram không convert gọn/đúng.

```xml
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">text</ac:parameter>
  <ac:plain-text-body><![CDATA[<nguyên source mermaid>]]></ac:plain-text-body>
</ac:structured-macro>
```

Mỗi lần fallback phải **ghi vào log + report** (diagram nào, lý do) để user biết cần chỉnh tay.

## Escape

Nội dung trong `<![CDATA[ ... ]]>` không cần escape XML. Chỉ đảm bảo source không chứa chuỗi `]]>`; nếu có, tách thành `]]]]><![CDATA[>`.
