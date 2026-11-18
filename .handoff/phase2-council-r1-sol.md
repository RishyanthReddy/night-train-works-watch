# Phase 2 council R1 — Codex Sol independent read-only review

**Verdict: CHANGES REQUESTED. Score: 8/10.**

Two medium findings in the new Phase 2 code. No new high-severity correctness/security failure was reproduced. P2.8 remains skipped, Phase 3 excluded, and accepted Phase 1 P1-R6-O1 is not reopened.

## Freeze and scope

- Checkout: `/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a`.
- Branch `phase2`; `git rev-parse HEAD` returned `1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e`.
- All **127** entries in `.handoff/phase2-council-r1-snapshot.json` matched SHA256 before review and after all checks. The isolated copy also still matches all 127 product hashes. Evidence: `freeze-before.txt`, `freeze-after.txt` alongside this report.
- Reviewed the tracked Phase 2 product delta and new product modules, mappings, fixtures and tests, using the frozen inventory. Read KICKOFF section 0, product/swap rules, canonical records, time rules, gates, model policy and P2.1–P2.7; builder evidence, state, decisions, next, sources, TODO and review ledger.
- All code execution used the independent `copy/` beside this report with checkout `.venv` symlinked for existing dependencies, `--no-sync`, and `PYTHONPATH` selecting `copy/src`. No checkout `data/` was read. No checkout/product/data/.handoff files were written by this reviewer. No delegation, commit, push, downloaded-code execution, live model call, real credential access or spend.
- Five existing parent screenshots were actually viewed: different, clock, partial, refusal and poison. They show the stated unknown/refusal results. Independent UI automation below used production `main()` through Streamlit AppTest; no new live-browser session was run.

## Findings

### P2-R1-S1 — medium — Malformed proposal JSON escapes the refusal boundary and crashes the UI

**Primary location:** `src/nightdesk/ui/app.py:229–231`, especially line 230. Related new-code boundaries: `src/nightdesk/llm/cache.py:51`, `src/nightdesk/llm/client.py:47–50,74–82`.

**Reproduction (all synthetic, network denied):**

1. Create an external replay JSON with valid `version: 1`, matching `source_text`, `dataset: synthetic_text`, `licence: synthetic`, and `proposal: "synthetic non-object"`.
2. Use the synthetic text mapping and matching text, select replay, and click **Get proposal only**.
3. `propose()` correctly returns `accepted: false` / `proposal_schema_invalid`, but also returns the original truthy string in `proposal`. The UI calls `.get('fields')` on that string before rendering its refusal. Actual AppTest result: `AttributeError: 'str' object has no attribute 'get'` at app.py:230.

Two related malformed-envelope cases also reproduced:

- A replay with matching metadata but no `proposal` raises `KeyError('proposal')` from cache.py:51. Direct API/UI gets an exception and no `text_request_refused` event. CLI's existing LookupError wrapper would return an error, but the model refusal audit is absent.
- A mocked Mistral HTTP 200 body `{"choices":[null]}` raises an uncaught `AttributeError` at client.py:47 rather than the static transport refusal. No real request or key was used.

**Impact:** Untrusted but syntactically valid JSON can abort the app run instead of producing an audited, visible refusal. A real model may emit a JSON string/array despite JSON mode; replay files can also be malformed. No unintended import, review, mapping change or output execution was observed.

**Fix:** Validate replay/envelope shapes at their boundaries and normalize failures to static refusal codes. Only put a validated object into the form; retain rejected raw responses separately if desired. Guard form population by validated shape/acceptance instead of truthiness. Add regressions for missing proposal, scalar/array proposal and null/malformed choice objects, asserting visible refusal, refusal audit and no AppTest exception.

**Evidence:** `test_independent.py` tests `test_missing_replay_proposal_crashes_without_refusal_audit`, `test_nonobject_replay_proposal_crashes_ui`, `test_malformed_mistral_envelope_not_contained`; actual exception and stack trace in `independent.log`.

### P2-R1-S2 — medium — GTFS provenance construction repeatedly scans and parses calendar exceptions

**Location:** `src/nightdesk/adapters/gtfs.py:173–174`, inside the service-day/stop output loop.

Every output stop row scans all `calendar` and `calendar_dates` rows again. For a valid one-trip feed with D added service dates and 11 stops, `_day()` is called **D + 11D²** times. This is avoidable superlinear work in a normal GTFS import, well below the adapter's 10,000-service-day and archive byte limits.

**Independent actual measurements** using the unchanged 11-stop fixture plus authored daily calendar exceptions:

