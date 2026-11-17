Phase 1 council round 1, Grok. Verdict: **changes requested. 6/10.** The checkout was not edited. Snapshot after the checks: **89 entries, 0 mismatches** against `.handoff/phase1-council-r1-snapshot.json`.

The synthetic accept path works. Five spec bugs are outside that fixture, and the 295 passing tests lock three of them in.

## Blockers

**1. High.** [mapping.py:473](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:473). Any row or typed `unresolved` marks a declared-complete capture incomplete. KICKOFF §7 says `complete` is true when the capture is declared complete, every file parsed, and no row was rejected or left with uncertain identity. C4 keeps a missing time unresolved and does not reject. C5 clamps an unknown enum. R2 then returns `comparison_unavailable`.

Repro: a blank optional time gives `complete: false`, `reasons: ["unresolved_fields"]`, `comparison_status: "comparison_unavailable"`, `field_diffs: 0`. An unknown enum `not-a-kind` is accepted (`rejected: 0`), clamped to `unknown`, and the capture is still incomplete for `unresolved_fields`. [tests/test_mapping.py:268](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/tests/test_mapping.py:268) asserts the stricter behaviour.

Fix: unresolved times and clamped enums stay row warnings. Incomplete only for undeclared complete, a parse failure, a rejected row, or uncertain identity. Change the test with the code.

**2. High.** [store.py:105](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/store.py:105). `FileExistsError` returns the stored revision and drops a valid predecessor. The predecessor is outside the content hash (KICKOFF §7), and R1 says a bad link is rejected while the revision is kept. A good link on the second save is discarded with `created: false` and no audit.

Repro: `make_reason: null`, attempted predecessor `7ca14153112007645792f02efe805f6752d81ab28d8148b8be2a2e1256c2720f`, `created: false`, `stored_predecessor: null`.

Fix: if the stored revision has no predecessor and the new save has a valid one, record it and audit it. If one is already stored and differs, keep the first and audit the conflict. Do not report success for a link that was not stored.

**3. High.** [match.py:87](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/match.py:87). Grade A requires `line_known`. KICKOFF §2 grade A is time overlap plus both endpoints resolved and on the ordered path. The worked example (KICKOFF ~679) is VILVOORDE to MECHELEN, both point ids on the path, grade A when the clock overlaps. No line is required. `line=None` with `path_unresolved` is a separate cap at B (P2.3).

Repro: both endpoints `syn:a` and `syn:c` on a `zz:1` run, `line=None`, clock overlapping 22:10–22:30. Outcome `B`, reasons include `line_unknown`. [tests/test_match.py:42](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/tests/test_match.py:42) asserts that downgrade.

Fix: A when both endpoints are resolved, ordered on the path, the clock overlaps that stretch, and the path is not unresolved. A missing line is a shown reason. Update `test_one_endpoint_unknown_line_and_gtfs_never_a`.

**4. High.** [match.py:46](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/match.py:46) and [match.py:66](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/match.py:66). With fewer than two on-path endpoints the pass window becomes the whole run. The line filter returns no-match only when every segment line is known and different. A line-only work whose clock hits another line is graded B because a later segment happens to carry the work’s line.

Repro: work `line=zz:9`, no endpoints, clock 22:00–22:05 Europe/Brussels. Run points a 22:00 (`zz:1`), b 22:10 (`line_arr=zz:1`, `line_dep=zz:9`), c 23:00 (`zz:9`). Outcome `B`, reason `not_on_ordered_path`, overlap `2026-11-17T21:00:00+00:00` to `2026-11-17T21:05:00+00:00` (the `zz:1` segment). D6 requires overlap with the pass on that stretch. D1 line is `a.line_dep` then `b.line_arr`.

Fix: when the only place evidence is a line, overlap the segments of that line. If that clock does not overlap, count no-match. Do not widen a line-only work to the whole run.

**5. High.** [desk.py:42](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:42) and [desk.py:69](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:69). The queue and dossier only open on a `PathLeg` with field diffs. A works-only change that removes an exposure never appears.

Repro: both captures complete. Exposure at 22:00 is `A`; at 01:00 it is `no_match`. `queue` is `[]`. `dossier` raises `select_a_changed_path_leg_from_these_captures`. `check_works` reports `no_match_checked_pairs: 1` of `checked_pairs: 4`.

Fix: one queue row per train/date when the path changed or the works exposure or border finding for that train changed. Let the dossier open on that row.

**6. Medium.** [ui/app.py:168](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/ui/app.py:168). The dossier screen never renders the scoped no-match count. [export.py:158](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/export.py:158) does: `No-match pairs: N of M`.

