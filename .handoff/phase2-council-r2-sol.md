# Phase 2 council R2 — Codex Sol independent read-only review

**Verdict: CHANGES REQUESTED. Score: 8.5/10.**

One medium finding remains in the malformed-replay refusal boundary. The original R1 proposal/envelope reproductions are fixed; a malformed metadata value still aborts the text UI without an audit event. No high-severity defect was reproduced. P2.8, Phase 3 and accepted P1-R6-O1 are excluded.

## Finding P2-R2-S1 — medium — malformed replay licence bypasses the audited refusal boundary

**Primary location:** `src/nightdesk/llm/cache.py:49`. Related boundaries: `src/nightdesk/llm/client.py:88` and `src/nightdesk/ui/app.py:235`.

**Reproduction, synthetic and network-denied:** create an external replay with otherwise valid matching metadata and a valid proposal, then set `licence` to `[]` or `{}`:

```python
body = dict(version=1, source_text=TEXT, dataset='synthetic_text',
            licence=[], proposal=PROPOSAL)
path.write_text(json.dumps(body))
propose(bundle, TEXT, mapping, provider='replay', replay_path=path)
```

At cache.py:49 the membership test in `{'synthetic', 'CC0'}` hashes the untrusted licence value and raises `TypeError: unhashable type: 'list'` (or `'dict'`). The replay metadata has not been type-validated. `propose()` catches only ValueError/OSError, so this exception escapes before `text_request_refused` is appended.

Actual independently observed results:

- Direct API: both list and object licence values raise TypeError; audit-event count stays unchanged and no capture is created.
- Production `render_text_intake` through Streamlit AppTest: clicking **Get proposal only** raises the same exception at cache.py:49, aborting the app run; no visible static refusal and no refusal audit.
- Actual installed `nightdesk text propose notice.txt --mapping mapping.yaml --provider replay --replay metadata.json`: exit **1**, with a traceback and the same TypeError; no refusal audit.

**Impact:** A small syntactically valid untrusted replay JSON aborts the UI instead of producing the required visible, audited refusal. This is a remaining case of the R1-S1 failure class. No record import, review change, mapping change, execution or credential disclosure was observed.

**Fix:** Type-check replay metadata before set membership (at least require a string licence, or validate the replay envelope with a typed model); raise an existing static refusal code. Keep failure normalization free of arbitrary exception text. Add list/object licence API, CLI and AppTest regressions requiring `proposal=None`, a visible refusal, a `text_request_refused` event and no capture. This is bounded P2.5 work.

Evidence: `test_independent_r2.py::{test_malformed_metadata_reproduces_uncaught_exception,test_metadata_crashes_actual_text_ui,test_malformed_metadata_actual_cli_traceback}`; `independent-final.log`. These tests deliberately assert the current defect, so their passing result does **not** mean the refusal requirement passes.

## R1 fixes independently checked

| R1 item | R2 assessment and evidence |
|---|---|
| O1 key disclosure | Fixed in the reviewed paths. Full suite runs malformed CR/LF/space/non-ASCII key regressions before connection. Independent mocked connection.request ValueError and HTTPException containing a synthetic secret return static `mistral_transport_or_response_invalid`, no secret in result/audit, refusal audited. No real credentials or live transport used. |
| S1 malformed proposal/envelope/UI | Original missing/scalar/array proposal and null/malformed choice cases pass the added regressions; rejected proposal is None and form population requires an accepted object. Metadata typing remains incomplete as P2-R2-S1 above. |
| S2 repeated calendar parses | Fixed. Independent exception-only feed tests: 100/200/400 dates yield 1,100/2,200/4,400 stop rows and exactly 200/400/800 `_day()` calls. Each output retains its matching raw exception proof. Index creation at gtfs.py:158–159 is outside the output loop. This verifies the requested at-most-2*n bound for the exception-only case. |
| G1 trip ambiguity | Fixed in tested flows. Two eligible same-route/date trips leave selected_run None with `run_selection_required`. Explicit ES453_v2 selection agrees across queue, dossier, comparison audit, dossier audit and JSON export. Foreign selection refuses. An independently changed bb:202 row remains present and unchanged when selecting the other train's trip. Full-suite production-main AppTest operates the actual Run observations selector. |
| O2/G3 injection variants | Added normalization and pattern regressions pass in full suite, before transport. No claim of a comprehensive natural-language injection detector. Quote/schema checks and explicit import remain necessary. |
| O3 output expansion | Projected row count is checked against MAX_GTFS_ROWS=50000 before constructing output rows; refusal code names date/trip selection. Added limit regression passes. |
| O4 archive failures | CSV, encrypted ZIP and unsupported-compression exceptions are normalized to unreadable archive; encrypted/CSV audit regressions pass. |
| O5 draft provenance | CLI --drafted-by, form origin and replay-to-import AppTest pass; proposed_by llm and drafted_by/reviewed_by are retained. |
| O6 declared mapping timezone | Missing source timezone receives the declared mapping timezone; retained basis and mapping hash are asserted by the added regression. |
| O7 month range | Added month separator and November-to-January interior-December regressions pass; contradictory December outside the November range refuses. |
| G4 frequencies | Presence of frequencies.txt is explicitly refused; no frequency feature added. Regression passes. |

