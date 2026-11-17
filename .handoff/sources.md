# Sources — verified facts only

| Fact | Verified by | When |
|---|---|---|
| User authorised Phase 0 only, TODO, council after completion, local commit; no remote/push or API keys. | Current chat instructions and KICKOFF.md Phase 0. | 2026-11-17 |
| User waived unavailable DeepSeek and chose Opus/Sol. | Cursor weekly-usage failure plus explicit user reply “Finish with Opus and Sol”. | 2026-11-17 |
| Baseline exists on phase0 at fedda2c. | git show --stat --oneline HEAD and git branch --show-current. | 2026-11-17 |
| Initial fresh setup/test commands exited 0; pytest collected/passed 111. | Actual tool output; phase0-direct-evidence.md. Earlier zero-test history is archived, not the current result. | 2026-11-17 |
| P0.1–P0.8 product and synthetic fixtures are present; P0.9 absent/skipped. | TODO.md, current src/tests/mappings and scope inspection. | 2026-11-17 |
| Council round 1: Opus 6.5/10 and Sol 8/10, both changes requested. | Completed T3 task results saved as council-r1-opus.md / council-r1-sol.md. | 2026-11-17 |
| All round 1 findings have fixes with passing targeted regressions. | review.md; tests/test_phase0_regressions.py, test_mapping.py, test_generic.py. Round 2 approved by both reviewers. | 2026-11-17 |
| 191 tests pass with keys unset and networking denied. | phase0-tests-r2.log; sandbox-exec deny network*, six env variables unset; exit 0. | 2026-11-17 |
| All six CLI acceptance steps pass; ordinary/denied stdout equal. | phase0-acceptance-isolated-r2.log and retained-workspace phase0-acceptance-r2.log, exit 0. | 2026-11-17 |
| JSON/XLSX sniff+ingest and merged headers -> flatten -> ingest pass without networking. | Same acceptance log, real subprocess commands and exit codes. | 2026-11-17 |
| Synthetic audit ingest measured 3000 rows 0.174s, 6000 rows 0.316s; no rejected rows. | phase0-performance-r2.log. This is a local synthetic measurement, not a general throughput claim. | 2026-11-17 |
| Audit concurrent writers allocate unique sequences. | Four-process 80-event regression test passed in the 191-test run. | 2026-11-17 |
| requests dependency removed; certifi MPL-2.0 and four other network packages removed from lock/environment. | Installed metadata inspection, uv lock output, git diff uv.lock and uv sync --frozen --offline exit 0. | 2026-11-17 |
| KICKOFF, historical script, empty package initializer and SPEC tail remain unchanged by this work. | phase0-direct-baseline.json hashes, scope commands. AGENTS/CLAUDE hashes changed during the session; coordinator did not write/stage them. | 2026-11-17 |
| Real operational claims are outside Phase 0; tests use synthetic inputs. | fixtures/admin/README.md, fixture/mapping contents and no fetch/model code in src. | 2026-11-17 |
| Council round 2 approved 9/10 each with 34 matching hashes and no remaining Phase 0 blockers. | council-r2-opus.md / council-r2-sol.md, completed T3 task results. | 2026-11-17 |
| Approved product committed locally as d220f620748737ba5709bc161ca63b2cd5750cb6; all 34 reviewed Git blobs and working files match; no tracked data or remotes. | git commit exit 0, SHA256 assertions against git show, git ls-files data/ empty, git remote -v empty. | 2026-11-17 |

Earlier research sources are preserved locally at history/20261117-before-phase0-closure/sources.md. They are not revalidated by the Phase 0 build or silently committed.
