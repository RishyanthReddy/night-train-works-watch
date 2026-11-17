I found no Phase 1 blocker, but two medium findings should be fixed before the phase closes. Verdict: approved with changes, **8/10**. All 89 snapshot SHA256 hashes matched before and after my checks. The checkout is unchanged: still 98 `git status` entries, HEAD d340990, and nothing written to it, `data/` or `.handoff/`.

## Checks I ran
All runs used a copy of the repo in `/tmp/nightdesk-p1-review-opus-ws` (no `data/`, `.venv` or `.git`), with `PYTHONDONTWRITEBYTECODE=1` and the `PYTEST_ADDOPTS` you gave.

- **Install:** `uv sync --frozen --offline` exit 0.
- **Tests:** `uv run --offline pytest -q`, run with networking denied (`sandbox-exec`) and the five credential variables unset: 295 passed, exit 0.
- **Phase 0 acceptance:** `uv run --offline python tests/phase0_acceptance.py` exit 0. The JSON/XLSX and merged-header flatten checks passed with networking denied.
- **Import (CLI, bundle `test-opus`):**
  - Importing a capture before its mappings were confirmed was refused (exit 1); `capture confirm` then exit 0.
  - v1 and v2 imported as `complete=True`. syn_bad imported as `complete=False` with one reject: row 2, `invalid_work_dates`.
  - Re-importing v2 gave the same capture id, and the revision count stayed at 8.
  - v3 added one revision (9 in total).
- **Comparisons (API):**
  - The queue v1→v2 shows one row, aa:101 / 2026-11-17, with `exit.at` and `exit.raw_time` changed.
  - The dossier shows works grades A, B and time_unknown, one unlocated work listed separately, no-match 0 of 4 checked pairs, and border `mismatch: boundary_instants_differ`.
  - Comparing v1 with syn_bad returns `comparison_unavailable` (`filter_mismatch`).
  - Reading the v1/v2 capture ids through another bundle fails because the files are not found.
- **Review and export:** a `needs_clarification` decision plus a question for "Synthetic owner" were recorded and exported as local MD/JSON. After v3, the decision is `stale=True` and the question `reopened`.
- **Audit chain:**
  - The seal and a sealed verify both exit 0.
  - An edited event value fails with "invalid hash chain at seq 30".
  - A removed middle line fails with a seq gap.
  - A cut tail passes without the seal but fails with it (`external_seal_or_count_mismatch`).
- **App:** a headless Streamlit `AppTest` run of the queue and dossier finished with no exception and showed A/B/time_unknown, the unlocated warning and the mismatch.
- **Source-specific names:** a grep for `PTCAR`, `EURSLEEPER`, `be-es`, `Brussels` and `infrabel` in `src/nightdesk` outside `config.py` matched only a `.pyc` file.
- **Licences:** apart from certifi (approved), all installed packages are permissive. PSF-2.0 (typing_extensions), MIT-CMU (pillow) and Zlib/0BSD/CC0 parts in numpy are outside the strict MIT/BSD/Apache wording; I'm noting them, not treating them as blockers.

## Findings for you to log

**1. Medium: the queue shows a stale review as if it were current (N6, acceptance step "old review shows as stale").** [desk.py:56-60](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:56) shows `local[-1].disposition` and ignores `.stale`.
- **Reproduction:** after importing v3, the queue v1→v2 (in both the API and AppTest) shows `local_review: needs_clarification`, while `decisions()` returns `stale=True`.
- **Impact:** a planner reads an outdated local decision as current. Your stale screenshot ([phase1-accept-stale.png](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/.handoff/phase1-accept-stale.png)) shows `"stale": true` only inside the raw dossier JSON.
- **Fix:** show something like `needs_clarification (stale)` in the queue, put a visible stale label in the dossier review section, and add a test.

**2. Medium: a review is not marked stale when a newer capture reverts a subject to earlier content (A→B→A).** [review.py:52-74](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/review.py:52) orders revisions by their first `revision_created` event, not by the latest capture that contains them.
- **Reproduction:** record `accepted_locally` on the v3 revision, then import a v4 that is a copy of v1 with only the label changed (`complete=True`). The v3 decision stays `stale=False`, even though the queue v3→v4 shows a changed `exit.at`. Going the other way, a decision on the v1 revision stays stale for good.
- **Fix:** work out staleness from the order of capture/batch import events. A decision becomes stale when a later capture holds a different revision of the same subject. Identical re-import must still create nothing new. Add an A→B→A test.

**3. Low/Medium: a revision's source record can be edited without detection.** [store.py:50-60](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/store.py:50) checks the hash of the payload only, which is what the spec defines; nothing checks `Revision.source`.
- **Reproduction:** changing `source.licence` to `CC0` and `url_or_path` to `/elsewhere/forged.csv` in a revision file still loads cleanly, and `audit verify` stays valid.
- **Impact:** the dossier's provenance and its "synthetic" label can be wrong without any error.
- **Fix:** record the source's sha256 in the `revision_created` event, or cross-check it against the capture's `rows.jsonl` when loading.

**4. Low: an unrecorded rule change on grade A.** [match.py:85-89](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/match.py:85) requires the work's line to be known before giving grade A.
- **Reproduction:** syn-A with `line=None`, both point ids on the ordered path and the time overlapping, gets B with `line_unknown`. KICKOFF §7's worked example (VILVOORDE→MECHELEN, a work with no line) says "A if the time overlaps", while the §2 table lists "line unknown" under B.
- **Impact:** works with no line, like the RFC ones, can never reach A.
- **Fix:** have the user choose between the two readings, then record the choice in `decisions.md`.

**5. Low: `raw_time` holds the parsed ISO value, not the source text.** At [gates.py:78-79](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/gates.py:78), a source time of `2026-11-17 23:00` becomes `raw_time` `2026-11-17T23:00:00+01:00`. Every time change is therefore listed twice in the queue (`exit.at` and `exit.raw_time`). Fix: keep the original cell text.

## Confirmed working
- **Time rules:** UTC half-open intervals, the weekday taken from the local start date, clipping at the inclusive end date, and refusal to guess on clock-change nights.
- **Revisions and links:** content-addressed and immutable, with no automatic replacement of older revisions. Journey links are explicit, and unlinked legs stay unknown.
- **Comparisons:** added/removed lists appear only when both captures are effectively complete with the same filter. The border check compares the same event kind at the same reviewed point with exact instants.
- **Batch captures:** child provenance is kept, and syn_bad comes through as incomplete with its reason.
- **Isolation, export and UI:** bundles are isolated, the dossier export is local only with escaped content, and the UI is plain.

Findings 1 and 2 must be fixed before Phase 1 closes. 3–5 can go in the ledger or be fixed at the same time.
