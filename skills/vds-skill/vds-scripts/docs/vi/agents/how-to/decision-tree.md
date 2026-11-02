<!-- diátaxis: how-to -->
<!-- TODO: translate — Vietnamese translation needed -->

# Tôi Đang Viết Loại Tài Liệu Nào?

> **Lưu ý**: Tài liệu này cần được dịch sang tiếng Việt.
> **Note**: This document needs Vietnamese translation. The English version is canonical.
> English source: [docs/agents/how-to/decision-tree.md](../how-to/decision-tree.md)

---

## Phương Pháp Một Câu Hỏi

*(English content below — TODO: translate)*

# What Kind of Doc Am I Writing?

Quick decision tree for choosing the correct Diátaxis quadrant.

---

## The One-Question Method

Start at the top and answer each question. The first "YES" tells you the quadrant.

```
Q1: Is this for someone who has NEVER done this before?
     → YES → TUTORIAL
     → NO → Q2

Q2: Is this a step-by-step recipe for a SPECIFIC task?
     → YES → HOW-TO GUIDE
     → NO → Q3

Q3: Is this listing exact flags, contracts, or API surfaces?
     → YES → REFERENCE
     → NO → Q4

Q4: Is this explaining WHY something works or background concepts?
     → YES → EXPLANATION
     → NO → Re-examine your scope. You may be mixing quadrants.
```

---

## Examples by Quadrant

| Doc Title | Quadrant | Why |
|-----------|----------|-----|
| "Day 0: Install the WHO toolchain" | Tutorial | First-time learner |
| "How to add a new skill to the catalog" | How-to | Specific task |
| `vds-cli --help` auto-generated docs | Reference | Exact flags |
| "Why we use Diátaxis for doc architecture" | Explanation | Background concept |

---

## Common Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Tutorial sneaks in unrelated tasks | Split to a separate How-to |
| Reference doc tells a story | Delete narrative; keep only facts |
| How-to explains the "why" | Move "why" to a linked Explanation doc |
| Explanation gives step-by-step commands | Move commands to a How-to |

---

## Header Convention

Every `.md` in `docs/agents/` should include its quadrant as the very first line:

```markdown
<!-- diátaxis: tutorial -->
# Title
```

Valid values: `tutorial`, `how-to`, `reference`, `explanation`
