---
name: ntapp-system-overview
description: 'Sinh tài liệu mô tả hệ thống (per-repo overview + cross-system contract matrix) cho multi-repo workspace. Hai mode, cùng output vào `NTAPP-output/Stage_1_Discovery/system_overview/`: (1) `--mode baseline` (DEFAULT — chạy khi user không nêu mode) — 10 sections + Section 0 Service Identity + Cross-System Contract Match Matrix + interactive Q&A loop với SA + dual-write archive, dùng làm input cho Stage 2 Architecture (HLD); (2) `--mode overview` (opt-in, phải gõ flag) — chỉ 10 sections prose-friendly per repo, không Section 0 / không Contract Matrix / không Q&A, dùng cho onboarding / code review / share BA-dev. Auto-detect sibling code repos qua marker file (`package.json` / `pom.xml` / `go.mod` / ...). Sử dụng khi user nói "tạo overview cho các repo", "system overview", "service overview doc", "scan brownfield", "baseline hệ thống", "tài liệu kỹ thuật service", "FE BE contract", "contract drift discovery".'
---

Follow the instructions in ./workflow.md.
