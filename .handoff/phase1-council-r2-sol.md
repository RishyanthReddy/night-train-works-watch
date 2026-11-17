**Changes requested — 8/10.** Two reproducible Phase 1 blockers remain:

1. **High — Whole added/removed legs disappear from the planner workflow.** [desk.py:42](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:42) selects only subjects present in both captures. With one leg in complete v1 and none in complete v2, `compare_captures` correctly reports removal, but the queue is empty and no dossier can open. Reversing the captures also hides the addition. Carry one-sided subjects through queue/dossier selection under R2, showing explicit source presence without inferring cancellation.

2. **Medium — Removed-date dossier drops a valid boundary mismatch.** [desk.py:170](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:170) selects the old revision for a removed date, then checks membership against after-capture legs. With aa losing November 17 while adjacent bb retains it, the queue correctly reports `mismatch: operating_dates_differ`; opening that exact row returns `findings=[]` and `border_not_checked`. Keep after-side boundary checking bound to the after revision, separate from display/run fallback.

Independent checks completed:

- **309 tests passed**, networking denied and six credential variables unset.
- **Phase 0 acceptance passed**, including alternate mappings, JSON/XLSX and flatten/import.
- Real CLI/API and fresh AppTest checks passed the synthetic review, export, stale-warning and reanswer flows.
- Viewed all six supplied R2 screenshots.
- **All 90 SHA256 hashes matched before and after.**

No checkout edits, delegates, network fetches, commits or pushes. [Detailed report and requirement coverage](/tmp/nightdesk-p1-r2-sol-review/verdict.md); [reproduction script](/tmp/nightdesk-p1-r2-sol-review/edgecases.py) and [results](/tmp/nightdesk-p1-r2-sol-review/edgecases.log).
