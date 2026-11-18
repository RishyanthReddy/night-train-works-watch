**Verdict: APPROVE, 8.5/10.** I found no material blocker. P1-R4-O1 is fixed: legs with no link get one sourced unknown each, explicit links pair only their own members, and checks scale linearly. One medium nonblocking issue remains, from the late same-train guard: a journey that re-enters a network can't be fully resolved by explicit choice, although it never produces a false result.

## Integrity
- **Hashes:** `.handoff/phase1-council-r5-snapshot.json` has sha256 `7f1ba468…a037a00`. All 94 entries matched before and after the review, in the checkout and in the /tmp copy.
- **Checkout untouched:** HEAD is still `ff4581b`. The modified tracked files are the same ones as at the start (six `.handoff` files plus the four product files under review). I didn't write to the checkout, run git commands that change it, touch Phase 2 or use the network.
- **Workspaces:** `/tmp/p1r5opus/ws` is a copy of the working tree without .git, data, .handoff or Praha. `/tmp/p1r5opus/head` holds `git archive HEAD`, for comparison. Both symlink the checkout `.venv`, which was not rewritten. The wrapper `/tmp/p1r5opus/run.sh` sets `PYTHONPATH` to the copy's `src`, denies network with sandbox-exec, unsets the six credentials, disables bytecode and the pytest cache, and uses its own basetemp.

## Results
| Check | Exit | Result (log in /tmp/p1r5opus) |
|---|---|---|
| `pytest -q` | 0 | 336 passed, 36.08 s (`full.log`) |
| presence + boundary_scope + border tests | 0 | 23 passed (`focused.log`) |
| `tests/phase0_acceptance.py` | 0 | PASS (`phase0.log`) |
| Reviewer probes, new code | 0 | 8 passed (`probe_new.log`, `probe_new2.log`) |
| Same probes, HEAD | 0 | 2 passed (`probe_head.log`) |

## What I checked
- **Scaling with many requests:** I used two-leg requests with 10 operating dates each.
  - 200 legs (2,000 rows): 0.74 s.
  - 800 legs (8,000 rows): 3.13 s, roughly 4× the 200-leg time, so linear.
  - Every row has exactly one boundary entry: `unlinked` without a link, `ambiguous_boundary_leg` when one link covers all 800 trains. Without the fix, the all-trains link would pair every leg with every leg at the next sequence.
- **Same train, two requests on different dates:** at HEAD, this case paired legs across requests and produced false `operating_dates_differ` mismatches. The new code returns `ambiguous_boundary_leg`. Choosing the request-17 legs restores the real `boundary_instants_differ` mismatch on 2026-11-17. The 2026-11-18 rows say `boundary_leg_not_selected`, and no positive result is invented.
- **Choices:** an unknown revision id raises `select_boundary_legs_from_these_captures`. The audit event records the choices and `boundary-scope-v1`.
- **Existing checks kept:** the removed-operating-date mismatch and missing-neighbour tests still pass, and `coverage_by_train` gives the same unsupported/unlinked reasons as the old `covers`.
- **Capture id alone:** excluding `selected_capture` from the finding comparison works. `queue(c1, c1)` returns `[]`.

## Nonblocking findings
**R5-O1 (medium): a journey that re-enters a network can't be fully checked.**
- **Where:** [desk.py:109-118](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:109) groups candidates by network and train only.
- **Repro:** probe `test_reentry_same_train_two_sequences` with aa:101 at sequence 1, bb:202 at 2 and aa:101 at 3, linked with `*`.
  - HEAD reports the real `boundary_instants_differ` mismatch on both boundaries.
  - The new code returns `ambiguous_boundary_leg` everywhere, even when every leg is chosen, because two chosen aa:101 records still count as competing.
  - The only workaround is two separate selections: one that includes sequence 1 and one that includes sequence 3.
- **Help text:** the UI help at [app.py:117](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/ui/app.py:117) says to "choose one", which doesn't work for this shape.
- **Suggested fix:** once every candidate in a network/train group is explicitly chosen and their sequences differ, treat the group as resolved per sequence.

**R5-O2 (low): a neighbour removed by a choice leaves no trace.**
- **Where:** [desk.py:174-178](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:174).
- **Repro:** in the re-entry case, choose sequences 1 and 2. The bb:202 row shows only the 1→2 mismatch, with nothing about the 2→3 boundary. The deselected aa seq-3 row is unknown in both captures, so it drops out of the queue.
- **Suggested fix:** emit a `boundary_leg_not_selected` unknown for the neighbour, as the missing-neighbour rule already does.

Phase 2 stays held. I stopped after this report.
