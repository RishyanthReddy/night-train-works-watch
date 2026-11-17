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

| Phases 1–3 now authorised, current branch phase1 from d340990; baseline frozen sync and 191 tests passed. | User instruction, git switch -c phase1 exit 0, uv sync --frozen --offline exit 0 and pytest exit 0. | 2026-11-17 |
| Streamlit UI dependency needs transitive certifi; user approved this specific exception to KICKOFF rule 6. | uv pip install --dry-run streamlit output and explicit user reply “Allow certifi for Streamlit”. | 2026-11-17 |

| Phase 1 P1.1–P1.13 implementation and synthetic browser acceptance executed; final council pending. | phase1-evidence.md, phase1-offline-tests.log (295 passed), phase1-phase0-acceptance.log, viewed phase1-accept-*.png. | 2026-11-17 |

| All three Phase1 council R1 reviews completed with matching89 product hashes; changes requested. | Delivered results, saved phase1-council-r1-opus.md / sol.md / grok.md. Parent independently reproduced stale queue and A→B→A in temporary synthetic workspace. | 2026-11-17 |
| Prepared first fixes passed302 tests under OS network denial, six credential variables unset; original89 hashes stayed unchanged during review. | /tmp preparation copy log prepared-offline-tests.log, exit0; source/test copies verified by prepared-files.json before applying. | 2026-11-17 |

| Phase1 council fix round1:309 tests pass with network denied and all six credential variables unset; Phase0 acceptance/format swap exit0. | phase1-r2-offline-tests.log, phase1-r2-phase0-acceptance.log; review.md maps every finding to verification. | 2026-11-17 |
| Fixed UI visually checked with local synthetic inputs, including removed date, scoped count, work records and prominent stale warning; local audit seal verifies. | Viewed phase1-r2-queue/works/evidence/stale/removed-queue/removed-dossier.png; phase1-r2-audit-cli.log. | 2026-11-17 |

| Sol Phase1 council R2 requests whole-leg presence and removed-date boundary fixes;90 hashes matched. Prepared changes in temporary copy leave original product unchanged. | phase1-council-r2-sol.md; /tmp/nightdesk-p1-r2-sol-review/edgecases.log; prepared tests/test_phase1_presence.py, focused20 tests passed exit0. next.md points to copy. | 2026-11-17 |
| Local synthetic loading measured50=0.157s,100=0.490s,200=1.751s; no general performance guarantee inferred. | Parent read-only scaling command, temporary synthetic workspace;90 frozen hashes unchanged. | 2026-11-17 |
| Prepared Sol R2 fixes pass315 tests with OS network denial and six credential variables unset; not applied to reviewed checkout. | phase1-r2-prepared-offline-tests.log, exit0. | 2026-11-17 |

| New continuation goal active; main resume sync/test baseline exit0 with309 tests; no product snapshot mismatches before presence proposal applied. All R2 reviews complete, no pending delegates. | get_goal returned null then create_goal succeeded; current command output; saved Opus/Grok R2 reports and earlier Sol report. | 2026-11-17 |

| Phase1 R2 fixes pass325 tests with OS network denial and all six credentials unset; Phase0 acceptance and actual CLI workflow pass. | phase1-r3-offline-tests.log, phase1-r3-phase0-acceptance.log, phase1-r3-cli.log. | 2026-11-17 |
| Synthetic2x2000 rows with explicit predecessor links import in1.715/3.097s; snapshot2000=.821s, all4000=1.578s, decision1.844s on this host. | phase1-r3-scaling-regressions.log; bounded audit/capture read counters. | 2026-11-17 |
| Whole-leg added/removed dossiers viewed; removed-side review/question/export and partial unknown presence checked in live browser. Further screenshots/selection automation failed; removed-date/group fresh visual check UNKNOWN — not checked. | phase1-r3-removed.png / added.png viewed via view_image, live DOM and synthetic bundle audit; current AppTest covers additional flows. | 2026-11-17 |
| Protected KICKOFF/SPEC/historical fetcher/gitignore hashes match baseline; server stopped, owned browser tab closed. | SHA256 assertions phases1-3-baseline.json and tool completion output. | 2026-11-17 |

| Council R3 launched with exact skill models; no score or approval claimed. All92 frozen product hashes remain unchanged. | orchestrator_capabilities confirmed model IDs/options; delegate_task responses and phase1-council-r3-tasks.json; local SHA256 assertions. | 2026-11-17 |

| Fresh browser visual checks now cover removed-date mismatch and explicit multi-leg selection before opening dossier. T3 preview had no screenshot frames; fallback agent-browser ownsession used and closed. | Viewed phase1-r3-removed-date.png, phase1-r3-group-choice.png, phase1-r3-group-dossier.png; server shutdown exit0. Earlier UNKNOWN visual statement above is superseded by this check. | 2026-11-17 |

