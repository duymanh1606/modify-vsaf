# reachability_check.py — endpoint reachability engine

Project-agnostic engine that proves every HTTP call a **consumer** makes resolves
to a route a **provider** actually serves, across one or more hops
(`consumer -> proxy/BFF -> service`). It reconciles at the `(method, path)` level,
so it catches the two feature-integration failure modes:

| Status | Meaning |
|---|---|
| `404` | no provider route serves this path at all |
| `405` | a route serves this path, but under a different HTTP verb |

Used by two NTAPP workflow gates as the single shared implementation:

- **slice-loop `slice-integration`** — raises seam verification from atom-level
  ("provider exists") to endpoint-level ("this method+path is served"), then
  escalate-blocks when a *Done* provider is missing the endpoint a consumer calls.
- **staging-deploy `feature-integration-smoke`** — static tier: reconcile the whole
  feature before staging; block on any unresolved `(method, path)`.

Nothing project-specific lives in the script. Directories and adapters come from
config; the script only ships **reference adapters** and the matching engine.

## Configure — `.bmm-config.yaml` `reachability:` block

Add a `reachability:` block to the project's `.bmm-config.yaml`. `hops` is an
ordered list; each hop names a consumer dir + adapter and a provider dir + adapter.
Relative dirs resolve against the config file's directory (override with `--root`).

```yaml
reachability:
  hops:
    # hop 1 — Angular frontend -> Spring BFF
    - consumer_dir: "web/fe"
      consumer_adapter: angular-httpclient
      provider_dir: "services/bff"
      provider_adapter: spring-mapping
    # hop 2 — BFF outbound adapter package -> core service
    - consumer_dir: "services/bff/src/main/java/com/acme/adapter"
      consumer_adapter: spring-restclient
      provider_dir: "services/core"
      provider_adapter: spring-mapping
    # optional per-hop label used in the report table
    - label: "fe->gateway"
      consumer_dir: "web/fe"
      consumer_adapter: angular-httpclient
      provider_dir: "api/openapi"
      provider_adapter: openapi
```

Notes:
- Use **one key per line** (standard YAML). No external YAML library is required to
  read this block — the script parses this small subset itself.
- Scope `consumer_dir` narrowly (e.g. the outbound-adapter package for
  `spring-restclient`) to keep the heuristic adapters precise.

## Run

```bash
# feature-wide, from config (the staging gate uses this)
python3 scripts/reachability_check.py --config .bmm-config.yaml

# ad-hoc single hop (no config) — handy for slice-integration targeting one provider
python3 scripts/reachability_check.py \
    --consumer-dir web/fe --consumer-adapter angular-httpclient \
    --provider-dir services/bff --provider-adapter spring-mapping

# list registered adapters
python3 scripts/reachability_check.py --list-adapters
```

Exit codes: `0` all resolved (or nothing configured), `1` unresolved calls found,
`2` usage / config error (unknown adapter, missing args). The report prints a table
of `HOP | METHOD | STATUS | PATH | SOURCE` for every unresolved call.

## Reference adapters

| Name | Kind | Extracts |
|---|---|---|
| `angular-httpclient` | consumer | `http*.get/post/put/delete/patch('...')` in `*.ts` |
| `spring-restclient` | consumer | `RestTemplate` (`getForObject`, `exchange(url, HttpMethod.X)`, ...), `WebClient` (`.get().uri('...')`), `@FeignClient` interface mappings in `*.java` |
| `spring-mapping` | provider | `@GetMapping/@PostMapping/...` + class-level `@RequestMapping` prefix + `@RequestMapping(method=RequestMethod.X)` in `*.java` |
| `openapi` | provider | `paths` section of an `*openapi*` / `*swagger*` `.json` (or `.yaml`/`.yml` if PyYAML is installed) |

The reference adapters are deliberately regex-light heuristics, not full parsers.
They cover the common idioms; edge cases (dynamic URL concatenation, env-prefixed
base URLs like `${environment.apiUrl}/...`) may need a custom adapter.

## Path normalisation

Before comparison the matcher normalises both sides so params line up:
`{id}` / `:id` / `${x}` -> `*`, scheme+authority and query strings are stripped,
duplicate slashes collapse, a leading slash is ensured. So `GET /a/{id}` (consumer)
matches `GET /a/*` (provider), while `POST /a/{id}` is a `405` and `GET /b` a `404`.

## Register a new adapter

Adapters are plain functions kept in two registries in `reachability_check.py`:

- **Consumer** adapter: `dir -> set[Call]` where `Call(method, path, source)`.
  `source` is any string used in the report (usually a file path). Register in
  `CONSUMER_ADAPTERS`.
- **Provider** adapter: `dir -> set[(METHOD, normalized_path)]`. Register in
  `PROVIDER_ADAPTERS`.

Always run raw paths through `normalize_path(...)` so matching is consistent.
Example:

```python
def extract_express_routes(directory):
    routes = set()
    for path in _iter_files(directory, {".js", ".ts"}):
        for m in re.finditer(r"\.(get|post|put|delete|patch)\(\s*(['\"])(.*?)\2",
                             _read(path)):
            routes.add((m.group(1).upper(), normalize_path(m.group(3))))
    return routes

PROVIDER_ADAPTERS["express-router"] = extract_express_routes
```

Then reference `express-router` as a `provider_adapter` in a hop. Unknown adapter
names raise `UnknownAdapterError`, so typos fail loudly rather than passing silently.
