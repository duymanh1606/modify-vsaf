---
name: sdlc-validate-srs
description: "Validate SRS — 8 dimensions, weighted scoring, parallel agents, GO/NO-GO. Triggers: 'validate srs', 'review srs', 'check srs'."
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

Follow the instructions in ./workflow.md.

**Lite mode:** if invoked with `--lite` (or the SRS header says `Mode: LITE`), validate only the core dimensions — completeness, consistency, testability — and emit a short GO/NO-GO instead of the full 8-dimension weighted scoring. Use lite for small, low-blast-radius features; use the full workflow otherwise.
