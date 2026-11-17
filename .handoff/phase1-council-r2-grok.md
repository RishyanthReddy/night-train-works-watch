Phase 1 round 2, Grok. Verdict: **changes requested. 6/10.** The checkout product bytes were not edited. Snapshot `.handoff/phase1-council-r2-snapshot.json`: **90 entries, 0 mismatches** before and after. HEAD `d340990`, branch `phase1`.

## Blockers

**1. High.** [match.py:58](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/match.py:58). A line-only clock is graded B on a segment whose line is unknown. `segment.line in {work.line, None}` treats a station-area hop (`be:0/…`, which `line_for_matching` turns into `None`) as the named line.

Repro: points a 22:00 `be:0/100`, b 22:10 `line_dep=zz:9`, c 23:00 `zz:9`. Work `line=zz:9`, no endpoints, clock 22:00–22:05. Result `B`, overlap `2026-11-17T21:00:00+00:00`–`21:05:00+00:00` (the throat). The `zz:9` segment starts at 22:10 and does not overlap. The same work at 22:15–22:20 is `B` on `21:15Z`, which is the named line. [tests/test_phase1_council.py:163](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/tests/test_phase1_council.py:163) only uses `zz:1` and `zz:9`.

Impact: the desk shows a grade B exposure on a hop the line rule has already excluded.

Fix: overlap only segments whose line equals the work line. If the named line does not overlap and a segment line is unknown, return `time_unknown`. Keep no-match when every segment line is known and different.

**2. High.** [desk.py:42](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:42) and [desk.py:125](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:125). The queue only pairs path legs that exist in both captures. A complete-capture removal is stored on the `ChangeSet` and never becomes a row. [app.py:112](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/ui/app.py:112) then says there is no comparable change.

Repro, both captures `complete=true`, `compare_captures` status `compared`:

- The only path leg is absent from the later file. `removed` has one revision id. `queue` is `[]`.
- `cc:303` is dropped from the three-leg synthetic set. Queue trains are `aa:101` and `bb:202`. The removed id appears only inside the neighbor dossier’s `capture_comparison.removed`.

Impact: N2’s declared removal does not reach the planner. An empty queue reads as “nothing changed.”

Fix: when the R2 gate passes, add one queue row per added or removed path leg and operating date, with per-side presence, and open the dossier on the revision that exists. Keep the word cancellation out.

**3. Medium.** [store.py:68](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/store.py:68). Load keeps a non-null predecessor from the revision JSON and applies `predecessor_recorded` only when that field is null.

Repro: record predecessor A, conflict on B is audited, file bytes stay identical, `load_revision` returns A. Writing B into the JSON makes `load_revision` return B. `audit verify` stays valid.

Impact: first-valid-wins is not true of the revision the dossier loads.

Fix: use the first `predecessor_recorded` event as the relationship. If the file field disagrees, raise.

**4. Medium.** [mapping.py:541](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:541) and [batch.py:124](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/batch.py:124). Load trusts `complete` from JSON. The batch id hash does not cover `declared_complete`, `complete`, or `incomplete_reasons`. Rejected rows are counted and then ignored.

Repro:

- A capture with one reject reloads as `complete=true`, `incomplete_reasons=[]` after that flag is edited.
- A manifest with `complete: false` imports as `unknown` / `incomplete_capture`. The `batch_imported` event stores `complete: false`. After the same flag edit, `load_batch` returns `complete=true` and `check_boundary` on equal 23:00 instants returns `agrees_on_checked_fields`. `audit verify` stays valid.

Impact: a positive border result is produced from a capture the audit still records as incomplete. The in-memory rule is right when the object is honest: no capture → `capture_completeness_unknown`; `complete=false` → `incomplete_capture`; a real complete v1 pair → `agrees_on_checked_fields`.

Fix: recompute effective completeness on load from the declaration, rejects, uncertain identity, and child captures. Refuse the file when the stored flag disagrees, and include the declaration in the batch identity check.

## Checks and results

