# Phase 0 completion evidence

Product commit: d220f620748737ba5709bc161ca63b2cd5750cb6 (phase0). Baseline fedda2c preserved.
Plan: KICKOFF.md section 0 and Phase 0 P0.1–P0.8, in order; optional P0.9 skipped. No Phase 1 implementation or remote action.

| Requirement | Authoritative evidence |
|---|---|
| Initial setup/test first | phase0-direct-evidence.md and actual tool output: uv sync --frozen exit 0; pytest exit 0, 111 passed in pre-existing partial work. |
| P0.1 protect data/SPEC | Baseline fedda2c; whole data/ ignored, SPEC first line superseded; tail hash preserved. |
| P0.2 CLI/config | cli.py/config.py; help/config tests and actual help exit 0. |
| P0.3 canonical models/audit | model.py/audit.py; schema, append-only, isolation, batch and concurrency tests. Chain/seal deferred. |
| P0.4 sniff CSV/XLSX/JSON | table.py/sniff.py; unit tests and real CLI logs for all formats. |
| P0.5 mappings/gates/flatten/confirm | mapping.py/gates.py/flatten.py; unconfirmed and changed-hash refusals, scalar gates, rejects and live flatten path. |
| P0.6 mappings | admin_v1.yaml/admin_alt.yaml; both synthetic, confirmed before ingest. |
| P0.7 comparison/export | generic.py/export.py; source-linked changed/added/unchanged/unknown identity, escaped Markdown/JSON; exported files read and inspected. |
| P0.8 fixtures | fixtures/admin README and three CSVs; v1/alt canonical equivalence and explicit synthetic labels. |
| All six acceptance steps | phase0-acceptance-r2.log retained workspace; phase0-acceptance-isolated-r2.log fresh synthetic workspace, both exit 0. |
| No keys/network | Same CLI stdout under OS deny-network profile; loopback returns EPERM; phase0-tests-r2.log: 191 passed, exit 0. |
| Independent council | council-r1-*.md then council-r2-*.md; Opus 6.5→9, Sol 8→9. Both APPROVE same 34-file snapshot. DeepSeek waived by user. |
| Findings resolved | review.md fixed rows; targeted regressions and exact snapshot unchanged after approval. |
| Allowed paths / user edits | Explicit staged whitelist, token scan clean; no data/research/instruction files staged. Original local research archived/preserved. |
| Local commit | git show hashes match phase0-council-r2-snapshot.json for all 34 files; no tracked data or remotes. |
| TODO/handoff | TODO.md P0 tasks checked; state/decisions/next/sources current, older research memory preserved under history/. |
| Swap check | A new local input plus a confirmed mapping YAML changes columns/units without core code; explicit flatten for multi-row/merged headers. Unsupported source logic gets an adapter later. |
| Stop boundary | No Phase 1 modules/UI/model calls/fetcher added. Later tasks remain unchecked in TODO. |

Known nonblocking limits: no crash-atomic capture/audit recovery; extremely deep or oversized native JSON may fail a whole file safely with a low-level error. No tamper-proofing, delay prediction or official approval is claimed.
Historical scripts/fetch_public.py is untouched and outside the Phase 0 package; requests was removed from Phase 0 due transitive certifi licence metadata.

Local synthetic example output: sniff 4 rows / 6 columns; v1 accepted=4 rejected=0; v2 accepted=5 rejected=1; row=7 field=duration_s reason=invalid_number; changed=2 added=1 unchanged=2 only_in_old=0; alt accepted=4 and canonical fields/extra match v1.