For items without a separately authored probe, evidence is this review's actual 415-test full run plus reading the production code and added regressions, not a repetition of the parent's test claim.

## G2 objection — accepted

The proposed R1 stop-zone conversion would be incorrect. The official stop_times arrival/departure definitions use the agency timezone even when a stop declares another zone. [Official GTFS reference, stop_times.txt](https://gtfs.org/documentation/schedule/reference/#stop_timestxt).

I opened that primary source with the read-only web tool and inspected its arrival_time/departure_time definitions (returned lines 699 and 708). The requested test also passed in the independent full run: changing stop_timezone to Europe/London retains **2026-11-10T10:00:00+00:00**, while Not/AZone is refused. Keeping agency-based conversion is correct; do not change it to 11:00Z. The invalid-zone part of the R1 concern is addressed. Documentation reading was separate from execution: all code and CLI runs were OS-network-denied.

## Freeze, scope and execution isolation

- Checkout: `/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a`.
- Branch **phase2**, HEAD **1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e**, independently read before and after.
- Read `.handoff/phase2-r2-evidence.md` first, then handoff skill/global/project memory, all three R1 reports, review ledger, TODO, KICKOFF section 0 / Phase 2 / model policy / common gates and relevant production/test code.
- All **128** R2 snapshot hashes match before and after. R1 comparison exactly matches the declared **eight production files plus one new test**; every other R1 snapshot entry is unchanged. Copy also matches all 128 after all tests. See freeze-before.json / freeze-after.json / snapshot.json.
- Independent copy: `REVIEW/copy`, rsync excludes data, .git, .venv, .handoff, Praha, __pycache__ and .pytest_cache. Only the existing checkout .venv is symlinked for read-only dependency reuse. An empty .handoff was created **inside the copy only**. The acceptance runner calls build()/cli()/run() with explicit temporary roots and never invokes the checkout-writing acceptance script main.
- PYTHONPATH points to copy/src; a successful independent environment probe verifies the imported module's resolved path is under copy. Ordinary Python, not -I, runs the tests/probes. The unchanged Phase 0 acceptance uses -I only for its stdlib-only child socket probe.
- No checkout product/data/.handoff writes, delegation, source edits, git mutations, commit/push, live Mistral request, real credential access or spend. No checkout data was read. No browser session or image viewing occurred in this review; UI evidence is AppTest, and no fresh visual verification is claimed.

## Actual commands and exits

`REVIEW` below is `/tmp/nightdesk-p2-r2-sol-ti4m7g6p` (macOS resolves /tmp as /private/tmp).

The exact execution wrapper is retained as `REVIEW/run.sh`:

```bash
cd "$REVIEW/copy"
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REVIEW/copy/src" \
  PYTEST_ADDOPTS="-p no:cacheprovider --basetemp=$REVIEW/pytest-$1" \
  sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  uv run --offline --no-sync "${@:2}"
```

| Actual command (REVIEW expanded as above) | Exit / result | Retained evidence |
|---|---|---|
| `bash "$REVIEW/run.sh" full pytest -q` | **0**, **415 passed in 40.43s** | full-tests.log |
| `bash "$REVIEW/run.sh" acceptance python "$REVIEW/run_acceptance.py"` | **0**, INDEPENDENT_PHASE0_PHASE2_ACCEPTANCE_PASS | acceptance.log |
| `bash "$REVIEW/run.sh" final-probes pytest -q -s "$REVIEW/test_independent_r2.py"` | **0**, **11 passed in 1.11s**, including confirmed defect assertions | independent-final.log |
| First probe run with same wrapper, basetemp pytest-probes | **1**, 1 failed / 9 passed: reviewer sanity assertion compared resolved /private/tmp to unresolved /tmp. Fixed only the temporary probe to resolve both sides. | independent.log |
| Sanity-corrected probe run before strengthening unrelated-row/CLI checks | **0**, 10 passed in 1.00s | independent-rerun.log |
| SHA256 snapshot/R1-delta verifier before review, checkout + copy verifier after review | **0**, 128 matching entries, branch/HEAD unchanged | freeze-before.json, freeze-after.json |
| `git diff --check` (read-only checkout) | **0** | also recorded in freeze-after.json |

Environment probe confirms six credential variables absent and a socket connection fails with PermissionError under sandbox-exec. Tests inject only synthetic placeholders inside mocked request tests.

Actual acceptance checks preserved earlier behavior: three synthetic dossiers remain unknown with different_boundary_points, ambiguous_local_time and incomplete_capture; replay CLI output is identical twice; three poison CLI requests return expected exit 1; demo verifies 27 hashed assets; GTFS accepts 22 scheduled rows / 0 rejects. Phase 0 six-step CLI flow, JSON/XLSX, merged-header refusal, flatten/import and its socket-denial probe pass. Source licensing/GTFS evidence and exact CLI output remain in acceptance.log.

## Parent ledger row

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P2-R2-S1 | Unhashable replay licence metadata raises TypeError at llm/cache.py:49; API/UI/CLI abort without text_request_refused audit. Validate replay metadata types before membership and regress list/object licences. | medium | open | |

Leave R1-S1 partly reopened or link it to P2-R2-S1 until that boundary regression passes. Other tested R1 fixes stand. Keep G2's correct agency-time conversion. This report and temporary evidence are the review artifact; the parent may copy the row/report into its ledger after review completion.
