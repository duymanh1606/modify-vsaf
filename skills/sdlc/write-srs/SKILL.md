---
name: sdlc-write-srs
description: "Write SRS theo template chuẩn — feature-level v6 (12 sections 0–11) hoặc system-level v2 (cross-module), domain-neutral + multi-archetype (UI/backend/integration/batch, greenfield/brownfield). Có Decision Log, Impact Matrix, Observability, Open Questions, AI Metadata. Domain-aware + project-memory reuse + anti-hallucination guardrails + self-check 8-dimension; mode draft|standard|full. Triggers: 'write srs', 'viết srs', 'tạo srs', 'system srs'."
version: 1.6.0
author: "@ngocsangairvds/vsaf"
contributors: ["LEP team (P0/P1 fixes: 12-section sync, PlantUML-only, self-check gate, domain-aware, glossary-aware; R1 external-AI triage: guardrails/ambiguity/pre-write analysis/security-privacy; R2: project-memory/cross-feature/FR-dependency/mode/few-shot; R3 template v5: applicability-profile/domain-neutral/interface-contract/data-migration/depth-legend; R4 template v6: decision-log/assumption-validation/impact-matrix/observability/open-questions/ai-metadata + optional priority-matrix/version-compat/feature-toggle; R5 system-template v2: PlantUML-fix/system-profile/decision-log/assumption-status/observability/domain-neutral/ai-metadata + wire vào skill)"]
changelog: |
  v1.0.0 — bản gốc: 4 bước (input-gate → đọc PRD/ADR → gap Figma → viết SRS → lưu 05-srs.md).
  v1.6.0 — system-template v2 nâng cấp full parity + wire vào skill (R5):
    SP0 (Cao): diagram Mermaid → PlantUML (System Context §2.2, Module Map §2.5, State §G) — hết trộn engine với feature-template.
    §0 System Applicability Profile (loại hệ thống/greenfield-brownfield/deployment/domains/mode) + Decision Log cấp hệ thống + §2.7 Assumptions có Status/Owner/Deadline.
    §4.9 Observability cấu trúc (Log/Metric/Trace/Dashboard/Alert) + §4.6 Interoperability (sửa numbering nhảy 4.5→4.7) + domain-neutral hoá ví dụ insurance (§E/§G) + §I AI Metadata máy-đọc.
    Wire: workflow frontmatter thêm systemTemplate/systemOutput; Bước 0.0 xác định cấp feature|system; skill giờ sinh cả 2 cấp SRS. Xem REFACTOR-NOTES §R5.
  v1.5.0 — template v6 (proposal triage R4, 10 điểm "lên 10/10" — 9 nhận có điều chỉnh, 1 từ chối):
    §0 Decision Log (quyết định + lý do, tách Change Log). §2.5 Assumption Validation (Status/Owner/Deadline).
    §11.4 Impact Matrix kỹ thuật (API/DB/Cache/Kafka/Batch/Scheduler/Permission/Notification). §8.2 Observability (Log/Metric/Trace/Dashboard/Alert).
    §11.7 Open Questions (câu hỏi nghiệp vụ, tách Gap Analysis). §11.8 AI Metadata block máy-đọc [full] (cộng hưởng Reuse Index §1.7 — feature sau đọc block này thay vì parse văn xuôi).
    Optional [full]: Priority Matrix §1.2 (Technical Complexity = dev-estimate tentative), Version Compatibility §4.5 (conditional), Feature Toggle §9.4.
    TỪ CHỐI #8 Test Data Spec (thuộc sdlc-test-design Phase 5) → thay bằng buộc §7.2 ghi boundary values tường minh. Xem REFACTOR-NOTES §R4.
  v1.4.0 — template v5 (domain-neutral + multi-archetype) + skill nối theo:
    §0 Applicability Profile: khai báo loại feature (UI/backend-process/integration-only/batch), có-UI?, có-state-machine?, có-tích-hợp?, brownfield? → section không áp dụng ghi "N/A — {lý do}" thay vì bảng rỗng.
    Non-UI: §5.2 dùng "Interface Contract" (mẫu 5.2-B: trigger/input/xử lý/output/idempotency/SLA) thay bảng control; §11.1–11.2 Figma = N/A; Bước 2 (Figma) bỏ qua.
    Domain-neutral: bỏ mặc định nghiêng insurance (Policyholder/NTBH) → token {PrimaryActor}/{DomainEntity}/{DomainPlatform}; ví dụ domain chỉ là gợi ý.
    §9.3 Data Migration & Backfill cho archetype brownfield/cắt-chuyển legacy (nguồn cũ/mapping/chiến lược/reconciliation/rollback/downtime).
    Depth legend [core]/[std]/[full] + canonical §1.3↔§11.6, §3.3↔§11.3 (chống trùng lệch). Bước 0 skill suy Applicability Profile; Bước 3 áp N/A + Interface Contract. Xem REFACTOR-NOTES §R3.
  v1.3.0 — external-AI proposal triage R2 ("hướng tới 10/10", 5 điểm — nhận tất cả có điều chỉnh chống bloat):
    #1 Project memory: Bước 1.7 quét `.vsaf/docs/features/*/05-srs.md` + CONTEXT/KNOWLEDGE → "Reuse Index" (entities/API/events/terms) để tái dùng (best-effort, chỉ trích không chép toàn văn).
    #2 Cross-feature consistency: FLAG near-synonym vs Reuse Index (vd InsuranceStatus↔PolicyStatus) — heuristic, chỉ cảnh báo.
    #3 Requirement dependency: §10 RTM thêm cột Depends-on (FR→FR), nối với check circular ở Bước 1.5a.
    #4 Mode draft|standard|full: gate độ sâu Bước 1.5, few-shot, ma trận optional, security checklist — đòn bẩy token; KHÔNG hạ chuẩn structure/guardrails/PlantUML.
    #5 Few-shot: tách file examples/srs-good-bad.md (Good/Bad cho FR/BR/UC/Data Model/NFR), nạp ở standard|full, draft bỏ qua (giữ mục tiêu token của #4). Xem REFACTOR-NOTES §R2.
  v1.2.0 — external-AI proposal triage R1 (12 đề xuất → nhận có chọn lọc, KHÔNG thêm step thừa):
    #12 AI Guardrails: block "Chống bịa" nổi bật đầu workflow (không tự thêm BR/state/API/NFR; thiếu → {{Cần bổ sung}}).
    #9  Ambiguity: quy tắc tránh weasel-word ở Bước 3 (nhanh/hợp lý/nếu cần… → định lượng hoặc {{Cần bổ sung}}).
    #1+#2+#3 gộp thành Bước 1.5 pre-write: FLAG dup/conflict/orphan/missing-actor/circular (KHÔNG tự sửa) + phân loại→định tuyến section + đối chiếu knowledge_model.
    #5 event mapping (trigger→event→consumer) + #6 API resilience (timeout/retry/fallback) → gộp §4 Data Model.
    #7+#8 Security & Privacy → checklist CÓ ĐIỀU KIỆN ở Bước 3 (auth/tiền/PII), không thêm step rỗng.
    #4 CRUD matrix + #10 Risk register → tuỳ chọn ở §11 Appendix.
    #11 Confidence per-section → tín hiệu bàn giao ở Bước 5 (không phải điểm số).
    Từ chối: auto-merge FR (#1), OWASP pass bắt buộc + step 3.5/3.6 riêng (#7), biến confidence thành scoring (#11). Xem REFACTOR-NOTES §R1.
  v1.1.0 — P0+P1 fixes (đồng bộ với cặp skill sdlc-validate-srs):
    P0-a: Bước 3 sửa "10 phần" → 12 sections (0–11) khớp template v4 (hết lệch template khi validate).
    P0-b: chốt DUY NHẤT chuẩn diagram = PlantUML (khớp template thực tế — dòng "Quy tắc viết" gốc ghi Mermaid là sai).
    P1-c: thêm Bước 5 — Self-check 8-dimension trước bàn giao (rút gọn từ sdlc-validate-srs) + gợi ý chạy `validate srs`.
    P1-d: domain-aware — đọc field `domain` trong CONTEXT.md → nạp invariants/knowledge_model từ domain-checklists (best-effort, dùng chung sdlc-validate-srs).
    P1-e: glossary-aware — nạp ubiquitous language của project nếu có, đặt tên entity/UC nhất quán.
    P2: version/changelog/contributors; fallback rõ ràng khi thiếu Figma MCP.
---

Follow the instructions in ./workflow.md.
