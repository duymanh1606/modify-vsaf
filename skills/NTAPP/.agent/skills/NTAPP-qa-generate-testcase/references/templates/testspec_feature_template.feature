# =====================================================================
# TESTSPEC FEATURE TEMPLATE — Canonical machine-readable artifact
# File: {id}_testspec.feature   ({id} = ID đầy đủ SLICE/unit, vd SLICE-06 / WGT-SIDEBAR)
# Hợp đồng: ../../principles/automation_contract_rules.md (tag dictionary §2)
# Sync Invariant: mỗi Scenario ⇔ 1 dòng markdown ⇔ cùng @id.
# Selector KHÔNG nằm ở đây (qa-robot lấy từ ui_schema). Chỉ dùng Nhãn UI.
# =====================================================================

@{id}
Feature: {Tên SLICE/Unit} — E2E system test
  ID: {id}
  Coverage gate: 100% luồng E2E qua các unit FE/BE (theo iron_rules R4)
  Generated: {timestamp}

  # ---- 1 Background cho toàn slice/unit (precondition + [Nav] units) ----
  Background:
    Given hệ thống ở môi trường "Staging" mạng ổn định
    And user đã đăng nhập với quyền theo luồng E2E

  # =================================================================
  # MÀN HÌNH ACTION {STT}: {Tên màn} ({unit_id})
  # =================================================================

  # ---- KHỐI 1: GIAO DIỆN (UI) ----
  @scr:{SCR-UNIT} @id:KB-{id}-01 @block:ui @tech:BVA @rule:textbox-base
  @risk:P1 @exec:automate @target:robot @oracle:ui
  Scenario: Email thiếu ký tự @ bị chặn (validation BVA)
    Given user ở màn "{Tên màn}"
    When user nhập "{Nhãn trường Email}" = "<email_invalid_no_at>"
    And user bấm "{Nhãn nút Submit}"
    Then UI: trường "{Nhãn trường Email}" viền đỏ, hiện lỗi "Email không đúng định dạng"

  # ---- KHỐI 2: CHỨC NĂNG (FUNCTIONAL / E2E) ----
  @scr:{SCR-UNIT} @id:KB-{id}-02 @block:functional @tech:EP @rule:save-button
  @risk:P0 @exec:automate @target:robot @oracle:ui @oracle:api @oracle:db
  Scenario: Tạo mới thành công toàn luồng UI → API → DB
    Given user ở màn "{Tên màn}"
    When user nhập dữ liệu hợp lệ từ fixture "<valid_compose_payload>"
    And user bấm "{Nhãn nút Lưu}"
    Then UI: chuyển sang màn "{Màn đích}", bản ghi mới ở dòng đầu danh sách
    And API: POST "{endpoint}" trả HTTP 200
    And DB: bảng "composite_requests" insert 1 bản ghi status "PENDING"

  # BVA/EP nhiều giá trị cùng-logic → MỖI case 1 Scenario riêng (CẤM Scenario Outline/Examples).
  # Chống trùng-lặp: giá trị input để ở fixtures.yaml (mỗi case 1 dataset), thân scenario chỉ khác giá trị nạp.
  @scr:{SCR-UNIT} @id:KB-{id}-03 @block:functional @tech:BVA @rule:maxlength
  @risk:P1 @exec:automate @target:robot @oracle:ui @oracle:api
  Scenario: Biên maxlength "{Nhãn trường}" = 255 (giá trị lớn nhất hợp lệ)
    Given user ở màn "{Tên màn}"
    When user nhập "{Nhãn trường}" từ fixture "<maxlen_255>"
    And user bấm "{Nhãn nút Lưu}"
    Then UI: lưu thành công
    And API: trả HTTP 200

  @scr:{SCR-UNIT} @id:KB-{id}-04 @block:functional @tech:BVA @rule:maxlength
  @risk:P1 @exec:automate @target:robot @oracle:ui @oracle:api
  Scenario: Biên maxlength "{Nhãn trường}" = 256 (vượt giới hạn)
    Given user ở màn "{Tên màn}"
    When user nhập "{Nhãn trường}" từ fixture "<maxlen_256>"
    And user bấm "{Nhãn nút Lưu}"
    Then UI: chặn, báo "vượt độ dài"
    And API: trả HTTP 400

  # ---- KHỐI 3: PHÂN QUYỀN & ATTT (SECURITY) ----
  @scr:{SCR-UNIT} @id:KB-{id}-05 @block:security @tech:EG @rule:security-input
  @risk:P0 @exec:automate @target:robot @oracle:api
  Scenario: Chặn IDOR — thao tác tài nguyên user khác
    Given có token của "User A" và một resource_id thuộc "User B"
    When gửi API request xem chi tiết resource_id bằng token User A
    Then API: trả HTTP 403 Forbidden

  # =================================================================
  # (Lặp lại khối Màn hình Action cho từng unit [Action] tiếp theo,
  #  ID @id chạy liên tục, không nhảy cóc — theo iron_rules R8)
  # =================================================================

  # =================================================================
  # BIẾN THỂ SERVICE (no-UI): dùng @svc thay @scr, oracle API/DB/MSG/Log
  # (không @oracle:ui). Given/When/Then là gọi request + quan sát
  # side-effect, KHÔNG "user ở màn". Xem service_surface_rules.md.
  # =================================================================
  # OPERATION {STT}: {METHOD /path} ({unit_id})

  # ---- KHỐI 2: NGHIỆP VỤ & E2E ----
  @svc:{HUB-UNIT} @id:KB-{id}-10 @block:functional @tech:EG @rule:backend-resilience
  @risk:P0 @exec:automate @target:robot @oracle:api @oracle:db @oracle:msg
  Scenario: Idempotency — request trùng key chỉ tạo 1 giao dịch
    Given có payload hợp lệ từ fixture "<valid_transfer>" và một "Idempotency-Key"
    When gửi request tạo giao dịch lần 1
    And gửi lại request với cùng "Idempotency-Key"
    Then API: lần 2 trả HTTP 200 cùng "transferId" lần 1
    And DB: bảng "transfers" chỉ có 1 bản ghi
    And MSG: chỉ 1 event "transfer.created" được phát
