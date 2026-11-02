# pgvector SET hnsw.ef_search Pre-flight Audit (TSK-8.0.3)

**Date**: 2026-04-27
**Purpose**: Verify zero plain `SET hnsw.ef_search` (without `LOCAL`) sites exist in `memory_orchestrator/`. The rule is forward-looking: under v2.15.3 session-mode pooling, plain `SET` is safe (1:1 client:backend), but per-stanza R12 promotion to transaction mode would expose plain `SET` to cross-client GUC leakage. Auditing now keeps the codebase ready for that future-decision without code changes.

## Verdict

✅ **CLEAN — zero current violations**

## Evidence

### Plain `SET hnsw.ef_search`

```bash
$ rg -n 'SET\s+hnsw\.' memory_orchestrator/
(0 matches)
```

### Any reference to `hnsw.ef_search` or bare `ef_search`

```bash
$ rg -n 'hnsw\.ef_search|ef_search' memory_orchestrator/
(0 matches)
```

`memory_orchestrator/` does not currently tune `hnsw.ef_search` at all — neither plain nor `SET LOCAL`. HNSW indexes exist (verified: `CREATE INDEX … USING hnsw` in `memory_orchestrator/alembic/versions/0003_create_memory_vectors_if_missing.py:38-40` and `memory_orchestrator/database/postgres_manager.py:309-310, 357-358`), but search code uses Postgres' default `ef_search=40`.

## Forward enforcement

Even though current code is clean, the rule still applies for future code. Recommended enforcement options:

1. **Lint rule** (preferred — fail-fast at CI time): `ast-grep` rule that flags `SET hnsw.ef_search` *not* preceded by `LOCAL` keyword in `memory_orchestrator/`. Needs careful pattern: only flag SQL strings, not Python identifier `ef_search`.

2. **Integration test (post-R12)**: when any stanza is promoted to `pool_mode=transaction` via per-database override, add a test that sets `hnsw.ef_search` via plain `SET` from one client and asserts the next client on the same backend doesn't observe the leaked value. Catches both authored mistakes and library regressions.

3. **Code review checklist** in `infrastructure-evolution-skill`: when adding any `SET <param>` SQL, verify it's `SET LOCAL` inside a transaction, OR encoded in DSN options / pgbouncer.ini `connect_query`.

For P8 scope, no `connect_query`-embedded default is needed — pgvector's built-in `ef_search=40` is the working default; the rule above keeps future code session-mode-and-transaction-mode-portable.

## Note: pgvector default ef_search performance

Postgres pgvector ships with `ef_search=40` (per pgvector README). This is fine for typical workloads. If memory_orchestrator's vector search ever needs tuning past this, the correct pattern (post-P8) is to issue `SET LOCAL hnsw.ef_search = N` inside the query transaction, never plain `SET`. Confirmed pgvector docs: https://github.com/pgvector/pgvector#querying

## Conclusion

WP-8.0.3 audit closes with zero violations. No code migration needed. Forward-enforcement rule documented (lint or test) for future code; will be added in WP-8.6 (verify-infra-topology +6 checks) or as a separate static-analysis rule.

## References

- Spec: `.gpt-5.4/specs/ecosystem-infrastructure-evolution/design.md` §ADR-INF-13 caveat 1
- pgvector README: https://github.com/pgvector/pgvector
