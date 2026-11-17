# Phase 1 council R3 — Opus

**Verdict: APPROVE, 9/10.** No reproducible Phase 1 blocker found.

Snapshot `.handoff/phase1-council-r3-snapshot.json`: 92 entries, 0 mismatches before and after (`/tmp/p1r3opus/verify.py`, exit 0). HEAD d340990, branch phase1. No checkout, handoff or data/ writes; all runs in `/tmp/p1r3opus/ws` (copy without .git/data/.venv; own `.venv` via `uv sync --frozen --offline`, exit 0).

## Commands
| Check | Exit | Result |
|---|---|---|
| pytest -q (sandbox-exec deny network*, six credential vars unset, PYTHONDONTWRITEBYTECODE=1, PYTEST_ADDOPTS -p no:cacheprovider --basetemp=/tmp/p1r3opus/bt) | 0 | 325 passed, 30.1 s |
| tests/phase0_acceptance.py (same wrapper) | 0 | PASS |
| probe/p1.py syn workflow (API) | 0 | queue aa:101 changed exit.at; dossier A/B/time_unknown + unlocated separate, no-match 0 of 4; boundary mismatch; syn_bad incomplete; review+follow-up+export; re-import same capture id, same rows; v3 makes review stale, follow-up reopened, queue(v1,v2) shows `(stale)` |
| CLI (network denied): import refused before confirm (1), confirm/import v1/v2/syn_bad, rejects, review --owner --question, seal | 0 except first (1) | syn_bad complete=False rejected=1 invalid_work_dates |
| audit verify: cut tail with seal / removed line / edited value / edited key | 1 / 1 / 1 / 1 | restored log verifies 0 |
| probe/scale.py batch with N extra works per capture | 0 | see below |

## Scaling (local, one machine)
N=1000: ingest 1.04/1.47 s, queue 1.33 s, dossier 2.06 s, decision 1.29 s, verify 0.2 s.
N=2000: ingest 2.09/2.98 s, queue 2.97 s, dossier 4.1 s, decision 2.58 s, queue after review 4.32 s, verify 0.41 s (8056 events).
Roughly linear; R2 quadratic blocker resolved.

## R2 findings re-checked
- Whole-leg add/remove: queue rows source_record_removed/added, dossier opens, presence before/after shown (probe p2).
- Removed-date after-boundary binding, line-only named-line overlap, line_mismatch keeps A, off-path B queued, first audited predecessor authoritative, completeness recomputed and artifact hashes committed: read in code (store.py ReadSession.get, mapping.py load_capture 582-641, match.py 56-117, desk.py) and covered by passing regressions.
- No module-level caches; ReadSession per operation. Core grep for PTCAR/EURSLEEPER/be-es/infrabel outside config.py: none. Only MPL package installed: certifi (approved).

## Nonblocking
1. Low-medium — [desk.py:99-104](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:99): when a linked neighbour leg is wholly removed in a complete capture, the remaining leg's dossier silently drops that boundary check. Repro probe/p2.py (aa:101 removed from v2): bb:202 before has 2 `agrees`, after has 1 `agrees`, unknowns lists only `no_scheduled_or_observed_run_selected`. The removed leg's own task shows `border_not_checked`. Suggest an explicit unknown `adjacent_leg_not_observed` when a link member has no leg.
2. Cosmetic — `no_run_selected` appears twice in `checks_after.unresolved` (desk.py:107-111: set union, then append).
3. Product note — literal W5: resolved off-path endpoints with no line grade B over the whole run window; at N=2000 that gave 1334 B for one train. Decision recorded in decisions.md; consider confirming with the user before real data.
4. queue(v2,v3) shows `not_reviewed_locally` for the new revision; the stale prior review appears only in the dossier and in queue(v1,v2). Acceptable under the spec.
