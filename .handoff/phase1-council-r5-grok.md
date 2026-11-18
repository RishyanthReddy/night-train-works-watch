# Phase 1 council R5 — Grok 4.7

**APPROVE — 9/10.** No material reproducible blocker in the five-file follow-up.

Product delta versus `ff4581bd05815305f8b9b475b9ba7472291c4217` is only:

- `src/nightdesk/desk.py`
- `src/nightdesk/links.py`
- `src/nightdesk/ui/app.py`
- `tests/test_phase1_queue_scale.py`
- `tests/test_boundary_scope.py` (untracked)

No Phase 2 module is in that delta. Snapshot `.handoff/phase1-council-r5-snapshot.json`: **94/94 SHA256 match before and 94/94 after**. Review writes stayed under `/tmp/p1r5grok`. Source files in the checkout were not modified by this review.

## Commands and exits

Execution copy `/tmp/p1r5grok/ws`, `PYTHONPATH` pointed at that copy (`nightdesk.desk` loaded from `/tmp/p1r5grok/ws/src/nightdesk/desk.py`). Shared `.venv` via symlink. `PYTHONDONTWRITEBYTECODE=1`. `PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/p1r5grok/pytest-basetemp'`. `uv run --offline --no-sync`. Sandbox `(version 1)(allow default)(deny network*)`. `MISTRAL_API_KEY`, `NS_API_KEY`, `SWISS_OTD_TOKEN`, `DB_CLIENT_ID`, `DB_API_KEY`, `TRAIN_ARCHIVE_TOKEN` unset.

| Check | Exit | Result |
|---|---|---|
| Snapshot hash before | 0 | 94 match, 0 missing, 0 mismatch |
| `pytest -q` in the copy | 0 | 336 passed in 35.07s |
| Socket to 1.1.1.1:443 inside the sandbox | caught | `PermissionError` errno 1 |
| Independent probe `/tmp/p1r5grok/probe.py` | 1 | Product checks below passed; three probe assertions were wrong (see notes) |
| Follow-up `/tmp/p1r5grok/probe2.py` | 0 | One-sided sides, missing-neighbour detail, export/audit fields |
| Snapshot hash after | 0 | 94 match, 0 missing, 0 mismatch |

Phase 0 acceptance script and the full CLI transcript were not re-run here. `UNKNOWN — not checked` for those two logs.

## What the probes showed

Unlinked mixed requests, 200 and 800 legs: `check_boundary` calls **0**, every row has one border entry `unknown/unlinked`. 800-leg queue **1.374s** in this sandbox (builder log says 1.189s). Same-capture queue returns 0 rows.

One explicit two-member link, different request ids `aa-request-0` and `bb-request-0`: **4** `check_boundary` calls and **2** `coverage_by_train` compiles at both 200 and 800 legs. The evaluated pair is `agrees_on_checked_fields` because the copied template instants match. Every other row stays one `unlinked`. A link dated 2026-11-18, and an unsupported date rule, make **0** pair calls and the reasons `unlinked` and `unsupported_service_date_rule`. `covers()` matches the previous member-order function on the rule orders tried. A revision id outside the two captures raises `select_boundary_legs_from_these_captures`.

Both captures contain a second `aa:101` leg, same sequence and sequence 4. Before a choice, `bb:202` has `ambiguous_boundary_leg` and does not have `boundary_instants_differ`. Choosing the original `syn-request` sequence-1 revisions produces `boundary_instants_differ` with instants `2026-11-17T22:01:00+00:00` and `2026-11-17T22:00:00+00:00`. Choosing every `aa:101` revision leaves `ambiguous_boundary_leg`. Audit `dossier_checked` stores the sorted choice and `boundary_scope: boundary-scope-v1`. `verify` returns valid.

Removed operating date on the after `aa:101` payload still yields `mismatch/operating_dates_differ`, presence `{before: true, after: false}`. Point, kind, blank time, and incomplete capture still yield `different_boundary_points`, `different_event_kinds`, `missing_time`, and `incomplete_capture`. Removing `bb:202` from the after capture yields one `unknown/adjacent_leg_not_observed` on `aa:101`, `selected_capture` equal to the after capture, queue border equal to the dossier, limits text saying no cancellation is inferred. With no link, that dossier's finding is `unlinked` / `boundary-scope-v1`.

`_check_changes` treats findings that differ only by `selected_capture` as unchanged, and treats a reason change or `other_capture_revision` change as a change (`desk.py` around the border comparison).

Export JSON of the chosen dossier contains `selections.boundary_revision_ids`. Its findings are `border-v1`. The string `boundary-scope-v1` is on `dossier_checked` and `comparison_checked`, not in that JSON body. Markdown does not render the selections block.

Viewed builder screenshots: unlinked dossier shows `unknown: unlinked` and `boundary-scope-v1`; ambiguity warning is on screen with the review checkbox off and an expanded `boundary_point_not_reviewed`; chosen source legs show `mismatch: boundary_instants_differ`. The 336 includes `test_app_explicit_boundary_choices_resolve_ambiguity`. This review did not open a new browser.

## Nonblocking notes (no change requested)

1. Ambiguity is per capture. A second `aa:101` only in the before capture leaves that side `ambiguous_boundary_leg` and still shows the after capture's single-leg `boundary_instants_differ`. The choice warning reads after findings (`ui/app.py` warning). The colliding side is not given a decisive aa/bb result.
2. A resolved export's finding rule versions are `border-v1`. Scope version and the choice ids are on the audit events; the choice ids are also in the JSON `selections`. Markdown has no selections section.

## Ledger for the parent

No open material finding. Suggested record: R5 Grok APPROVE 9/10, 94/94 hashes, 336 passed, 35.07s, network errno 1, six credentials unset. Notes above are nonblocking.
