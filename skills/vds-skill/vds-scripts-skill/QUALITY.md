# Quality Baseline — vds-scripts-skill

## Version History

| Version | Date | Score | Evaluator | Notes |
|---------|------|-------|-----------|-------|
| 1.0.0 | 2026-03-19 | 3.6/5 | Manual | Initial baseline - needs split |
| 1.1.0 | 2026-03-23 | pending | Manual | Repositioned as platform-routing skill; pending post-refactor review |

## Evaluation Criteria

| Criterion | Weight | Type | Description |
|-----------|--------|------|-------------|
| Accuracy | 40% | Scored 1-5 | Commands and routing guidance are correct |
| Completeness | 25% | Scored 1-5 | Current WHO capabilities are represented through skill text, references, or routing aids |
| Actionability | 20% | Scored 1-5 | Users can quickly choose the correct command family or specialist skill |
| Token Efficiency | 10% | Scored 1-5 | Main skill stays concise and relies on progressive disclosure |
| Schema Validity | 5% | Binary | Skill follows AgentSkills/OpenSkills structure and metadata |

## Current Role

`vds-scripts-skill` is the platform-routing skill for the WHO scripts ecosystem.
It is not the deep specialist runbook for audit workflows or other specialist domains.

## Known Issues

- Post-refactor scoring still needs a fresh baseline run.
- Capability coverage should be validated against the current WHO workspace inventory.
- Generated/root agent surfaces must be synced after the final skill/doc changes land.

## Validation Checklist

- [ ] `SKILL.md` remains concise and activation-oriented
- [ ] references/ covers the broader capability map
- [ ] routing matrix maps common intents to the right skill/command family
- [ ] registry metadata matches the updated role
- [ ] scripts docs and skills docs tell the same ownership story

## Quality Hypotheses

| Date | Hypothesis | Expected | Actual | Score Change |
|------|------------|----------|--------|--------------|
| 2026-03-23 | Shift from command dump to platform-routing + references | Token Efficiency up, Completeness up, clearer routing | pending | pending |
| 2026-03-23 | Add capability index and routing matrix | Completeness 3.5→4.2 | pending | pending |
