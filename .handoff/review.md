# Review ledger

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P0-PLAN-01 | Sol: compare raw-path command must resolve accepted same-bundle ingests; reject missing/stale/ambiguous artifacts. | blocker | fixed | Coordinator: phase0-plan revision2 pins resolution, rejects and tests; council recheck pending. |
| P0-PLAN-02 | Sol/Opus: exact network denial, credential unset wrapper and fresh bundle roots missing. | blocker | fixed | Revision2 exact sandbox-exec wrapper; actual probe PermissionError, uv starts successfully (phase0-baseline.txt). |
| P0-PLAN-03 | Opus: fixture schema/outcomes and decimal minute conversion unspecified before mappings. | blocker | fixed | Revision2 fixture contract specifies four v1 rows, v2 outcomes, alt equivalence and integer seconds. |
| P0-PLAN-04 | Opus: concurrent reviewers/repeated captures contaminate practice outputs; grouped rejects and safe test bundles needed. | blocker | fixed | Revision2 unique named test bundles and per-capture rejects; implementation not yet built. |
| P0-PLAN-05 | Opus: bootstrap commit lacks reviewer/stage list/data-ignore and secret checks. | blocker | fixed | Revision2 coordinator mechanical check and explicit allowed staged paths; no research staged. |
| P0-PLAN-06 | Carbon run failed after feedback: Requests ending with a model turn are not supported. | historical | wontfix | User retired Carbon from council; replaced by Cursor DeepSeek in latest AGENTS. No Carbon approval required. |

2026-11-17: Independent Kiro Opus medium APPROVED revision2, verifying P0-PLAN-01..05 addressed. Task bf360436-2538-4af0-a90c-95d3538e2130; raw verdict delivered to coordinator. Coordinator Codex approves same plan. Council only at end of Phase0.

## Phase 0 council round 1 — 2026-11-17

User authorised finishing with Opus and Sol after Cursor DeepSeek failed weekly usage eligibility. DeepSeek: no score, not replaced.
Reports: council-r1-opus.md (6.5/10, CHANGES REQUESTED), council-r1-sol.md (8/10, CHANGES REQUESTED).
Both completed and product snapshot hashes matched. Fix round 1 follows; no Phase 1 scope.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P0-R1-S1 | Missing times rejected or accepted without unresolved raw/reason (Sol). | blocker | fixed | tests/test_mapping.py: required/optional missing clock, missing datetime, and missing joined time stay unresolved; 191 tests pass. |
| P0-R1-S2 | JSON absent key padded to null, hiding field-presence change (Sol). | blocker | fixed | tests/test_generic.py absent-to-null field diff; sparse JSON extra regression and sniff missing-aware lookup; 191 tests pass. |
| P0-R1-O1 | Case aliases bypass NDA/cross-bundle path guard (Opus F1). | high | fixed | Filesystem identity containment; case-alias guard regression passes on this host. |
| P0-R1-O2 | Per-row audit appends reread log quadratically; no writer lock (Opus F2). | medium | fixed | Locked batch append; 2000-row test reads history twice; 4-process 80-event seq check passes. Benchmark 3000=0.174s / 6000=0.316s. |
| P0-R1-O3 | Huge numeric exponents hang/abort whole ingest instead of rejecting row (Opus F3). | medium | fixed | Technical limits in config before Decimal-to-int; huge positive/negative exponents and oversized mantissa reject only bad rows. |
| P0-R1-O4 | Mapped/unmapped modes compared as compatible records (Opus F4). | medium | fixed | Mode/dataset mismatch refused before comparison/export; regression tests pass. |
| P0-R1-O5 | Unknown enum raw value lost (Opus F5). | low | fixed | Unknown enum keeps canonical unknown and raw value/reason in unresolved; regression passes. |
| P0-R1-O6 | Whitespace-only required key accepted (Opus F6). | low | fixed | Required whitespace key rejects; generic whitespace key stays uncertain; tests pass. |
| P0-R1-O7 | HTML entity numeric hash escaped in Markdown (Opus F7). | low | fixed | Plain Markdown quotes preserved without numeric-entity corruption; apostrophe and injection checks pass. |
| P0-R1-O8 | Flatten can copy between known bundle roots (Opus F8). | low | fixed | Flatten --bundle validates source and explicit output against known bundle roots; cross-root regression passes. |
| P0-R1-O9 | Typo in comparison key lacks clear missing-column error (Opus F9). | low | fixed | Missing comparison key explicitly named; real CLI regression returns 1. |
| P0-SELF-LIC | Existing requests pulls MPL-2.0 certifi, outside dependency rule. | medium | fixed | Removed unused requests and five network packages including MPL-2.0 certifi; uv.lock updated; frozen offline sync exits 0. |

## Phase 0 council round 2 — APPROVED

Opus 9/10 and Sol 9/10 independently approved the same 34-file snapshot, with all hashes matching before/after. Exact reports: council-r2-opus.md and council-r2-sol.md. Both reran 191 tests normally and network-denied plus the real CLI acceptance path. One fix round; two full review rounds. User waived unavailable DeepSeek; no replacement or score.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P0-LATER-JSON | Extremely deep JSON / huge native JSON integer can fail the whole unreadable file with a low-level error. | nonblocking | wontfix | Opus R2 approved: exits 1 without writing output; clearer file-level error handling deferred. |
| P0-LATER-CRASH | Capture rename and audit append are not one crash-atomic transaction. | nonblocking | wontfix | Opus R2 identified a possible gap but did not test it; no crash-recovery claim. Revisit with Phase 1 store/audit. |
| P0-LATER-HARDLINK | Deliberately hard-linking data out of NDA root defeats path ancestry classification. | nonblocking | wontfix | Opus R2 explicitly excluded this intentional user action as a bypass; symlinks/case aliases are checked. |
