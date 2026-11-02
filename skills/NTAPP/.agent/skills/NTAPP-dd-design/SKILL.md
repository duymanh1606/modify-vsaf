---
name: ntapp-dd-design
description: 'Tái dựng (reproduce) mô hình Domain-Driven Design của hệ thống hiện hữu thành một bộ artifact SỐNG, làm Single Source of Truth cho cả business (spec repo) lẫn dev (code repo) — tương tự /ntapp-architecture-design nhưng tập trung vào DDD. Multi-Agent tuần tự (D0 → D1 → D2 → D3 → D4), interview-driven (grill SA dựa trên HLD/Module 0/system-overview, KHÔNG reverse-engineer code bẩn). Có 2 mode: REPRODUCE (default — dựng đầy đủ as-is model → maturity assessment → to-be blueprint → migration roadmap) và REFRESH (`--refresh <bc>` — cập nhật MỘT bounded context khi đổi, re-score maturity, giữ model khỏi drift; gọi từ slice-loop DoD). Output spec-canonical co-locate cạnh HLD/Module 0 (`{planning_artifacts}/domain/`); code chỉ tham chiếu qua header `bc:`/`agg:`. Sử dụng khi người dùng nói "tái dựng DDD", "reproduce domain model", "DDD audit", "đánh giá mức độ DDD", "bounded context map", "thiết kế lại theo domain", "mô hình miền", "what is good / what to change về DDD".'
---

Follow the instructions in ./workflow.md.
