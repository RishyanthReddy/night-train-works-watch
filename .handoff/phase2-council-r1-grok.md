# Phase 2 council R1 — Grok 4.7

Verdict: **CHANGES REQUESTED**
Score: **7/10**
Reviewer: Grok 4.7, read-only. No product, checkout, `data/`, or `.handoff` writes. No delegation, commit, push, live model call, credential use, or downloaded-code execution.
Baseline: branch `phase2`, HEAD `1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e`.
Scope: KICKOFF section 0, canonical records, time rules, gates, section 8 model policy, P2.1–P2.7. P2.8 skipped. Phase 3 not reviewed. Accepted Phase 1 limit P1-R6-O1 not reopened.

## Freeze

`.handoff/phase2-council-r1-snapshot.json`: 127 product hashes.
Before review: missing 0, mismatch 0, extra product files under `src/`, `tests/`, `mappings/`, `pyproject.toml`, `uv.lock`: 0.
After review: missing 0, mismatch 0. HEAD unchanged. Checkout product status is the same Phase 2 delta as at the start.

## Commands and exits

Isolated copy: `/tmp/phase2-r1-grok-copy` via rsync excluding `data/`, `.git`, `.venv`, `.handoff`, `Praha`. Checkout `.venv` symlinked. `PYTHONPATH` set to the copy `src`. Import resolved to `/tmp/phase2-r1-grok-copy/src/nightdesk/adapters/gtfs.py`.

Credentials unset for every run: `MISTRAL_API_KEY`, `NS_API_KEY`, `SWISS_OTD_TOKEN`, `DB_CLIENT_ID`, `DB_API_KEY`, `TRAIN_ARCHIVE_TOKEN`.

1. Full suite, from the copy, `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/phase2-r1-grok-pytest'`, `uv run --offline --no-sync pytest -q --tb=line`, wrapped in `sandbox-exec` profile `(version 1)(allow default)(deny network*)`.
   Result: **381 passed in 35.71s, exit 0**.
2. Independent probes `/tmp/phase2-r1-grok-probe.py` with the copy interpreter, same sandbox and unset keys. **exit 0**. Cases below.
3. Copy `tests/phase2_acceptance.py`, same sandbox, `PYTHONPATH` so the CLI imported the copy. **exit 0**.
   - `different`: unknown / `different_boundary_points`
   - `clock`: unknown / `ambiguous_local_time`
   - `partial`: unknown / `incomplete_capture`
   - `demo check`: 27 hashed assets, exit 0
   - valid replay twice, stdout equal, exit 0
   - injected / wrong-year / month-contradiction: exit 1, reasons `text_addresses_model`, `invalid_work_dates`, `month_contradicts_dates`
   - GTFS import: accepted=22 rejected=0, path_unresolved
   - printed `PHASE2_ACCEPTANCE_PASS; no live model request`
4. Extra GTFS probe (frequencies.txt and invalid `stop_timezone`), same sandbox. **exit 0**.

No live Mistral request. No API key was present.

## Screenshots viewed

- `.handoff/phase2-app-different.png`: dossier shows `unknown: different_boundary_points`, rule `border-v2`. The review checkbox is unchecked; that result is reached before the reviewed-point check.
- `.handoff/phase2-app-clock.png`: `unknown: ambiguous_local_time`, `border-v2`, review checkbox checked.
- `.handoff/phase2-app-partial.png`: `unknown: incomplete_capture`, `border-v2`.
- `.handoff/phase2-app-refusal.png`: button “Ask for a delay estimate” shows “Delay prediction is unavailable…”, `prediction_not_validated`, and the written-method fix. No delay number on that screen.
- `.handoff/phase2-app-poison.png`: replay of `tests/fixtures/text/injected.json` shows `Proposal refused: text_addresses_model`. Work-field boxes stay `{}`.

## Findings

| ID | Severity | Status | File |
|---|---|---|---|
| P2-R1-G1 | medium | open | `src/nightdesk/desk.py:220`, `src/nightdesk/adapters/gtfs.py:167`, `src/nightdesk/ui/app.py:140` |
| P2-R1-G2 | medium | open | `src/nightdesk/adapters/gtfs.py:20` |
| P2-R1-G3 | low | open | `src/nightdesk/intake/text.py:21`, `src/nightdesk/config.py:140` |
| P2-R1-G4 | low | open | `src/nightdesk/adapters/gtfs.py:116`, `src/nightdesk/adapters/gtfs.py:201` |

