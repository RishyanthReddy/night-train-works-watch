**Verdict: changes requested, 6.5/10.** Most of the R1 fixes meet the requirements, not just the tests. One new high-severity blocker came in with the fix round, and the line-rule change produces a false no-match. All 90 snapshot SHA256 hashes matched before and after my checks. I wrote nothing to the checkout, `.handoff/` or `data/`; HEAD is still d340990.

## Blockers

**1. High: every revision load reads the whole audit log, so the time grows with the square of the data.**
- **Where:** [store.py:69](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/store.py:69) calls `read_events(bundle)` inside every `load_revision`, and [store.py:61-65](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/store.py:61) reloads the whole capture each time. [review.py:76-77](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/review.py:76) then calls `load_revision` once per observation. This came in with the R1 fixes for source metadata checks (P1-O3) and predecessor links stored as audit events (P1-G2).
- **Repro:** I used synthetic works in bundle `test-perf3` with the confirmed `syn_works.yaml`:
  - First 2,000-row ingest: 2.1 s.
  - A second 2,000-row capture with different descriptions: **87 s**.
  - Re-importing an identical capture: 0.28 s.
  - With 4,000 revisions and 8,003 audit lines, `snapshot_revisions` on one capture took **279 s**, `revisions()` took **583 s**, and one `record_decision` took **43 s**.
- **Impact:** the queue and dossier load each capture several times. At the KICKOFF data sizes (46k German works, 40k Infrabel rows) the app cannot be used. Phase 0's fix for quadratic audit reads (P0-R1-O2) is undone for typed imports.
- **Fix:** read the audit log once per operation and pass in an index of `revision_created`, `predecessor_recorded` and observation events (or cache it by log size and mtime). Do the same for capture rows. In `review.py`, work out each revision's subject once. Add a scaling test, for example 2×2,000 works within a time budget.

**2. Medium-high: a work with both exact endpoints on the path becomes `no_match` when its line differs.**
- **Where:** [match.py:53](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/match.py:53) returns `None` whenever every known segment line differs from the work's line, including when both endpoints are on the ordered path.
- **Repro:** in capture `vline` (v1 with syn-A's line set to `zz:9`), syn-A keeps `syn:start` → `syn:end` and its clock overlaps the run. The dossier no longer lists syn-A and reports "No-match 1 of 4". The queue row moves from A=1 to A=0.
- **Impact:** this goes against the A definition adopted in `decisions.md` and the §7 worked example. It also breaks §2 "Place gates downgrade… nothing else changes a grade" and "no-match is not safe". Line attribution is weak evidence (D1 notes 13.8% of segment-line assignments differed), yet here it removes an A.
- **Fix:** use the line filter only when there is line-only evidence. With both endpoints on the path, keep A and show `line_mismatch` as a reason, or at most cap the grade at B. Add a regression test.

**3. Medium: the queue ignores a new B exposure from a work whose endpoints are off the path.**
- **Where:** the `attached` flag at [desk.py:77](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:77) and the change test at [desk.py:101-103](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:101).
- **Repro:** capture `voff` is v1 plus syn-X (`syn:x` → `syn:y`, no line, clock overlapping). The dossier grades syn-X as **B** (`not_on_ordered_path`, `line_unknown`), but `queue(v1, voff)` returns **0 rows**.
- **Impact:** the works-only queueing fix (P1-G5) is inconsistent. A train-attached B shows in the dossier but never reaches the planner's queue. Because the run's whole window is used, every resolved work anywhere with an overlapping clock is graded B for every train. On real data that floods every dossier.
- **Fix:** decide the rule and apply it in one place. Either a work with both endpoints resolved and neither on the path is a counted `no_match`, or it is B and treated as attached. My recommendation is `no_match`, but the literal §2/W5 wording reads as B, so this needs a user decision recorded in `decisions.md`. Base `attached` on the exposure outcome (A/B) instead of re-deriving it from points and lines.

## Checks run
I worked in a copy at `/tmp/nd-opus-r2/ws` (no `.git`, `data/` or `.venv`) with `PYTHONDONTWRITEBYTECODE=1` and the `PYTEST_ADDOPTS` you gave.

| Check | Result |
|---|---|
| `uv sync --frozen --offline` | exit 0 |
| `pytest -q`, network denied with `sandbox-exec`, credential variables unset | **309 passed**, exit 0 |
| `tests/phase0_acceptance.py`, network denied | exit 0, PASS (JSON/XLSX, merged-header refusal → flatten → ingest) |
| syn v1, v2 and two variants imported as batches | all `complete=True` |
| v1→vline queue and dossier | blocker 2 reproduced |
| v1→voff queue and dossier | blocker 3 reproduced |
| `audit seal` / `audit verify`, bundle `test-opusr2` | exit 0, 105 events, wording keeps "source truth is not proved" |
| Scaling (CLI and API) | blocker 1 timings above |
| Screenshots viewed: `phase1-r2-queue.png`, `phase1-r2-stale.png`, `phase1-r2-works.png` | queue shows check columns plus the neighbour border row bb:202; dossier shows a prominent stale warning, the scoped no-match sentence and the unlocated warning |

## What held up when I read the code against the requirements
- **Completeness:** capture warnings no longer make a capture incomplete.
- **Predecessors:** links are append-only metadata, the first valid one wins and conflicts are audited.
- **Line-only works:** they now use only the matching line's segment windows.
- **Removed dates:** the queue uses the union of operating dates and shows per-side presence.
- **Border checks:** a positive check needs effective complete capture evidence. The "agrees" result also needs the capture to be present.
- **Review state:** staleness and reanswers follow capture observations in order, and the stale label shows in the queue and the dossier.
- **Audit:** check results are deduplicated under the lock (`append_once`).

I did not re-test the A→B→A and source-tamper cases myself; their regression tests pass.

The scaling blocker is enough on its own to hold the phase. After fixing 1 and 2 and settling the rule in 3, I would expect about 8.5/10.
