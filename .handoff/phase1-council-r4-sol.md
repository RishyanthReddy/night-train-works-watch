# Phase1 council R4 — focused Codex Sol review

**APPROVE — 9/10.** No material reproducible Phase1 regression found in the two-file delta. P1-R3-S1 is resolved. P1-R3-O1/O2 also pass the focused recheck. No new finding IDs or requested fixes.

## Scope and frozen inputs

Read the current state, decisions, next action, sources/review ledger, all three saved R3 reports, and KICKOFF's Phase1 requirements. Compared the R3/R4 snapshot manifests: exactly `src/nightdesk/desk.py` changed and `tests/test_phase1_queue_scale.py` was added. Diffed desk.py against the saved R3 review copy after verifying that copy's SHA256 against the R3 snapshot.

R4 snapshot: **93/93 SHA256 hashes match before and after; zero mismatches.** All 93 files in the temporary execution copy also match afterward. Snapshot file SHA256: `f72830b4087866dbefc9bf540d8174fb3f72c608f0cdf43d38a295a6abc9bbfc`. Evidence: `hash-before.json`, `hash-after.json`, `desk.diff` beside this report. Checkout HEAD: `d340990773cb70a88584194f571064e8ec1fb06d`, branch `phase1`.

## Why the R3 blocker is fixed

- `desk.py:71` indexes leg sequences/positions and runs by train/date on the operation's context. `_contexts` constructs fresh contexts per queue/dossier operation; there is no module/global cache.
- `desk.py:90` enumerates only the selected revision's sequence-minus-one/plus-one candidates. Sorting by original left/right positions preserves the former nested-loop present-pair order, including duplicated sequence values. The existing `check_boundary` handles each candidate's semantics.
- Independent exact counters on 100/400/800 nonadjacent legs found **200/800/1600 sequence reads across both sides**, with no boundary calls. This replaces the R3 cubic enumeration. The supplied 500-sequential-leg test also passes, asserting exactly `4*(500-1) = 1996` boundary calls across both sides.
- Independent comparison with the hash-verified R3 code passed **1,757 selected-leg evaluations across 150 randomized contexts**, including duplicate sequences, gaps, None and shuffled record order. Findings and order are identical; only the intended unresolved-list normalization is allowed. Six real synthetic-fixture checks also match R3 after that normalization.
- Independent run-index probe: 500 checks over a context of 400 runs read each run's train/date exactly once. Selected ambiguous train/date still raises `select_one_run_capture_for_train_date`; a fresh context containing one candidate selects it independently, including `run_train` override.

Actual queue benchmark, synthetic status-only changes with all sequence values 1, fresh temporary bundles, no works/runs/links:

| Legs per capture | Queue seconds | One dossier seconds |
|---:|---:|---:|
| 200 | 0.299 | 0.371 |
| 400 | 0.613 | 0.739 |
| 800 | 1.149 | 1.393 |

These local measurements are consistent with roughly linear cost for this probe, not a general throughput guarantee or an assertion that workloads with many actual adjacent candidates are linear. Evidence: `queue_scale.py`, `queue-scale.log`, `queue-scale.json`.

## Missing-neighbour and integration semantics

Independent real-fixture tests removed each of the first, middle and last legs separately. Surviving adjacent dossiers emit one/two/one **sourced unknown** `adjacent_leg_not_observed` findings respectively, scoped to the selected capture and rule `border-presence-v1`. No current boundary or cancellation is inferred. Queue/dossier summaries agree. Selecting no link, or a link that excludes the missing train, emits no such finding. Audit records include the presence rule version and the resulting chain verifies. The new supplied regression additionally confirms that the surviving other boundary remains `agrees_on_checked_fields` and `no_run_selected` occurs once.

Fresh actual CLI/API integration passes: unconfirmed-import refusal; complete v1/v2 captures; selected link; A/B/time_unknown and separately unlocated evidence; changed-boundary mismatch; source work/run records; local review, assigned question and Markdown/JSON export; idempotent reimport; v3 stale review/reopened follow-up; reanswer; syn_bad rejection/incompleteness; seal verification; expected cut-tail/edited-event refusals; restored seal verifies.

## Commands and exits

All execution used `/tmp/nightdesk-p1-r4-sol-0wjknr87/workspace` with only frozen code/mappings/test fixtures copied in, an existing `.venv` symlink used for reading, and no environment sync/install. Common wrapper:

```sh
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/nightdesk-p1-r4-sol-0wjknr87/workspace/src:/tmp/nightdesk-p1-r4-sol-0wjknr87/workspace/tests \
  UV_CACHE_DIR=/tmp/nightdesk-p1-r4-sol-0wjknr87/uv-cache \
  TMPDIR=/tmp/nightdesk-p1-r4-sol-0wjknr87 \
  PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=<own tmp>' \
  sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  uv run --offline --no-sync <command>
```

Full pytest used `PYTHONPATH` with only the copied `src`, and basetemp `pytest-temp`; independent pytest used copied `src:tests` and basetemp `independent-temp`. Both are under this report directory.

| Command after wrapper | Exit | Evidence |
|---|---:|---|
| `pytest -q` | 0 | **330 passed in 23.09s**, `pytest.log` |
| `pytest -q -s /tmp/nightdesk-p1-r4-sol-0wjknr87/test_independent.py` | 0 | **7 passed in 2.12s**, `independent.log` |
| `python tests/phase0_acceptance.py` | 0 | Six steps, alternate mapping equivalence, JSON/XLSX, merged-header refusal/flatten/ingest; `phase0.log` |
| `python /tmp/nightdesk-p1-r4-sol-0wjknr87/integration.py` | 0 | `INTEGRATION PASS`, `integration.log`; credential absence asserted and loopback denied with errno 1 |
| `python /tmp/nightdesk-p1-r4-sol-0wjknr87/queue_scale.py` | 0 | Actual 200/400/800-leg queue/dossier, `queue-scale.log` |
| Initial/final snapshot and copy assertions | 0 | All 93 match, `hash-before.json` / `hash-after.json` |

One initial independent-test run exited 1 because its comparator required R3's old unresolved-list order (`unlinked, no_run_selected`). R4 intentionally sorts/deduplicates that list. Normalized only that field in the temporary comparator, leaving finding order comparison exact; all seven tests then passed. Initial evidence retained in `independent-initial.log`. No product fix was needed.

## Read-only result and limits

No checkout/handoff edits, checkout `data/` reads, environment rewrite, delegation, network fetch, commit or push by this reviewer. Only temporary synthetic copies/probes/logs/report were written. Git status acquired one additional untracked path during the review, `.handoff/phase1-completion-audit.md`; this reviewer did not create/read/edit it. All tracked status lines and 93 frozen product hashes stayed unchanged. Before/after status retained beside this report.

This is a focused R4 delta/integration review, not another audit of unchanged features. No new browser or visual verification is claimed. The approved certifi exception is accepted. Phase2+ excluded. Parent should save the report/ledger result, finish the Phase1 checkpoint, then **STOP before Phase2**. No fix applied; review stops here.
