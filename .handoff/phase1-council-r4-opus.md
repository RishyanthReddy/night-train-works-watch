# Phase 1 council R4 — Opus (focused recheck)

**Verdict: APPROVE, 9/10.** No reproducible Phase 1 regression in the two-file delta.

## Integrity
- `.handoff/phase1-council-r4-snapshot.json`: 93/93 match before and after; the /tmp copy matches all applicable entries. Only desk.py and tests/test_phase1_queue_scale.py differ from the R3 snapshot.
- No writes to the checkout. git status gained two new `.handoff` files during the run (phase1-completion-audit.md, phase1-council-r4-tasks.json). The parent wrote those, not this reviewer.
- Workspace: /tmp/p1r4opus/ws. It is a copy without .git, data or .handoff, uses a symlink to the checkout .venv and sets PYTHONPATH to the copy's src. The wrapper is /tmp/p1r4opus/run.sh: sandbox-exec deny network, the six credentials unset, no bytecode, no pytest cache, own basetemp.

## Results
| Check | Exit | Result |
|---|---|---|
| pytest -q | 0 | 330 passed, 22.95 s (full.log) |
| tests/phase0_acceptance.py | 0 | PASS (phase0.log) |
| probe/test_r4_probe.py | 0 | 46 passed (probe.log) |
| queue_scale.py (Sol's script, 100/200/400/800 legs at sequence 1) | 0 | queue 0.148/0.281/0.587/1.203 s, linear (scale.log) |

## Probes
- 40 random leg sets (sequence None or 1-5, duplicate sequences): R4 `_checks` gives the same findings order, border summary and unresolved set as R3 desk.py.
- Real syn v1→v2 queue with a link: identical to R3 apart from deduplicating `no_run_selected`.
- Removed middle leg: aa:101 and cc:303 each get exactly one `adjacent_leg_not_observed` unknown. Queue and dossier agree. With no link, no presence finding appears.
- Incomplete after capture: the existing `incomplete_capture` boundary is kept, the extra finding is only `unknown`, and no cancellation or agree/mismatch is invented.
- Added uncovered dd:404: no presence finding on the before side.
- Neighbour removed on a date it never operated: an extra unknown appears. This is consistent with the existing date-agnostic pairing in check_boundary.

## Nonblocking (pre-existing, not introduced by R4)
Medium: boundary candidates are matched by sequence only, so legs from different requests or journeys get paired (desk.py:96-97, same rule as R3). Test: 2-leg requests with sequences 1 and 2 (multi_request.py). R4 queue times were 0.33/1.03/3.65/14.7 s for 100/200/400/800 legs, with 400 `unlinked` border entries per row at 800 legs. R3 times were 0.42/2.06/11.9 s at 100/200/400 legs, so R4 is an improvement. The remaining cost is quadratic because the number of candidate pairs grows quadratically. KICKOFF row 8 says "adjacent path legs of one linked journey", so it would help to also scope candidates by request_id or journey_ref. This is outside the requested fix.