| Service dates | ZIP bytes | Output rows | `_day()` calls | Normalization seconds |
|---:|---:|---:|---:|---:|
| 100 | 4,818 | 1,100 | 110,100 | 0.251 |
| 200 | 6,818 | 2,200 | 440,200 | 0.944 |
| 400 | 10,818 | 4,400 | 1,760,400 | 3.746 |

Doubling the input dates/output rows makes normalization take about four times as long. Counts are deterministic assertions, not only wall-clock inference. No large download, memory exhaustion or deliberately huge archive was used.

**Impact:** A small, valid multi-date schedule spends most of its work reparsing the same source dates, and the accepted technical limits do not prevent this amplification. Larger imports can hold the synchronous CLI/UI operation for much longer than their output size warrants.

**Fix:** Build calendar indexes by service and exception indexes by `(service_id, parsed_date)` once, then reuse the raw evidence rows in the output loop. Keep identical retained raw proof and validation semantics. Add a bounded-operation scaling regression rather than a fragile timing threshold.

**Evidence:** `test_independent.py::test_gtfs_exception_scan_scaling` at D=100,200,400; `independent.log` records input sizes, output sizes, exact date-parse counts and timings.

## Verification actually run

All shell check runners used this wrapper, with their indicated argument tail:

```sh
cd /tmp/nightdesk-p2-r1-sol-2a0ce8f8/copy
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/nightdesk-p2-r1-sol-2a0ce8f8/copy/src \
  PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=<unique path below>' \
  sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  uv run --offline --no-sync <argument tail>
```

The tests use synthetic placeholder keys only inside mocked transport tests; no actual credentials were read or sent.

| Argument tail / command | Basetemp | Actual result / evidence |
|---|---|---|
| `pytest -q` | `.../pytest-tmp` | **exit 0**, 381 passed in **37.29s**; `full-tests.log` |
| `python /tmp/nightdesk-p2-r1-sol-2a0ce8f8/run_acceptance.py` | `.../acceptance-pytest-tmp` | **exit 0**; `acceptance.log` |
| `pytest -q -s /tmp/nightdesk-p2-r1-sol-2a0ce8f8/test_independent.py` | `.../probes-tmp` | **exit 0**, 9 probes passed in **5.26s**; includes assertions confirming the defects above; `independent.log` |
| `pytest -q -s /tmp/nightdesk-p2-r1-sol-2a0ce8f8/test_ui_independent.py` | `.../ui-probes-tmp` | **exit 0**, 4 full-app checks passed in **7.59s**; `ui-independent.log` |
| `git diff --check` (read-only, checkout) | n/a | **exit 0** |
| SHA256 verification of checkout and isolated-copy snapshot | n/a | **exit 0**, all 127 product hashes match before/after |

`run_acceptance.py` imports the unchanged Phase 2 acceptance module and calls `build()`/`cli()` with an explicit temporary workspace, avoiding its original script-main .handoff write. It also runs unchanged Phase 0 acceptance in a separate temporary workspace. Actual installed CLI subprocesses inherit the copy's PYTHONPATH.

Acceptance results:

- Three synthetic API dossiers/export paths returned `unknown` with `different_boundary_points`, `ambiguous_local_time`, `incomplete_capture`.
- Public demo manifest: 27 hashed CC0/synthetic assets passed; valid replay stdout identical on repeated real CLI runs; injected, wrong-year and month-contradiction replays returned expected CLI exit 1.
- GTFS real CLI imported 22 scheduled rows, 0 rejects, with unresolved-path wording.
- All six Phase 0 steps plus JSON/XLSX/merged-header refusal/flatten/import passed. Its socket probe returned exit 0 and errno 1 under network denial.
- Independent production-main AppTest exercised all three cases through queue → dossier → local review/question → delay refusal → Markdown/JSON export → audit verify.
- Independent production-main public-demo AppTest confirmed/imported both allowlisted synthetic captures, replayed a valid notice, then refused the poisoned replay without adding a capture.
- Full suite covers reviewed aliases, ambiguity/bundle isolation/tamper detection; uncertain work identity and multi-date absolute boundary binding; DST/half-open windows; GTFS >24h/DST/variants/B cap; dataset/bundle consent and revocation, fixed Mistral host/no redirect; cache isolation; poison gates and transitive demo provenance. Additional independent probes checked changed quote/value rejection, explicit import, German date spellings, missing clocks and invalid timezone refusal.
- UI log includes Streamlit's automatic Arrow conversion warning for heterogeneous diff values; assertions found no app exception on the ordinary UI flows. This is not a warning-free-log claim.

The fixes requested are contained within P2.3/P2.5. No optional feature or Phase 3 scope is requested. This reviewer deliberately left the checkout and ledger untouched; the parent can copy these two findings and this report into its ledger after review completion.
