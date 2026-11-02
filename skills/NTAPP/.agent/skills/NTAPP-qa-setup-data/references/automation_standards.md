# Robot Automation Standards (Facade — scope: Test Data Setup)

Skill này (`ntapp-qa-setup-data`) chỉ lo thiết kế **Dữ liệu Mồi (Test Data) Setup/Teardown**, không sinh Page Object / locator / test suite. Tiêu chuẩn áp dụng:

1. **Robot Rules:** [auto_robot_rules.md](./auto_robot_rules.md) — đặc biệt §2 Test Data Management (isolation bằng timestamp/UUID, clean-state) và §4 Anti-Patterns (Zero-Fabrication, cấm hardcode dữ liệu rác).

*(Các chuẩn Coding Convention / Framework Structure / Locator Strategy thuộc khâu sinh code automation — xem skill `ntapp-qa-robot`, không nằm trong scope setup-data.)*
