# Phase 2 council R2 — Grok 4.7

Verdict: **APPROVED**
Score: **9/10**
Reviewer: Grok 4.7, read-only. No product, checkout, `data/`, or `.handoff` writes by this review. No delegation, commit, push, live model call, credential use, or browser session.
Baseline: branch `phase2`, HEAD `1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e` before and after.
Scope: R1 fixes on the 128-file R2 freeze. P2.8, Phase 3, and accepted Phase 1 P1-R6-O1 were not reopened.

No new open ledger rows. P2-R1-G2 stays **disputed**. Do not convert `stop_times` through `stops.stop_timezone`.

## Freeze

`.handoff/phase2-council-r2-snapshot.json`: 128 files.
Before: missing 0, mismatch 0, extra product files under `src/`, `tests/`, `mappings/`, `pyproject.toml`, `uv.lock`: 0.
Against `.handoff/phase2-council-r1-snapshot.json` (127 files): the 8 delta sources changed, `tests/test_phase2_council.py` is new, the other 119 R2 entries match R1. Delta list is exactly `.handoff/phase2-r2-delta.json`.
After every command below: missing 0, mismatch 0, extra product files 0. HEAD unchanged.
`git diff --check` exit 0.
Checkout `.venv` mtime stayed `1794933299`. `src/nightdesk/adapters/gtfs.py` mtime stayed `1794976193`. No new `__pycache__` under checkout `src/` or `tests/`.
Checkout `.handoff/phase2-acceptance-workspace.txt` still points at `nightdesk-phase2-accept-j1bboaqo`. This review's acceptance pointer was written only in the copy.
Two untracked handoff files appeared during the window and were not written by this review: `.handoff/phase2-council-r2-opus.md`, `.handoff/phase2-r2-opus-parent-repro.log`. They are outside the 128-file product freeze. This review did not read them.

## Commands and exits

Copy: `/tmp/phase2-r2-grok-copy`, rsync excluding `data/`, `.git`, `.venv`, `.handoff`, `Praha`, `__pycache__`, `*.pyc`. Checkout `.venv` symlinked. `PYTHONPATH=/tmp/phase2-r2-grok-copy/src`. Ordinary `.venv/bin/python`, not `-I`. Imports resolved to the copy (`nightdesk/adapters/gtfs.py` and the other probed modules).
Every run unset `MISTRAL_API_KEY`, `NS_API_KEY`, `SWISS_OTD_TOKEN`, `DB_CLIENT_ID`, `DB_API_KEY`, `TRAIN_ARCHIVE_TOKEN`.
Sandbox profile: `(version 1)(allow default)(deny network*)`. A socket to `1.1.1.1:443` raised `PermissionError` errno 1.
`PYTHONDONTWRITEBYTECODE=1`. Pytest addopts: `-p no:cacheprovider --basetemp=/tmp/phase2-r2-grok-pytest`.

| Command | Result |
|---|---|
| `uv run --offline --no-sync pytest -q --tb=line` in the copy | **415 passed in 39.07s, exit 0** |
| `tests/phase2_acceptance.py` with `.handoff` created in the copy | **exit 0**. `different` / `different_boundary_points`, `clock` / `ambiguous_local_time`, `partial` / `incomplete_capture`. Demo check 27 assets. Replay stdout equal. Injected, wrong-year, and month-contradiction exit 1. GTFS accepted=22 rejected=0, `path_unresolved`. `PHASE2_ACCEPTANCE_PASS; no live model request` |
| `tests/phase0_acceptance.py` | **exit 0**. Six steps, JSON/XLSX/merged-header flatten, network-denial probe errno 1 |
| `/tmp/phase2-r2-grok-probe.py` | Product checks passed. Two assertions were probe errors, not product failures: an unchanged second leg is absent from the change queue; `Path.resolve()` is `/private/tmp` while the copy path was `/tmp`. See probe 2 |
| `/tmp/phase2-r2-grok-probe2.py` | **exit 0**, `PROBE2_PASS` |

No live Mistral request. The only key material was the in-process fake `synthetic-secret\n`. It was absent from the result and the audit, and no connection object was constructed.

No new browser claim. The new trip selector was exercised with Streamlit `AppTest` on `src/nightdesk/ui/app.py` from the copy. The five existing screenshots were not opened again.

## Timezone objection — sustained

R1 P2-R1-G2 asked to measure a non-empty `stop_timezone` with the noon-minus-12 rule and to treat `Europe/London` on this fixture as `2026-11-10T11:00:00+00:00`. That conversion is the wrong clock for GTFS `stop_times`.

This review did not re-open https://gtfs.org/documentation/schedule/reference/#stop_timestxt. The brief denies network. The page text is therefore **UNKNOWN — not re-fetched this session**. The parent's recorded citation says arrival and departure use `agency.agency_timezone`, not `stops.stop_timezone`. The code and the regression follow that rule, and the executed instants show what the rejected conversion would have done.

Executed with the copy's `gtfs_instant` and `normalized_rows`:

- Service day `2026-11-09`, clock `35:00:00`, zone `Europe/Brussels` → `2026-11-10T10:00:00+00:00`.
- The same digits in `Europe/London` → `2026-11-10T11:00:00+00:00`.
- Fixture agency is `Europe/Brussels`. After every `stop_timezone` was set to `Europe/London`, the Prague `35:00:00` row on `2026-11-09` stayed `2026-11-10T10:00:00+00:00`. The raw stop zone stored in `gtfs_evidence` was `Europe/London`. `agency_timezone` stayed `Europe/Brussels`. `time_basis` names the agency zone.
- An empty `stop_timezone` kept the same `10:00Z` instant.
- `Not/AZone` raised `gtfs_stop_timezone_invalid` and produced no rows.