| Opus Phase1 R3 approved9/10,325 tests and independent roughlylinear scaling;92 hashes matched. Two nonblocking display/explanation issues recorded. | Delivered review, completed thread read, /tmp/p1r3opus/report.md copied to phase1-council-r3-opus.md; builder inspected desk.py loop/summary. | 2026-11-17 |

| Builder independently reproduced Opus R3 missing-neighbour explanation and duplicate no_run_selected. | PYTHONDONTWRITEBYTECODE=1 sandbox-exec deny network, six variables unset, /tmp/p1r3opus/ws/.venv/bin/python /tmp/p1r3opus/probe/p2.py /tmp/nightdesk-main-r3-adjacent-repro exit0; bb after1 agrees vs before2, unresolved no_run_selected twice. | 2026-11-17 |

| Sol R3 requests changes8/10 for cubic boundary enumeration. Builder reproduced6*n^3 access counts; prepared fix passes13 focused tests and800-leg queue measured1.181s. | phase1-council-r3-sol.md; command outputs, phase1-r3-prepared-evidence.md and temporary queue_benchmark.py. Main product remains frozen. | 2026-11-17 |

| Prepared R3 fixes pass330 tests22.62s with OS network denied and six credentials unset; not yet applied. Main92 frozen hashes still match. | uv run --offline --no-sync pytest -q exit0 in phase1-r3-prepared-path.txt workspace; prepared-files.json SHA256; main snapshot assertions. | 2026-11-17 |

| Prepared adjacency explanation visibly shows unknown in surviving-leg dossier with explicit link; proposal not applied. | Temporary app on8502, own agent-browser fallback, viewed phase1-r3-prepared-adjacent.png; both closed; fixture restored and hashes asserted. | 2026-11-17 |

| Phase2 is now held until user continuation after Phase1 fixes/review/commit. | Latest user instruction in this chat; state/next/TODO checkpoint updated. | 2026-11-17 |

| Local commit preflight: three run-fixture hashes/counts match manifest; existing Git history224 commits/611 distinct blobs has zero private-key/GitHub/OpenAI-key pattern matches; no tracked data or remote. | Python assertions using runs/manifest.json, git rev-list --all/ls-tree/cat-file, git ls-files data/, git remote -v. This is a pattern scan, not a guarantee of absence. Proposal retained in phase1-r3-proposal.json; candidates listed but not staged. | 2026-11-17 |

| All R3 reviews finished; applied exactly two prepared product files, now330 tests22.04s pass with network denial/six credentials unset. Phase0 and full actual CLI integration pass;800-leg queue1.185s. | Completed Grok thread read/report; main phase1-r4-*.log EXIT0; new93-file snapshot diff assertions. Initial extra CLI setup failed from interpreter symlink resolution, then corrected without product edits. | 2026-11-17 |

| Focused R4 council launched with all three exact skill models/options; no score claimed. All93 product hashes match. | delegate_task returned starting/working with completion-wakeup policy; phase1-council-r4-tasks.json and SHA256 assertions. | 2026-11-17 |

| Phase1 task-by-task builder completion audit mapped every P1.1–P1.13 and app/swap requirement to current evidence; R4 approval and local commit remain pending. All14 model class names and four EXIT0 logs asserted;93 hashes match. | phase1-completion-audit.md, AST/model and log/SHA256 assertions. | 2026-11-17 |

| Opus R4 approved9/10;330 tests+46 probes and roughlylinear all-sequence1 queue;93 hashes matched. Mixed-request pre-existing quadratic unknown expansion noted as nonblocking. | Completed thread read; phase1-council-r4-opus.md, /tmp/p1r4opus/multi-r4.log; builder inspected candidate and link gates. | 2026-11-17 |

| Sol R4 approved9/10;330 tests+7 independent checks,1757 selected-leg evaluations preserve findings order; Phase0/CLI pass and93 hashes match. | Completed Sol thread read and saved phase1-council-r4-sol.md from /tmp/nightdesk-p1-r4-sol-0wjknr87/report.md. | 2026-11-17 |

| Mixed-request sequence expansion reproduced in main code without source edits; every emitted boundary entry unknown/unlinked. | phase1-r4-mixed-requests.log EXIT0,25/50 requests and audit payload assertions; no positive inferred. | 2026-11-17 |

| Phase1 R4 unanimously APPROVE9/10; all93 product hashes matched each reviewer. Frozen offline sync exit0 checked45 packages. P1-R4-O1 explicitly deferred nonblocking; local commit pending. | Saved phase1-council-r4-{opus,sol,grok}.md, completed thread reads, uv sync output, review.md decision and hash assertions. | 2026-11-17 |
