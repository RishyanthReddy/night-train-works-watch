# Phase 1 council R3 — Grok

**APPROVE. 9/10.**

No reproducible Phase 1 blocker. The R2 findings I re-checked are fixed in the product, not only in the tests named for them. Phase 2 and later were not reviewed. I did not edit the checkout, `.handoff/`, or `data/`.

## Snapshot

`.handoff/phase1-council-r3-snapshot.json`: **92 entries, 0 missing, 0 mismatches** before the runs and again after the last command. HEAD `d340990773cb70a88584194f571064e8ec1fb06d`, branch `phase1`. No `data/` path is in the snapshot.

## Commands and results

All of these used the temporary tree `/tmp/nightdesk-p1-r3-grok-ws` (checkout copy, no `data/`, `.venv` symlinked and not rewritten). `PYTHONPATH` pointed at that copy. `PYTHONDONTWRITEBYTECODE=1`. Credentials `MISTRAL_API_KEY`, `NS_API_KEY`, `SWISS_OTD_TOKEN`, `DB_CLIENT_ID`, `DB_API_KEY`, and `TRAIN_ARCHIVE_TOKEN` were unset. Network denial was `sandbox-exec -p '(version 1)(allow default)(deny network*)'`. A loopback connect under that profile returned errno 1 (`EPERM`).

| Check | Exit | Result |
|---|---|---|
| `uv run --offline --no-sync pytest -q --tb=line` with `PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/nightdesk-p1-r3-grok-basetemp'` | 0 | **325 passed** in 21.88s. Log `/tmp/nightdesk-p1-r3-grok-logs/pytest.txt` |
| Same wrapper, `tests/test_phase1_integrity_scale.py::test_two_2000_row_captures_have_bounded_audit_and_capture_reads -s` | 0 | 1 passed in 9.09s. Log `/tmp/nightdesk-p1-r3-grok-logs/scale.txt` |
| `tests/phase0_acceptance.py` from the copy | 0 | Six steps matched with credentials unset. JSON/XLSX sniff and ingest, merged-header refusal, flatten, ingest. Network-denial probe errno 1. Log `/tmp/nightdesk-p1-r3-grok-logs/phase0.txt` |
| Independent probes `/tmp/nightdesk-p1-r3-grok-logs/edge.py` | 0 | 14 PASS, 0 FAIL. Log `/tmp/nightdesk-p1-r3-grok-logs/edge2.txt` |
| CLI path `/tmp/nightdesk-p1-r3-grok-logs/cli_check.py` | 0 | Unconfirmed import exit 1; confirm; v1/v2 import `complete=True` rejected 0; idempotent v2 reimport; review + question; dossier export; v3 makes the review stale and reopens the question; `syn_bad` `complete=False`, one `invalid_work_dates`; seal and verify; cut tail exit 1. Log `/tmp/nightdesk-p1-r3-grok-logs/cli.txt` |

Synthetic scaling on this machine, from the scale test print: first 2000-row ingest **1.542s**, second 2000 with 2000 predecessor links **2.85s**, snapshot of the second capture **0.739s**, all **4000** revisions **1.419s**, one `record_decision` **1.761s**. The test's own counters stayed within 6 audit reads and 6 capture reads on ingest, and within 2 and 2 on snapshot and `revisions()`. Those are local timings, not a throughput guarantee. They are not the builder's 1.715/3.097/1.578 figures.

Core name check on `src/nightdesk`: `PTCAR`, `EURSLEEPER`, and `be-es` have no matches. `infrabel` and `Brussels` appear only in the dataset assumption in `config.py`. Installed metadata: **certifi 2026.10.23 is the only package whose License field is MPL-2.0.** That Streamlit transitive exception is the one already approved.

## What I reproduced