AppTest of the reviewed syn dossier: screen contains `aa:101`, `time_unknown`, `unlocated`, `boundary_instants_differ`, `mismatch`, `needs_clarification`, `stale`. It does not contain `no_match`, `No-match`, or `checked pairs`. The exported Markdown contains the no-match sentence and the synthetic label. Underscores in that Markdown are escaped, so a raw search for `boundary_instants_differ` in the file is false even though the finding is on screen.

Fix: render the same scoped sentence on the dossier.

**7. Medium.** [desk.py:57](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:57). Section 2 asks the queue row for unresolved checks. The syn row keys are `train_no`, `service_date`, revisions, `changed_fields`, `next_owner`, `local_review`, `unresolved_fields`. Grades and the border finding appear only after the dossier opens.

Fix: put the check summary on the queue row.

**8. Medium.** [review.py:98](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/review.py:98). After applying `follow_up_answered`, every stale follow-up is forced to `reopened`. A later answer stays invisible. N6 reopen-on-new-revision itself works (see checks). The in-repo test only covers that reopen, not a later answer.

Repro after the v3 import: answer the stale follow-up, status remains `reopened`.

Fix: an answer newer than the revision that caused staleness can set `answered`. Force `reopened` only until that answer.

## Checks and results

Temporary workspace `/tmp/nightdesk-p1-review-grok-ws`. `PYTHONDONTWRITEBYTECODE=1`. `PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/nightdesk-p1-review-grok'`. Commands used `--offline --no-sync` so the frozen environment was not rewritten. No `data/` access. No network fetch. Repros under `/tmp/nightdesk-p1-repro-run`.

| Check | Result |
|---|---|
| `uv run --offline --no-sync pytest -q` | **295 passed** in 3.31s, exit 0. Log: `/tmp/nightdesk-p1-review-grok-logs/pytest.txt` |
| `uv run --offline --no-sync python tests/phase0_acceptance.py` | **PHASE0_EXIT:0**. Unconfirmed ingest exit 1. Six steps identical with credential vars unset and OS network denied. JSON/XLSX sniff, ingest, merged-header refusal, flatten, ingest. Log: `/tmp/nightdesk-p1-review-grok-logs/phase0.txt` |
| Snapshot SHA256 | **after_entries=89 mismatches=0** |
| Licences | Header scan of installed `METADATA`. MIT, BSD, Apache-2.0, PSF-2.0, or a permissive AND/OR of those (numpy includes CC0-1.0; pillow MIT-CMU). **certifi 2026.10.23 is the only MPL-2.0 package.** `nightdesk` itself has no licence field. The empty lists in `repro3.txt` were a script parser bug. |
| CLI syn | Unconfirmed batch exit 1. v1 `e49369d7…` and v2 `6b14706e…` complete, rejected 0, label Synthetic. Outcomes A, B, `time_unknown`, 1 unlocated. Border `mismatch:boundary_instants_differ`. Unreviewed point `unknown:boundary_point_not_reviewed`. Reimport v2 keeps 8 revisions. Review not stale. v3 `44f71308…` makes 9 revisions, review stale, follow-up `reopened`. `syn_bad` `9d2c751b…` complete false, rejected 1. Reject reason `invalid_work_dates` once. |
| Audit | Seal text includes “source truth is not proved”. 75 events. Cutting the tail without a seal stays valid at count 74. Sealed verify of the cut raises `external_seal_or_count_mismatch`. A payload edit raises `invalid hash chain at seq 1`. The `audit_tamper ok=False` in `repro3.txt` was a malformed-JSON script bug. |
| Isolation | Loading a revision id from another bundle raises `FileNotFoundError`. |
| App | Streamlit AppTest, no browser. Exception none. Screen shows the train, grades, unlocated, boundary mismatch, the decision, and stale. Export wrote both `dossier-*.md` and `dossier-*.json` under the temp bundle. |

## What held

Phase 0 acceptance is unchanged. Revision ids ignore capture time and path. Identical reimport does not create a revision. v3 stales the decision and reopens the follow-up. Bundles do not leak. The synthetic label is present. W1 rejects surface once. Mapping confirmation is required. Border exact-instant mismatch and unreviewed-point unknown match §2. The audit chain matches P1.12, including the written limit that it does not prove source truth. The time suite passed; no separate time blocker.

## Score

**6/10. Changes requested.** Do not start Phase 2. The syn queue, dossier, review, export, stale import, `syn_bad`, seal, and Phase 0 path are real. The five high bugs hide a missing time from R2, drop a valid predecessor, grade the worked example B, attach a line-only work to the wrong stretch, and leave a works-only exposure change off the desk.