### P2-R1-G1 — Two scheduled trips of one route abort the whole queue

Severity: medium.

`runs.py:24` keeps trips separate (`trip_id` is part of the run group). `adapters/gtfs.py:167` sets `train_no` to `namespace + ':' + route_id`, so two GTFS trips of one route share that train number. `desk.py:85-86` indexes runs only by `(train_no, service_date)`. `desk.py:220-222` then raises `ValueError("select_one_run_capture_for_train_date")` when more than one run matches. There is no trip selector in the UI or queue API. `ui/app.py:138-144` catches that error and leaves `rows` empty, so the queue also shows the empty-capture message.

Repro (synthetic zip, copy only): duplicate the fixture trip as `ES453_v2` with the same `route_id` `ES453`, import with namespace `aa`, and open `queue()` for a path leg whose `train_no` is `aa:ES453` on `2026-11-09`, with that GTFS capture as `run_capture_id`.

Observed: import accepts 44 rows. `build_runs` has both `ES453_v1` and `ES453_v2` on `2026-11-09` and on `2026-11-11`. `queue()` raises `select_one_run_capture_for_train_date` and returns no rows. The same path comparison against the single-trip fixture returns 1 row.

Impact: fail-closed, no false A/B grade. The Phase 2 “variants stay separate” case cannot be inspected, and one colliding route suppresses every other row in that queue call. `--trip-id` at import is a workaround, not a selection in the queue. The error tells the user to select a capture even though both trips are already in the one capture.

Fix: do not raise out of `queue()` / `dossier()`. When several scheduled trips share a train number and service date, leave that train/date `time_unknown` with a reason such as `multiple_scheduled_trips`, and list the trip ids. Do not pick one. Keep rendering the other rows.

### P2-R1-G2 — Declared `stop_timezone` does not control the scheduled instant

Severity: medium.

`gtfs_instant` (`adapters/gtfs.py:20-34`) always measures elapsed time from agency-zone noon minus 12 hours. The comment says `stop_timezone` does not change that basis. `normalized_rows` (`gtfs.py:161-163`) calls it with the single agency zone. The raw stop, including `stop_timezone`, is copied into `gtfs_evidence`, and `planned_arr` / `planned_dep` are still emitted as aware instants.

The committed fixture’s zones (`Europe/Brussels`, `Europe/Amsterdam`, `Europe/Berlin`, `Europe/Prague`) are all `+0100` at `2026-11-10T10:00:00+00:00`, so the 22 acceptance rows are not numerically wrong for that feed. Prague `35:00:00` is `2026-11-10T10:00:00+00:00`.

Repro: same fixture with Prague `stop_timezone` set to `Europe/London`. Emitted arrival remains `2026-11-10T10:00:00+00:00` (Brussels elapsed time) while the stored stop says `Europe/London`. The same elapsed rule in `Europe/London` is `2026-11-10T11:00:00+00:00`. A second copy with `stop_timezone=Not/AZone` still emits `2026-11-10T10:00:00+00:00` and stores `Not/AZone`. The archive is not refused.

Impact: a stop whose zone offset differs from the agency zone gets a confident scheduled instant that the GTFS field does not state. Matching then uses that instant. Invalid declared zones are not left unresolved.

Fix: if `stop_timezone` is non-empty, apply the same noon-minus-12 elapsed rule in that zone. If the zone is missing or not a real zone, do not substitute the agency instant; leave the stop unresolved or refuse the archive. Do not invent the other zone’s offset.

### P2-R1-G3 — Injection markers are exact substrings

Severity: low. Not the reason for changes requested.

`text_guard` (`intake/text.py:21-26`) NFKC-casefolds and searches for the literals in `config.py:140-142`. The authored fixture still returns `text_addresses_model` (probe and CLI exit 1). Adding a newline (`Ignore previous\ninstructions`) or U+200B (`Ignore previous\u200b instructions`) to an otherwise valid notice makes `validate_proposal` return no reasons.

