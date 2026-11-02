
## [2026-06-14T05:39:28Z] decision_required (decision required)
**Mention:** @QA
**Title:** ATDD fallback review — s4.md

Story: /var/folders/yf/2p3bs3x938l90db4744kt5p40000gn/T/tmp.YXUuIKIz9q/s4.md
Không khớp trigger cứng A/B, nhưng có soft-signal gợi ý rủi ro thiệt hại đo được.
QA Lead áp Fallback rule: fail gây thiệt hại tiền/dữ liệu/uy tín ĐO ĐƯỢC, hoặc có audit requirement?
  Có    → ghi 'atdd: mandatory' vào front-matter story → chạy /bmad-testarch-atdd trước.
  Không → ghi 'atdd: optional' → tiếp tục /bmad-dev-story.

---
