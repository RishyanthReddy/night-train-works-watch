**Verdict: APPROVE, 9/10.** This delta has no material regressions. The R6 change fixes both R5 Opus nonblockers: O1, a journey that re-enters a network can now be fully checked, and O2, an excluded neighbouring leg now leaves an unknown instead of disappearing.

**Hash freeze**
- Before the review, all 94 entries in [phase1-council-r6-snapshot.json](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/.handoff/phase1-council-r6-snapshot.json) matched (sha256, 0 mismatches). After the review they still matched.
- Compared with the R5 snapshot, exactly three files changed: `src/nightdesk/desk.py`, `src/nightdesk/ui/app.py` and `tests/test_boundary_scope.py`.

**O1: re-entering a network**
- In [desk.py:110-127](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:110), a network/train group stops being ambiguous only when three things hold: at least one of its records was chosen, every chosen record has a sequence, and those sequences are all different.
- These cases still stay ambiguous: nothing chosen, two chosen records with the same sequence, and a chosen record without a sequence. Records you didn't choose go into the excluded list.
- I probed the riskiest new case: choosing aa:101 sequence 1 from `syn-request` together with aa:101 sequence 2 from `synthetic-other-request` (the `duplicate_anchor(2)` fixture, all aa:101 records chosen).
  - The two records are now paired. `check_boundary` returns `unknown same_network` / `different_boundary_points`, and no mismatch is produced.
  - The bb:202 row gets `boundary_leg_not_selected`.
  - So a cross-request pair within one train is still caught by the boundary rule's same-network guard.
- Pairing across requests between different networks still needs an explicit choice for each record. That was already true at R5, so it isn't new risk.

**O2: excluded neighbour**
- [desk.py:189-190](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:189) emits `boundary_leg_not_selected` when the neighbour's sequence has no selected record but does have excluded ones.
- The new test checks the full sequence: no choice gives all ambiguous, a full choice gives 2 `boundary_instants_differ`, and a partial choice gives 1 mismatch plus 1 unknown at sequence 3 ([test_boundary_scope.py:141-169](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/tests/test_boundary_scope.py:141)).

**UI**
- The help text at [app.py:117](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/ui/app.py:117) now explains that a re-entering train needs one choice per leg, each with a different leg number.
- The multiselect has no default, so nothing gets selected without the user. The CLI doesn't pass `boundary_revision_ids`.

**Low, nonblocking**
- An excluded record from the other selected capture can also trigger `boundary_leg_not_selected`.
- That finding doesn't record which capture the excluded record came from, unlike `adjacent_leg_presence`, which carries `evidence="other_selected_capture"`. The result is only a conservative extra unknown.

**Commands**
- I ran everything in my own copy at `/tmp/nd-r6-review-ggSU`, made with rsync excluding `.venv`, `.git` and `.pytest_cache`.
- Setup:
  - `PYTHONPATH` pointed at the copy's `src`; I confirmed `nightdesk.desk` was imported from the copy.
  - `UV_PROJECT_ENVIRONMENT` pointed at the checkout's `.venv` with `--no-sync`, so the venv was not rewritten.
  - `PYTHONDONTWRITEBYTECODE=1`, with `-p no:cacheprovider` and `--basetemp=/tmp/nd-r6-review-ggSU-bt`.
  - All six keys were unset, and `sandbox-exec '(deny network*)'` was on.
- The probe test (`tests/test_zz_probe.py`, in the copy only, then deleted) ran 7 imported tests that passed. The probe itself failed on purpose with `assert 0` so it would print its output.
- Full suite: `uv run --offline --no-sync pytest -q` gave **337 passed in 35.75s, exit 0**.
- I edited nothing in the checkout, used no network, delegated nothing and committed nothing. I did not start Phase 2.