- Operation-scoped `ReadSession` (`store.py`). No module-level session. A second session does not see the first session's revision cache. Passing one session into another bundle raises `cross_bundle`. Import of 2×2000 does not reread the audit once per row.
- First `predecessor_recorded` is what `load_revision` returns. The revision file stays `predecessor: null`. A later conflicting link is audited as `predecessor_rejected` and does not replace the first. Writing the other predecessor into the JSON raises `revision_predecessor_metadata_mismatch`. `audit verify` stays valid.
- Editing a capture or batch `complete` flag, or the stored batch manifest, is refused on load. `syn_bad` stays incomplete with `invalid_work_dates`. A declared-incomplete batch cannot be flipped to complete in `batch.json`.
- Batch revision ids follow manifest role order. A manifest with `works` before `legs` does not match alphabetical role order (4 work revisions, then the legs).
- Whole-leg removal and addition reach the queue, dossier, local review, follow-up, and Markdown/JSON export. Presence is true/false. The export does not say cancellation. An incomplete one-sided capture is `record_presence_unknown`, presence null, and `removed` is empty.
- Removed operating date: the before boundary is `agrees_on_checked_fields`; the after boundary is `operating_dates_differ`; queue `checks_after.border` matches the dossier. Using the before date set would have hidden that mismatch.
- Line-only `zz:9` on a `be:0/100` throat then `zz:9` segment: 22:00–22:05 is `time_unknown` / `line_unknown_for_pass_window`. 22:15–22:20 is `B` with overlap `2026-11-17T21:15:00+00:00`. A known different line with no endpoint on the path is no-match.
- Both exact endpoints on the ordered path with line `zz:other` stay **A** with `line_mismatch`. The same case with `path_unresolved` stays **B**.
- Resolved off-path endpoints and no line, clock overlapping the run: **B** / `not_on_ordered_path`, queued when path fields are unchanged (`changed_fields` empty, B count +1).
- One train/date with a removed leg and a changed sibling is one queue task, `multiple_source_leg_changes`, both legs retained. Each leg's dossier shows its own presence or field diff.
- `comparison_checked` does not grow when a review disposition or follow-up owner changes. It does grow for a new capture pair.
- Forged revision `licence` and an edited `rows.jsonl` are refused. Synthetic v1→v2 dossier grades are A, B, and `time_unknown`, with a separate unlocated work and border `boundary_instants_differ` once the link and reviewed point are selected. No-match count on that pair is 0.

## Not a blocker

**Low.** `desk.py` lines 154–156 set a grouped train/date `before_operating` / `after_operating` to true when any source leg is true. An independent case with one removed `aa:101` leg and one changed sibling shows the task `after_operating: true` while that removed leg is `after_operating: false`. `leg_changes` still has both, `change_kind` is `multiple_source_leg_changes`, and the dossier for the removed revision has `after: null`. The queue table does not render `leg_changes`; the dossier tab starts with no source leg selected (`app.py` around lines 128–132). I am not treating the summary OR as a Phase 1 blocker.

A work with both endpoints off the path **and** a line that matches no segment returns no-match (`match_work` is `None`), not W5 B. Section 2 lists a line verified not to overlap as no-match. The literal off-path B case above has no line. I did not treat this as a defect.

## Screenshots

I viewed `.handoff/phase1-r3-removed.png` and `.handoff/phase1-r3-added.png`. They show `aa:101 / 2026-11-17`, synthetic, with the source record absent on one side and present on the other, and the sentence that absence does not state an operational meaning. I also viewed `.handoff/phase1-r2-works.png` (A, B, `time_unknown`, no-match 0 of 4, separate unlocated warning), `.handoff/phase1-r2-stale.png` (stale local-review warning), and `.handoff/phase1-r2-evidence.png` (work payload for `syn-A`).

I did not produce a new browser capture. I am not claiming a fresh visual for the removed-date boundary or the multi-leg selector. Those paths passed current AppTest inside the 325.

## Score

**9/10. Approve.** Queue, dossier, export, review, stale reopening, scoped works grades, R2 integrity, and the Phase 0 CLI path hold on synthetic fixtures. The remaining note is the grouped operating flag, and the removed-date / multi-leg UI was not newly screenshotted in this review.
