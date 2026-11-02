# SonarQube Standard — `sonar-viettel`

> **Single source of truth** for the SDLC SonarQube standard. Referenced by both the
> **code** phases (`/sdlc-implement`, `/sdlc-hotfix-implement`) and the **review** phases
> (`/sdlc-review`, `/sdlc-hotfix-review`). Code what passes here; review re-checks the same numbers.
>
> Deployed location: `.claude/skills/_shared/sdlc/sonar-viettel/`
>
> Files in this folder:
> - `sonar-viettel-profile.xml` — the 357-rule Java **Quality Profile** (which checks run).
> - `sonar-viettel-gate.json` — the **Quality Gate** (pass/fail conditions), machine-importable.
> - `quality-gate.md` — this human/agent-readable summary (transcribed verbatim from the Viettel SonarQube UI).

A condition **FAILS** the gate when the metric crosses the operator/value shown. Ratings: A=1, B=2, C=3, D=4, E=5.

> The two tables below are a **human-readable rendering of `sonar-viettel-gate.json`** — that JSON is the machine-importable source of truth for the gate. If they ever disagree, the JSON wins; fix the table.

## Quality Gate — Conditions on New Code

| Metric | Threshold (PASS) | Fails when |
|--------|------------------|------------|
| Issues | = 0 | > 0 |
| Blocker Issues | = 0 | > 0 |
| Critical Issues | = 0 | > 0 |
| Major Issues | = 0 | > 0 |
| Code Smells | ≤ 20 | > 20 |
| Vulnerabilities | = 0 | > 0 |
| Security Hotspots Reviewed | = 100% | < 100% |
| Coverage | ≥ 0% | < 0.0% (gate effectively **disabled**; TDD still mandatory) |
| Duplicated Lines (%) | ≤ 45% | > 45.0% |
| Maintainability Rating | ≥ A | worse than A |
| Reliability Rating | ≥ A | worse than A |
| Security Rating | ≥ A | worse than A |

## Quality Gate — Conditions on Overall Code

| Metric | Threshold (PASS) | Fails when |
|--------|------------------|------------|
| Blocker Issues | = 0 | > 0 |
| Critical Issues | = 0 | > 0 |
| Major Issues | = 0 | > 0 |
| Bugs | = 0 | > 0 |
| Code Smells | ≤ 50 | > 50 |
| Vulnerabilities | = 0 | > 0 |
| Duplicated Lines (%) | ≤ 45% | > 45.0% |
| Maintainability Rating | ≥ A | worse than A |
| Reliability Rating | ≥ A | worse than A |
| Security Rating | ≥ A | worse than A |

## Rule Parameters

⚠️ **The 357 rules and their parameters live authoritatively in `sonar-viettel-profile.xml`. Do NOT hard-code rule values here — they drift.** When you need the parametrised rules (param thresholds, naming regexes, credential words), derive them live from the profile:

```bash
node -e '
const fs=require("fs");
const x=fs.readFileSync("sonar-viettel-profile.xml","utf8");
const re=/<key>(S\d+)<\/key><type>([^<]*)<\/type><priority>([^<]*)<\/priority><parameters>(.*?)<\/parameters>/g;
let m; while((m=re.exec(x))){
  const ps=[...m[4].matchAll(/<key>([^<]+)<\/key><value>([^<]*)<\/value>/g)].map(p=>p[1]+"="+p[2]).join(", ");
  console.log(`${m[1]} [${m[3]}/${m[2]}]: ${ps}`);
}'
```

Run from this folder (`.claude/skills/_shared/sdlc/sonar-viettel/`). It prints every rule that carries a threshold/format — e.g. `S107` (max params), `S3776` (cognitive complexity), `S110` (inheritance depth), `S1479` (switch cases), `S1192` (literal duplication), `S2068` (credential words), and the `S100/S101/S115/S116/S117` naming regexes. **The XML output is the source of truth; the rule names here are only signposts.**

## How to Apply

- **If the project has SonarQube:** import `sonar-viettel-profile.xml` as the Quality Profile, recreate the gate from `sonar-viettel-gate.json`, then run `sonar-scanner` and read the gate result.
- **If the project has no SonarQube:** review the changed code manually against the tables above plus the rule parameters — scan for injection, hardcoded secrets, null dereference, resource leaks, concurrency issues, duplicated blocks, naming/SOLID violations.

## Phase-specific overrides

- **Hotfix (`/sdlc-hotfix-implement`, `/sdlc-hotfix-review`):** apply the **New Code** conditions on changed files only, but tighten **Code Smells (new) = 0** — a surgical 1–3 line fix has no excuse to introduce a smell.
