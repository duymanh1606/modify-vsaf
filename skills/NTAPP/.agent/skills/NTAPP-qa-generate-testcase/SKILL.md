---
name: ntapp-qa-generate-testcase
description: 'Sinh kịch bản kiểm thử E2E automation-ready cho một SLICE HOẶC một đơn vị đứng riêng (HUB/WGT/SCR/MPF… — tính năng không gom vào SLICE) theo School B: shift-left → risk-based allocation → triple-emit. Tập trung trải nghiệm End-to-End từ UI xuống Backend, phối hợp các units (FE/BE/downstream). Input nhận `{id}`: nếu có file SLICE `{slices_root}/{id}-*.md` → lane SLICE (nhiều unit); nếu không nhưng có `{id}_detailed_design.md` → lane unit-đơn. Output 3 artifact tại `{qa_artifacts}/{id}/`: `{id}_testspec.feature` (Gherkin canonical → automation), `{id}_detailed_test_manual_testcase.md` (bảng 11 cột — QA ký + qa-robot parse), `{id}_fixtures.yaml` (data máy-đọc). Bridge sang `/ntapp-qa-robot`. Alias lệnh: `/ntapp_qa_generate_testcase`. Sử dụng khi người dùng nói "sinh testcase slice", "test E2E cho slice", "generate slice qa", "viết KBKT cho một slice", "sinh testcase cho HUB/WGT", "test cho tính năng đứng riêng".'
---

# NTAPP QA Generate Slice / Unit Testcase (E2E + Automation-Ready)

Sinh kịch bản kiểm thử E2E cho một **SLICE** (nhiều unit) hoặc một **đơn vị đứng riêng** (HUB/WGT/SCR/MPF — tính năng không gom vào SLICE) với **triple-emit** (`.feature` + markdown view + `fixtures.yaml`), risk-based allocation và shift-left gate — output dùng trực tiếp cho automation qua `/ntapp-qa-robot`.

**Hai lane input** (auto-detect ở Step 00 theo `{id}`): `slice` (có file SLICE tương ứng → phối hợp nhiều unit + xếp thứ tự E2E) · `unit` (chỉ có `{id}_detailed_design.md` → coi như "slice một unit", bỏ bước xếp thứ tự liên-unit, giữ nguyên triple-emit + risk allocation). Mọi biến định danh dùng chung **một khóa `{id}`** = ID đầy đủ (vd `SLICE-06`, `WGT-SIDEBAR`, `HUB-01`).

**Hai bề mặt test** (`surface_type`, quyết định ở **cấp test-target** tại Step 00 — KHÔNG per-unit):
- `ui` — **target có ≥1 màn (`SCR-*`/`WGT-*`)** → E2E **tích hợp đi qua màn** (per-screen loop, oracle UI-first). **Mọi unit BE (HUB/MPF/INT/PMT-EXT…) là BACKEND của màn**, verify bằng oracle API/DB nhúng trong testcase của màn (Background — như cũ). BE **KHÔNG** tách thành bề mặt riêng, KHÔNG đứng riêng trong thứ tự E2E. → **hành vi sinh testcase SLICE giữ nguyên như trước khi có nhánh service.**
- `service` — **target KHÔNG có màn nào** (unit `HUB/MPF/INT` đứng riêng, hoặc slice thuần BE) → per-operation loop, oracle API-first `api/db/msg/log`, test-design từ error catalog / state machine / idempotency / resilience ([service_surface_rules.md](./principles/service_surface_rules.md)). KHÔNG cần `ui_schema`; qa-robot sinh `RequestsLibrary` vẫn theo POM.

→ **"Không có giao diện thì dùng được không": CÓ** — chạy skill trên chính unit BE đó (target no-UI → `service`). **Có giao diện thì tích hợp đi qua màn như cũ.** 1 lần chạy = 1 target = 1 `surface_type` (không trộn).

**3 lane chạy** (`run_mode`, xem [run_mode_rules.md](./principles/run_mode_rules.md)): `full` (default, 4 HITL gate, governance) · `batch` (2 gate, auto-proceed, lặp nhanh) · `delta` (entry tắt khi 3 artifact đã tồn tại — chỉ patch phần đổi). Mọi lane dùng **Context Ledger** load-once để scoped-reload, chống drift trên slice lớn. Iron Rules + Sync Invariant enforce ở mọi lane.

Đọc đầy đủ và tuân theo: `./workflow.md`