`gtfs_instant` in [gtfs.py:20](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:20) takes one zone. `normalized_rows` passes the agency zone into it at [gtfs.py:177](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:177). A declared stop zone is only checked with `ZoneInfo` at [gtfs.py:137](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:137). The regression is [test_phase2_council.py:130](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/tests/test_phase2_council.py:130).

Do not change this to 11:00Z.

## R1 items

| ID | Result |
|---|---|
| P2-R1-G1 | Fixed. Two trips of `syn:ES453` on `2026-11-17` do not raise. Queue returns that row with `run_selection_required` and a separately edited `cc:303` row with `no_run_selected`. Four works stay `time_unknown` / `run_selection_required` until a choice. `run_options` labels list `ES453_v1` and `ES453_v2`. Choosing the v2 id sets `selected_run.trip_id` to `ES453_v2`, clears the reason, and leaves no grade A. The id is in the dossier JSON, the Markdown, and the audit. A foreign id raises `select_runs_from_these_captures`. AppTest showed both trip labels, no exception, and the widget value became the v2 id. |
| P2-R1-G2 | Disputed, and the dispute holds. See the timezone section. |
| P2-R1-G3 / O2 | Fixed for the R1 strings. Double space, zwsp-plus-space, newline, "Ignore the previous instructions", "disregard prior instructions", `SYSTEM :`, and `<\|im_start\|>system` all return `text_addresses_model` before send. |
| P2-R1-G4 | Fixed. `frequencies.txt` raises `gtfs_frequency_service_not_supported`, writes `gtfs_import_refused`, and adds no capture. |
| P2-R1-O1 | Fixed. Fake key `synthetic-secret\n` returns `mistral_key_invalid_format`, is absent from the result and the audit, and builds no connection. The 415 include CR, LF, space, and non-ASCII. |
| P2-R1-S1 | Covered by the 415 (`test_malformed_replay_visible_without_ui_exception`, `test_malformed_live_envelope_refused`). Replay non-objects return `replay_proposal_invalid` with `proposal` None. The form populates only an accepted object at [app.py:237](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/ui/app.py:237). |
| P2-R1-S2 | Covered by the 415. Calendar evidence is indexed once at [gtfs.py:157](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:157). The fixture has no `calendar.txt`, so the `<= 2*n` date-parse bound matches one pass in `service_dates` and one pass in the index. |
| P2-R1-O3 | `MAX_GTFS_ROWS = 50000` at [config.py:132](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/config.py:132). The projected count is refused before row construction at [gtfs.py:160](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:160). The 415 cover the refusal. |
| P2-R1-O4 | `csv.Error`, `RuntimeError`, and `NotImplementedError` become `gtfs_unreadable_archive` at [gtfs.py:125](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:125). The 415 cover an oversized field and an encryption flag, with `gtfs_import_refused`. |
| P2-R1-O5 | `--drafted-by` at [cli.py:199](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/cli.py:199). A non-manual mode stores `proposed_by` `llm` plus `extra.drafted_by` / `reviewed_by`. The 415 AppTest covers replay proposal then human import. |
| P2-R1-O6 | A missing timezone field takes the mapping default at [text.py:81](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/text.py:81), with `timezone_basis` `declared_mapping`. Covered by the 415. |
| P2-R1-O7 | `Month: December`, `Month December`, and `Month - December` are recognized. December inside 2026-11-17..2027-01-05 was accepted by an independent `validate_proposal` call. The same declaration on the November-only notice returned `month_contradicts_dates`. |

G1 selection is [desk.py:238](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:238) through [desk.py:268](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:268). The queue no longer has `select_one_run_capture_for_train_date`. The UI control is [app.py:142](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/ui/app.py:142). Audit payloads include `run_selection_ids` from [desk.py:401](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:401) and the dossier selections at [desk.py:452](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:452).

## Checked, not filed

- Before a choice, dossier `unknowns` also contains `no_scheduled_or_observed_run_selected` even though both trips were imported. `run_selection_required` is present beside it, and the selector lists the trip ids. No grade is emitted. Not a separate defect.
- The summary grade counter stays at zero `time_unknown` until a run is chosen, because that counter only tallies `match_work` exposures. The per-work audit rows are `time_unknown`, and `checked_pairs` is 0. No false A or B.
- `ignore` + U+200B + `previous instructions` (the format character used as the space) is not caught by the denylist. With consent off it stopped at `bundle_external_processing_disabled` and did not send. The R1 cases, which keep a real space, are refused. The fix does not claim the denylist is complete. Quotes and typed gates remain the record control.
- Empty `stop_timezone` correctly keeps the agency instant. Invalid names are refused. This review did not add parent-station timezone inheritance checks. That was not an R1 fix.

## Not checked

- A fresh fetch of the GTFS reference page.
- A live Mistral call, billing, or a real TLS handshake.
- A new browser session, or a second viewing of the five Phase 2 screenshots.
- P2.8, Phase 3, and P1-R6-O1.
- Checkout `data/`.

## Ledger for the parent to copy

No new open row.

Existing row to leave disputed:

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P2-R1-G2 | `stop_timezone` must not reinterpret `stop_times`. Agency noon-minus-12 stays `2026-11-10T10:00:00Z` when the stop zone is `Europe/London`. `Not/AZone` is refused. The 11:00Z conversion is rejected. | medium | disputed | R2 Grok: independent `gtfs_instant` / `normalized_rows` on the copy. Do not change the clock. |