Impact: the obfuscated text is not rejected. It still cannot be executed. `propose` does not import or record a review, and a later `submit_text` still has to pass quotes and W1–W3. Mappings are not edited. This does not bypass consent, the fixed host, or NDA external replay (`nda_replay_requires_own_bundle_cache` on bundle `es`).

Fix: remove Unicode category Cf characters and collapse whitespace before the marker scan. Keep the quote and typed gates as the control that blocks a bad record.

### P2-R1-G4 — `frequencies.txt` is ignored while the capture is marked complete

Severity: low. Not the reason for changes requested.

`normalized_rows` reads `agency`, `stops`, `routes`, `trips`, `stop_times`, `calendar`, and `calendar_dates` only (`gtfs.py:116-122`). `import_gtfs` sets `complete=True` (`gtfs.py:201`). A synthetic `frequencies.txt` with `headway_secs=3600` on the fixture trip imported as accepted=11, rejected=0, `complete=True`, 11 rows: the template trip once, not the headway.

The committed fixture has no `frequencies.txt`. The 22-row acceptance import is unchanged. Do not build headway expansion in this fix.

Fix: refuse an archive that contains `frequencies.txt`, or any other schedule-shaping table this adapter does not apply, before marking a capture complete.

## Checked, not filed

- P1-R6-O1 excluded-neighbour provenance display. Phase 2 does not change that finding. Not reopened.
- Uncertain work identity returns `time_unknown` / `identity_uncertain` (`match.py:47-48`). Covered by `tests/test_phase2_dates.py`.
- A leg whose operating-date set has more than one date returns `boundary_service_date_binding_unknown` and does not reuse one absolute instant (`border.py:83-85`). A single service date may still agree when the instant falls on the next calendar day.
- Different boundary points, ambiguous local time, and incomplete capture stay `unknown` with those reasons. CLI acceptance and the three screenshots agree.
- GTFS path stays scheduled-only: real times and line stay empty, exact endpoints still grade B (`tests/test_gtfs.py`). Noon-minus-12 for the agency zone matches the Brussels DST examples in that test.
- `estimate_delay` ignores caller numbers. Refusal JSON has no digit. Export always includes it. Screenshot has no delay number.
- Model path: default provider `off`; dataset flag defaults false; bundle consent is the last `model_consent` event; mapping hash must be confirmed; host is fixed `api.mistral.ai`; non-200 does not follow a redirect; response is JSON-parsed, not executed. Covered by `tests/test_text.py` inside the 381. This review made no live call.
- NDA bundle replay of an external synthetic file is refused. Local cache hash/audit checks are in `tests/test_text.py`.
- Authored poisons do not import. German `17.12.2026` still fails `month_contradicts_dates` when the text says `Monat: November`.
- A range that starts in the declared month and ends in the next month is accepted (`Monat: November`, `2026-11-17`..`2026-12-18`). That is the written “declared month is one of the endpoint months” rule, not a second defect.
- Demo check refuses an NDA bundle, cycles, unlisted captures, and tampered hashes (`tests/test_demo.py`, CLI 27 assets). Public demo failure calls `st.stop()` (`ui/app.py:41-43`).
- No `eval`, `exec`, `subprocess`, `pickle`, or `os.system` under `src/nightdesk`. No `PTCAR`, `EURSLEEPER`, or `be-es` under `src/nightdesk`.
- Queue scale was not re-benchmarked in this review. No new quadratic path was identified in the Phase 2 diff. Alias load uses the operation reader.

## Ledger rows for the parent to copy

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P2-R1-G1 | Two GTFS trips that share route_id and service date raise `select_one_run_capture_for_train_date` and abort the whole queue. No trip selector. | medium | open | |
| P2-R1-G2 | `stop_timezone` is ignored. A different offset, and an invalid zone, still emit the agency instant. Fixture EU zones match +0100, so the 22-row sample is not currently wrong. | medium | open | |
| P2-R1-G3 | Newline or U+200B splits an injection marker so `text_guard` does not reject. Authored fixture still rejects. No exec or mapping change. | low | open | |
| P2-R1-G4 | `frequencies.txt` is ignored and the capture is still `complete=True`. Fixture has no such file. | low | open | |
