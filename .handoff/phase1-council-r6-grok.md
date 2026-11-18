**APPROVE, 9/10.** No material regression in the three-file R6 delta. O1 and O2 behave as specified: an explicit choice of distinct non-null sequences resolves each boundary, and a choice-excluded adjacent sequence stays an unknown.

## Material regressions

None.

## What the delta does

Against the R5 snapshot, only these three files changed:

- `src/nightdesk/desk.py`
- `src/nightdesk/ui/app.py`
- `tests/test_boundary_scope.py`

`links.py` and `tests/test_phase1_queue_scale.py` are unchanged from R5. The desk change is in `choose_members` at [desk.py:122](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:122). A network/train group resolves per sequence only when at least one record is chosen, every chosen sequence is non-null, and the sequences are unique. Unchosen records and duplicate sequences stay ambiguous. [desk.py:189](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:189) emits one `unknown` / `boundary_leg_not_selected` when the adjacent sequence has excluded records and no selected record. The UI change is the help string at [app.py:117](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/ui/app.py:117). The new regression is [test_boundary_scope.py:141](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/tests/test_boundary_scope.py:141).

## Independent probes

Copy: `/tmp/p1r6grok-review/ws`, then removed. `nightdesk.desk` loaded from that copy. Shared `.venv` was a symlink; `uv run --offline --no-sync`; no venv file was newer than the review start.

| Check | Exit | Result |
|---|---:|---|
| Probe file, first run | 1 | 6 passed, 2 failed in 2.33s. The two failures were the helper sorting a `None` reason on `agrees_on_checked_fields`. The instant assertions had already passed. |
| Those two tests, rerun | 0 | 2 passed in 2.03s |
| `pytest -q` | 0 | **337 passed in 34.61s** |
| Socket to 1.1.1.1:443 inside the sandbox | caught | `PermissionError`, errno 1 |
| Six credential variables | absent | `MISTRAL_API_KEY`, `NS_API_KEY`, `SWISS_OTD_TOKEN`, `DB_CLIENT_ID`, `DB_API_KEY`, `TRAIN_ARCHIVE_TOKEN` |

Re-entry `aa:101` sequence 1, `bb:202` sequence 2, `aa:101` sequence 3:

- No choice: two `unknown` / `ambiguous_boundary_leg`.
- Every leg chosen: two `boundary_instants_differ`. Border 1 is `2026-11-17T22:01:00+00:00` against `2026-11-17T22:00:00+00:00`. Border 2 is `2026-11-17T22:35:00+00:00` against `2026-11-17T22:30:00+00:00`. The before capture agrees on both.
- Sequence 3 excluded: the queue and dossier for `bb:202` both show one border-1 mismatch and one `unknown` / `boundary_leg_not_selected` at sequence 3.
- Two chosen `aa:101` records at sequence 1, plus a chosen sequence 3, stay `ambiguous_boundary_leg`.
- A null sequence on an otherwise chosen re-entry stays ambiguous. That leg reports `leg_sequence_unknown`.
- Consecutive chosen legs of the same train return `unknown` / `same_network`.
- Sequence 3 absent from the after capture, and its revision chosen, stays `unknown` / `adjacent_leg_not_observed` beside the real border-1 mismatch.
- Four-leg mixed requests: unlinked queue makes 0 `check_boundary` calls and one `unlinked` entry per row. One explicit two-member link makes 4 calls, all `aa:0`/`bb:0`. The 200-leg and 800-leg assertions in the 337 cover the same call counts.

## Low residual

An excluded leg that exists only in the other selected capture can produce `boundary_leg_not_selected` on the current capture. The probe's after-side finding names sequence 3 and `selected_capture` equal to the after capture, and its detail has no `other_capture_revision`. The result is `unknown`. The positive finding beside it is the real border-1 mismatch. This is the same low provenance limit already on the ledger as P1-R6-O1. It does not need another fix cycle.

No new screenshot. The help text was read from source. The existing UI test is inside the 337.

## Hash freeze

`.handoff/phase1-council-r6-snapshot.json` has 94 entries, sha256 `26b79edc414a0d68e8bb4bfc2373bb15f79d83d9d796281ff9cc2a86d654e1f2`. Checkout matched 94/94 before the probes and 94/94 after. The copy matched 94/94 after. Git status was unchanged. No checkout edit, handoff write, data read, network fetch, delegation, commit, or push.

| File | R6 sha256 |
|---|---|
| `src/nightdesk/desk.py` | `6cedf90b2146ddd1a414fb8874dcd179d55a6a27084d8dbcf4ca29701430e311` |
| `src/nightdesk/ui/app.py` | `15251a6c3f77ef9b244610e533c3358286f0da6e576b6e699a395ebaa0f43558` |
| `tests/test_boundary_scope.py` | `2b16e6fcb6df74c2ff1888a4592f8d88d0f0658346212774da32ceb4543c8b69` |

Phase 2 was not started.