Temporary tree `/tmp/nightdesk-p1-r2-grok-ws`. `PYTHONDONTWRITEBYTECODE=1`. `PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/nightdesk-p1-r2-grok'`. Runs used `uv run --offline --no-sync` inside `sandbox-exec` `(deny network*)`, with `MISTRAL_API_KEY`, `NS_API_KEY`, `SWISS_OTD_TOKEN`, `DB_CLIENT_ID`, `DB_API_KEY`, and `TRAIN_ARCHIVE_TOKEN` unset. No `data/` read in the checkout. Repros under `/tmp/nightdesk-p1-r2-repro-run`.

| Check | Result |
|---|---|
| `uv run --offline --no-sync pytest -q` | **309 passed** in 13.96s, exit 0. Log `/tmp/nightdesk-p1-r2-grok-logs/pytest.txt` |
| `python tests/phase0_acceptance.py` | **PHASE0_EXIT:0**. Six steps matched with credentials unset and the network denied. JSON/XLSX sniff and ingest, merged-header refusal, flatten, ingest. Log `/tmp/nightdesk-p1-r2-grok-logs/phase0.txt` |
| Snapshot SHA256 | **90 / 0 mismatches** before and after |
| Licences | Installed `METADATA`: **certifi 2026.10.23 is the only MPL-2.0 package.** `nightdesk` has no licence field |
| Core names | `PTCAR`, `EURSLEEPER`, `be-es`, `infrabel`, `Brussels` in `src/nightdesk` outside `config.py`: no matches |
| CLI syn | Unconfirmed import exit 1. v1 and v2 `complete=true`, rejected 0. `syn_bad` `complete=false`, one `invalid_work_dates`. `exit.raw_time` is `2026-11-17 23:01` |
| API | Missing work line is **A** with `line_unknown`. `path_unresolved` stays **B**. Neighbor `bb:202` is queued with `boundary_instants_differ` and no field diffs. Dossier grades A, B, `time_unknown`, unlocated separate, no-match **0 of 4**. Second dossier leaves the audit count unchanged. Blank time and `not-a-kind` stay `complete=true` and unresolved. Removed 17 November shows `before_operating=true`, `after_operating=false`, with no cancellation wording |
| Review | Answer closes. A later capture of different content reopens. A return to existing bytes adds no `revision_created` and the queue shows `needs_clarification (stale)` |
| Predecessor happy path | Later valid link is stored, file bytes unchanged, conflicting link audited, first link kept |
| Source tamper | Edited `licence` / path raises on load |
| Audit | Seal text includes “source truth is not proved.” Sealed verify of a cut tail exits 1 with `external_seal_or_count_mismatch` |
| AppTest | No exception. Queue columns include `checks_before`, `checks_after`, and `local_review`. Unresolved reasons in that row include `recurrence_unknown` and `unlinked`. Dossier text contains `No-match pairs: 0 of 4 checked pairs only` and `Stale local review` |
| Screenshots viewed | [phase1-r2-queue.png](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/.handoff/phase1-r2-queue.png) shows check columns and the unchanged `bb:202` row. [phase1-r2-works.png](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/.handoff/phase1-r2-works.png) shows A, B, `time_unknown`, the no-match sentence, and a separate unlocated warning. [phase1-r2-stale.png](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/.handoff/phase1-r2-stale.png) shows the stale warning. [phase1-r2-evidence.png](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/.handoff/phase1-r2-evidence.png) shows the work payload. [phase1-r2-removed-queue.png](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/.handoff/phase1-r2-removed-queue.png) and [phase1-r2-removed-dossier.png](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/.handoff/phase1-r2-removed-dossier.png) show 17 November `before=true` / `after=false` and the not-cancellation caption |

`git status --short` was 114 at the start of this review and 116 at the end. The 90 hashed product paths did not change. I did not write in the checkout.

## Score

**6/10. Changes requested.** The synthetic queue, dossier, stale review, scoped no-match line, raw source time, and Phase 0 path hold. A line-only work is still attached to the wrong hop, and a complete-capture removal still disappears from the queue.
