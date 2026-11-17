**Verdict: changes requested — 7.5/10.** Four reproducible Phase 1 blockers:

1. **P1-SOL-01 · High — Removed operating dates disappear.** [desk.py:54](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:54) builds queue rows from new operating dates only. Changing `17;18 November` to `18 November` hides the removed 17th; opening its dossier also fails. Use both revisions’ dates, show per-side presence, and allow inspection of the removed date without inferring cancellation.

2. **P1-SOL-02 · Medium — Executed checks are absent from audit.** [desk.py:85](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/desk.py:85) computes comparisons, works exposures and boundary findings without recording them. The synthetic dossier produced A/B/unknown outcomes and a mismatch while audit count remained **53 → 53**. Record selected inputs, rule versions and results at the application boundary, with deduplication for rerenders.

3. **P1-SOL-03 · Medium — Work evidence cannot be inspected in the dossier.** [export.py:128](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/export.py:128) exports exposure hashes and references but omits work payloads. Descriptions, endpoints, clocks, effects and unchanged `extra` fields are unavailable in the report/UI. An unmapped synthetic field survived storage but disappeared from the dossier. Include referenced work records and selected run evidence, with escaped source/extra display.

4. **P1-SOL-04 · Medium — Reopened questions cannot become answered.** [review.py:98](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/review.py:98) unconditionally overlays `reopened` whenever the bound revision is stale. Answer → import v3 → answer again records `follow_up_answered`, yet still returns `reopened`. Derive status chronologically, allowing an explicit later answer or revalidation to close the question.

Independent verification completed:

- **295 tests passed** with the requested environment settings.
- Phase 0 acceptance passed, including network-denied CLI execution, alternate mappings, JSON/XLSX and flatten/import.
- Synthetic CLI/API checks confirmed complete captures, expected exposure/border outcomes, idempotence, rejected-work incompleteness and bundle refusal.
- Independent Streamlit AppTest completed import → queue → dossier → review/question → export without app exceptions. Supplied works screenshot inspected.
- CLI audit verification accepted the seal and rejected both tail deletion and an edited event.
- **All 89 snapshot SHA256 values matched before and after.**

No checkout edits, delegation, network fetches, commits or pushes. Detailed findings and reproduction locations are in [the review report](/tmp/nightdesk-p1-review-sol-manual/verdict.md).
