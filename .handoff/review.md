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

## Phase 1 council round 1 — changes requested

Reports phase1-council-r1-{opus,sol,grok}.md. All89 product hashes matched. Scores Opus8, Sol7.5, Grok6.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P1-O1 | Queue hides stale flag | medium | fixed | Queue stale label + prominent UI warning; council regressions and viewed phase1-r2-stale.png. |
| P1-O2 | A→B→A capture does not stale review | medium | fixed | Decision basis uses capture/batch observations; A→B→A/new re-review regression passes. |
| P1-O3 | Source metadata can be edited independently | medium | fixed | First SourceRef checked against retained capture and audit SHA256; tamper regression passes. |
| P1-O4/G3 | Line-unknown grade A spec ambiguity | high | fixed | Explicit A definition/worked example chosen; missing line shown, exact endpoints A; GTFS unresolved cap retained. test_match.py passes. |
| P1-O5 | raw_time uses parsed value | low | fixed | Mapping retains original boundary cells; raw_time regression passes. |
| P1-S1 | Removed operating dates hidden | high | fixed | Union operating dates + per-side presence; removed-date API test and viewed removed queue/dossier screenshots. |
| P1-S2 | Checks absent from audit | medium | fixed | Locked deduplicated comparison/dossier audit events with selected refs, rule versions and results; regression + real audit verify. |
| P1-S3 | Work/run evidence absent from dossier | medium | fixed | Work records/source/extra and selected run included in JSON/escaped MD/UI; regression and viewed evidence screenshot. |
| P1-S4/G8 | Reanswered stale follow-up never closes | medium | fixed | Chronological observations/answer events; answer→new revision→reanswer→new revision regression passes. |
| P1-G1 | Unresolved warnings mark captures incomplete | high | fixed | Unresolved time/enum warnings retained without making capture partial; typed completeness/R2 regressions pass. |
| P1-G2 | Valid later predecessor dropped | high | fixed | First explicit predecessor stored as append-only metadata, conflict audited; immutable bytes and later-link regression passes. |
| P1-G4 | Line-only work matches wrong stretch time | high | fixed | Line-only matching uses that line's segment pass windows; wrong-stretch no-match and matching-stretch B regressions pass. |
| P1-G5 | Works-only changes absent from queue | high | fixed | Checks compared for unchanged legs; A→no-match remains queued and dossier opens; unrelated unlocated-only changes stay global. |
| P1-G6 | No-match count absent from UI | medium | fixed | Scoped no-match sentence rendered; viewed phase1-r2-works.png. |
| P1-G7 | Unresolved check summary absent from queue | medium | fixed | Before/after checks and unresolved reasons on queue rows; tests and viewed queue show check columns. |
| P1-SELF1 | Incomplete equal-date boundary capture can agree | medium | fixed | Positive boundary check requires complete matching capture evidence; equal-date incomplete and missing-evidence regressions pass. |

## Phase1 council round2 — changes requested, fixes verified

All three completed against90 matching product hashes: Opus6.5/Sol8/Grok6. Reports phase1-council-r2-*.md. Fixes applied only after reviews finished.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P1-R2-S1 | Whole added/removed PathLeg subjects excluded by pair intersection, so queue/dossier cannot open them. | high | fixed | Prepared optional-side queue/dossier/source presence/review/export changes; tests cover complete removal/addition and incomplete/missing-file unknown presence.  Evidence: main 325-test offline pass; test_phase1_presence.py / test_phase1_integrity_scale.py; phase1-r3 CLI and scaling logs. |
| P1-R2-S2 | Removed-date dossier uses old revision for after-boundary membership, dropping queue's operating_dates_differ finding. | medium | fixed | Prepared separation of after boundary identity and display/run fallback, with queue/dossier agreement regression.  Evidence: main 325-test offline pass; test_phase1_presence.py / test_phase1_integrity_scale.py; phase1-r3 CLI and scaling logs. |

All R2 reports now delivered: Opus6.5/Sol8/Grok6, changes requested. Their90 product hashes matched before/after. User requested a new continuation goal; created after get_goal returned null.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P1-R2-G1 | Unknown/station-area line segments falsely provide a line-only B exposure. | high | fixed | Match only verified named-line spans; unresolved overlapping line spans stay unknown.  Evidence: main 325-test offline pass; test_phase1_presence.py / test_phase1_integrity_scale.py; phase1-r3 CLI and scaling logs. |
| P1-R2-G3 | Raw JSON predecessor can override the first audited predecessor. | medium | fixed | Make audit metadata authoritative and refuse disagreement.  Evidence: main 325-test offline pass; test_phase1_presence.py / test_phase1_integrity_scale.py; phase1-r3 CLI and scaling logs. |
| P1-R2-G4 | Edited capture/batch completeness flags bypass rejects/declarations. | medium | fixed | Recompute/validate effective completeness and commit source declarations/artifacts.  Evidence: main 325-test offline pass; test_phase1_presence.py / test_phase1_integrity_scale.py; phase1-r3 CLI and scaling logs. |
| P1-R2-O1 | Repeated audit/capture reads make typed loading/import/review quadratic. | high | fixed | Introduce an operation-scoped reader/index and prove scaling on synthetic captures.  Evidence: main 325-test offline pass; test_phase1_presence.py / test_phase1_integrity_scale.py; phase1-r3 CLI and scaling logs. |
| P1-R2-O2 | Conflicting line attribution suppresses exact-endpoint exposure as no-match. | high | fixed | Keep strong point evidence; show line disagreement explicitly.  Evidence: main 325-test offline pass; test_phase1_presence.py / test_phase1_integrity_scale.py; phase1-r3 CLI and scaling logs. |
| P1-R2-O3 | A graded B exposure is hidden from the works-only queue by a separate attached predicate. | medium | fixed | Use the canonical exposure outcome consistently; preserve explicit W5 B semantics.  Evidence: main 325-test offline pass; test_phase1_presence.py / test_phase1_integrity_scale.py; phase1-r3 CLI and scaling logs. |

## Phase1 council round3
Opus APPROVE9/10; Sol CHANGES REQUESTED8/10; Grok APPROVE9/10. All three finished; source freeze ended before applying two-file proposal. Report phase1-council-r3-opus.md;92 hashes matched in review. No product edits while reviews remain active.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P1-R3-O1 | Remaining linked leg silently loses a boundary check when adjacent source leg is no longer observed. | low-medium, nonblocking | fixed | Builder verified loop only checks present adjacent pairs; reproduce missing-neighbour explanation before choosing bounded fix after all reviews.  Applied desk.py/index/presence fix;330 main offline tests pass, actual800-leg queue1.185s, CLI/Phase0 pass; exact proposal visual evidence matches applied code. R4 approval pending. |
| P1-R3-O2 | no_run_selected can appear twice in unresolved summary. | cosmetic, nonblocking | fixed | Builder verified set built then appended unconditionally in _checks; remove duplicate after review freeze ends.  Applied desk.py/index/presence fix;330 main offline tests pass, actual800-leg queue1.185s, CLI/Phase0 pass; exact proposal visual evidence matches applied code. R4 approval pending. |

| P1-R3-S1 | Boundary enumeration scans all leg pairs per selected leg, cubic queue cost;800 legs took58.965s in reviewer synthetic probe. | high | fixed | Prepare one operation-scoped adjacent-candidate index, preserving existing findings; deterministic bounded-enumeration regression and actual queue benchmark needed.  Applied desk.py/index/presence fix;330 main offline tests pass, actual800-leg queue1.185s, CLI/Phase0 pass; exact proposal visual evidence matches applied code. R4 approval pending. |

Grok R3 low note: grouped after_operating is any-source-leg presence, with every leg retained separately. No blocker or requested fix; preserve explicit source-leg selection rather than invent a single source winner. Report phase1-council-r3-grok.md.

Phase1 R3 final scores: Opus9 APPROVE, Sol8 CHANGES REQUESTED, Grok9 APPROVE; all92 hashes matched. R4 is a focused recheck of exactly desk.py and test_phase1_queue_scale.py against the new93-file freeze. No Phase2 permitted before user continuation.

## Phase1 council round4 — focused recheck
Opus APPROVE9/10,330 tests plus46 independent probes;93 hashes matched. Sol APPROVE9/10 with330 tests+7 independent checks,93 hashes matched; Grok APPROVE9/10 with330 tests and independent enumeration/boundary/CLI probes,93 hashes matched. All three approve. Reports phase1-council-r4-{opus,sol,grok}.md.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P1-R4-O1 | Pre-existing sequence-only candidate scoping yields many unlinked unknowns across distinct requests; reviewer800-leg case14.724s/400 unknown entries per row. | medium | fixed | User explicitly reopened and authorised fix2026-11-18. Previous disposition:  Deferred from Phase1 after unanimous R4 approval. Builder verified12500 emitted entries unknown/unlinked; no positive/automatic link. Retain as explicit efficiency/verbosity limit for later identity scoping (P2.2), which must respect explicit cross-network links rather than require equal national request ids. No Phase2 work started. |

## Phase1 council — four rounds, closed

| Delegate | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| Opus through Kiro |8/10|6.5/10|9/10|9/10 APPROVE|
| Codex Sol |7.5/10|8/10|8/10|9/10 APPROVE|
| Grok4.7 |6/10|6/10|9/10|9/10 APPROVE|

All93 R4 product hashes matched before/after every review. No remaining Phase1 blocker. Mixed-request unknown expansion is explicitly deferred above, not silently fixed or called linear in general. User checkpoint: local commit then STOP before Phase2.

## Phase1 follow-up — user explicitly authorised2026-11-18
P1-R4-O1 now fixed: explicit journey/date eligibility before pairing, single unlinked scope explanation, ambiguous source groups stay unknown until explicit UI/API revision choice; choices and scope rule audited.336 tests pass with network denied/six credential variables unset; actual mixed800leg queue1.189s with one border entry per row. Three viewed native browser screenshots. Focused council R5 pending; no Phase2 implementation. Prior deferral above is superseded by this follow-up.

## Phase1 council R5 — follow-up review
Opus APPROVE8.5/10, all94 hashes match,336 tests pass. Sol APPROVE9/10 with336 tests+16 probes, Grok APPROVE9/10 with336 tests;94 hashes matched every reviewer. All R5 finished before prepared changes applied. Product stays frozen until all finish.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P1-R5-O1 | Explicit selection of multiple distinct-sequence legs for a re-entering linked train still yields ambiguity. | medium, nonblocking per Opus | fixed | Prepare resolving explicit distinct-sequence choices without automatic grouping.  Main337 tests34.55s and actual CLI pass under OSnetworkdenial/sixcredentialsunset; reentry partial/full choice regression. Live DOM shows2mismatches, snapshot frames failed; no new visual claim. Focused R6 pending. |
| P1-R5-O2 | Excluding a neighbour via explicit choice drops the boundary explanation. | low | fixed | Prepare one sourced boundary_leg_not_selected unknown for that neighbour sequence.  Main337 tests34.55s and actual CLI pass under OSnetworkdenial/sixcredentialsunset; reentry partial/full choice regression. Live DOM shows2mismatches, snapshot frames failed; no new visual claim. Focused R6 pending. |

## Phase1 council R6 — focused three-file refinement recheck
Opus APPROVE9/10;337 tests,94 matching hashes. Sol APPROVE9/10 with337 tests+14 independent probes,94 hashes matched; Grok APPROVE9/10 with337 tests; all94 hashes match. All three approve. Reports phase1-council-r6-{opus,sol,grok}.md.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P1-R6-O1 | Conservative excluded-neighbour unknown may refer to the other selected capture without distinguishing its origin in that finding. | low, nonblocking | wontfix | Record as a bounded provenance-display limit; it never yields a positive boundary. Full selected revision ids remain in report/audit. Avoid extending this completed fix into another review cycle absent material issue. |

R5 follow-up scores: Opus8.5/Sol9/Grok9 APPROVE; R6 refinement scores: allthree9/10 APPROVE. P1-R4-O1 and P1-R5-O1/O2 closed; only accepted low provenance limit P1-R6-O1. No more fix cycle required for it.

## Phase2 council R1 — running
Exact skill members launched on127-file freeze; handles phase2-council-r1-tasks.json, builder evidence phase2-builder-evidence.md. No verdict or score received yet. Product stays frozen until all reviews finish.

## Phase2 council R1 — all complete; changes requested
Scores Opus7.5/Sol8/Grok7. All127 frozen hashes matched each reviewer and builder after completion. Reports phase2-council-r1-{opus,sol,grok}.md. Opus disclosed five ignored bytecode writes/deletions; no frozen source changed. No real key used in leak reproduction.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P2-R1-O1 | Malformed API key header ValueError leaks key into audit/UI/CLI. | high | fixed | Visible-ASCII key validation, transport exception normalization and allowlisted public errors; malformed keys never reach connection and fake key absent from audit/results. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-S1 | Malformed replay/proposal/envelope shapes crash UI or escape audited refusal. | medium | fixed | Replay Proposal/envelope shape checked at boundary, invalid proposal returnedNone, form population requires accepted object; scalar/array/missing/null regressions show visible audited refusal without exception. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-S2 | Per-stop calendar evidence rescans/reparses exceptions quadratically. | medium | fixed | Calendar/service-day evidence indexed once. At100/400dates date parses at most2*n with identical per-row proof. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-G1 | Multiple same-route/date trips abort queue without selector. | medium | fixed | Explicit run observation selector, unknown run_selection_required until chosen; no queue abort. Choices validated against selected captures and retained in audit/export, API and full-app test pass. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-G2 | Reviewer requests stop_timezone conversion rather than agency timezone. | medium | wontfix | Suggested stop-zone clock conversion rejected by official GTFS specification; all three R2reviewers uphold agency-time basis. Declared invalid stop-zone validation added and tested. No openclockfinding. |
| P2-R1-O2/G3 | Whitespace/format/role-marker variants bypass injection guard. | medium/low | fixed | NFKC/casefold, Unicode-format removal and whitespace collapse; role/ignore instruction patterns include cheap variants; pretransport regressions pass. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-O3 | Output expansion lacks technical row bound. | low-medium | fixed | MAX_GTFS_ROWS50000 bounds projected expansion before row construction; clear select_dates_or_trips refusal. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-O4 | CSV/encryptedZIP parsing errors escape refusal audit. | low | fixed | CSV/encrypted/unsupported archive errors normalized to static gtfs_unreadable_archive with audit; fieldsize/encryption regressions pass. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-O5 | Model-drafted import labelled manual. | low | fixed | CLI --drafted-by and form drafting origin; proposal sets origin; canonical proposed_by plus extra drafted_by/reviewed_by preserve evidence. Real AppTest replay→review→import passes. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-O6 | Declared mapping timezone ignored when text field absent. | low | fixed | Absent text timezone defaults to declared mapping timezone; retained timezone_basis and mapping SHA name the origin. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-O7 | Month-in-range check false rejects and misses separator variants. | low | fixed | Month declaration separators handled; membership checked across complete date range including year wrap. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |
| P2-R1-G4 | Frequencies ignored while declaring complete. | low | fixed | frequencies.txt explicitly refused as unsupported rather than silently declaring complete. test_phase2_council.py; phase2-r2-final-tests.log415passed39.00s EXIT0, OSnetworkdenied/sixcredentialsunset; Phase0/Phase2actualCLI EXIT0. |

G2 disputed conversion resolved by official spec evidence and regression: stop_times agency timezone retained, valid Europe/London stop zone does not shift instant; Not/AZone now refused. No false clock conversion adopted. Official reference URL in decisions.md. Fresh R2 council requested to assess objection.

## Phase2 council R2 — running
All three exact skill members launched on128-filefreeze; no score/verdict yet. phase2-council-r2-tasks.json and phase2-r2-evidence.md. Product stays frozen until every reviewer finishes.

### R2 Sol received — changes requested8.5/10
Independent415tests40.43s/Phase0+2CLIpass,128hashesmatch. Original R1 fixesstand; G2agencytimezoneobjectionupheld. Remaining malformedmetadata boundarybelow; Opus/Grokstillpending, productfrozen.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P2-R2-S1 | Replay licence list/object is unhashable in set membership; API/UI/CLI crash without refusal audit. R1-S1 remaining metadata case. | medium | fixed | Replay metadata validates integer version, string licence/dataset/source text/optionalbundle before set membership. List/object API/actualCLI/AppTest return static audited replay_input_mismatch with no capture. R1-S1 remaining class closed. tests/test_phase2_council.py; phase2-r3-final-tests.log429passed40.09s EXIT0 OSnetworkdenied/sixkeysunset, actualPhase0/2CLI EXIT0. |

### R2 Opus received — APPROVE8.5/10 with four low residuals
415tests40.06s/Phase0+2CLIpass,128hashesmatch; no checkoutbytecodewrites thisround. G2objectionupheldagain. Builder independentlyreproduced below in temporary authoredinputs with no source edits, log phase2-r2-opus-parent-repro.log EXIT0. GrokR2pending; productfrozen.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P2-R2-O1 | Deep JSON raises RecursionError without audited refusal. | low | fixed | Replay and live model nestedJSON decode/Pydantic/canonicalization errors normalize to static audited refusal; no untrusted exception text. tests/test_phase2_council.py; phase2-r3-final-tests.log429passed40.09s EXIT0 OSnetworkdenied/sixkeysunset, actualPhase0/2CLI EXIT0. |
| P2-R2-O2 | Corrupted deflate raises zlib.error without GTFS refusal audit. | low | fixed | Corrupt deflate/zlib and truncated/lzma streams contained in GTFS parserrefusal; actual malformed compressed ZIP regression audits and no capture. tests/test_phase2_council.py; phase2-r3-final-tests.log429passed40.09s EXIT0 OSnetworkdenied/sixkeysunset, actualPhase0/2CLI EXIT0. |
| P2-R2-O3 | timezone_basis says declared_mapping even when none is declared. | low | fixed | timezone_basis now source_field/declared_mapping/none according to actually available evidence; missing both givesNone+none. tests/test_phase2_council.py; phase2-r3-final-tests.log429passed40.09s EXIT0 OSnetworkdenied/sixkeysunset, actualPhase0/2CLI EXIT0. |
| P2-R2-O4 | Widened month regex rejects ordinary 3monthperiod/monthofDecemberprose. | low | fixed | Unseparated unknown words aftermonth/monat treated asprose, explicitcolon/dash unknownmonth remainsrefused; knownmonth/time-range contradictions unchanged. tests/test_phase2_council.py; phase2-r3-final-tests.log429passed40.09s EXIT0 OSnetworkdenied/sixkeysunset, actualPhase0/2CLI EXIT0. |

Opus note (not a finding): role-marker denylist can reject ordinary signalling-system prose. Retain conservative bounded C6 policy for this fix; no general language classification claim. Do not broaden this cycle into a new injection-detection system.

R2 allfinished: Opus APPROVE8.5, Solchangesrequested8.5, GrokAPPROVE9. All128hashesmatch. Product edits permitted after completedthreadreads; bounded fivefindings fixednext. G2agencytimezone rule upheldbyallthree, contrary conversion rejected by officialspec.

R2 five bounded corrections verified429tests40.09s; no otherproductdelta. R3freeze128files, fourproductionfiles+existingtest changed; freshfocusedcouncilpending.

## Phase2 council R3 — running
Allthreeexactskillmemberslaunched,128-filefreeze/five-filedelta. No verdictor scoreyet; productfrozenuntilallfinish. Handles phase2-council-r3-tasks.json; evidence phase2-r3-evidence.md.

### R3 Opus received — APPROVE9/10
429tests43.03s, actualPhase0/2CLIpass,128hashesmatch; allfiveR2fixesverified. Extra probes31pass/1reviewerassertionfailure (depth200 ordinaryauditedrejectioncorrect). No materialregression. Sol/GrokR3pending, productfrozen.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P2-R3-O1 | Corrupt bzip2 member returns raw fixed stdlib OSError wording rather than gtfs_unreadable_archive. | low, nonblocking | wontfix | Accepted error-code wording limit: import_gtfs catches OSError, auditsrefusal, no capture, CLIexit1/noTraceback. Verified code outerboundary and Opus independentmalformedbzip2probe; messageisfixedlibrarytext, no secret/source echo. Do not extend approvedboundedfixintoanothercycleforcosmeticnormalization. |

### R3 Sol received — APPROVE9/10
429tests42.97s+62independentprobes/actualPhase0+2CLIpass,128hashesmatch. S1 andallfourlowresiduals independentlyverifiedfixed; no newproductfinding. Parenthandofftrailingwhitespacefixedwithoutsourceedit. GrokR3pending; productfrozen.

## Phase2 council final result — R3 unanimous approval
Rounds3. All128R3producthashes matched eachreviewer andbuilder. No openmaterialPhase2finding. R2-S1 andR2-O1–O4verifiedfixed. AcceptedlowP2-R3-O1 onlyerrorwordinglimit; G2wrongconversionrejectedbyofficialspec. Allreviewscomplete, approvedproductreadyforlocalcommit.

| Delegate | R1 | R2 | R3 |
|---|---|---|---|
| Opus through Kiro |7.5/10 changes|8.5/10 APPROVE|9/10 APPROVE|
| Codex Sol |8/10 changes|8.5/10 changes|9/10 APPROVE|
| Grok4.7 |7/10 changes|9/10 APPROVE|9/10 APPROVE|

## Phase3 council R1
| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P3-R1-S1 | Raw retained dates override conflicting canonical validity, yielding false expiry/entry | medium | fixed | Canonical/envelope/individual date consistency, visible conflict evidence; ordinary JSON intake regressions and real dossier/exports/audit pass. phase3-r2-final-tests.log476passedEXIT0. |

SolR1 CHANGESREQUESTED8.5/10;451passed1expectedlocal-data-skip, actualPhase0/2/3CLIpass,145hashesmatch. OtherR1verdictspending.

| P3-R1-O1 | Unknown validity suppresses otherwise eligible R2 one-sided rows | medium | fixed | Only proven expired/entering excluded; unknown notes retain R2 presence rows. Complete/partial and old/new invalid-bound cases pass in476test run. |
| P3-R1-O2 | Explicit hours silently override contradictory retained window declaration | medium | fixed | Direct/role/either-capture declarations preserved; explicit hours cannot override, conflict inputs retained/audited. Six policy cases plus new-capture conflict pass in476test run. |

OpusR1 CHANGESREQUESTED7.5/10;451passed1skip,CLIflowsPASS,145hashesmatch. Fourlowresiduals nonblocking; canonical/rawlowL2 duplicates SolS1materialfinding. GrokR1pending; no sourceedit.

| P3-R1-G1 | Local T3 checkpoint refs reach historical data paths, absent from HEAD/index | low | wontfix | Parent verified ref/object path metadata only; phase3-checkpoint-ref-evidence.json. No remote/push allowed; preserve T3 refs, never push refs/t3 or mirror. --all is branches-only (git push -h); still use an explicit reviewed branch. Before any future authorised push verify intended branch reachability only. |

Phase3R1allcomplete:Opus7.5changes/Sol8.5changes/Grok9APPROVE.145hashesmatch before correction. Three medium comparison findings independentlyreproduced; proceed bounded fix. G1acceptedlocal-ref limit, no history/ref deletion.

## Phase 3 council round 2 final verdict

Opus, Grok and Sol each approved at 9/10. The first Sol attempt hit a usage limit. The user requested a retry, which independently verified the three fixes with 475 tests passed, one expected skip and 51 probes passed. All Phase 0, 2 and 3 CLI acceptance runs exited 0. See phase3-council-r2-sol.md and the Opus and Grok reports. The committed product matches all 145 reviewed hashes.

## Real-data council round 1

Opus 7/10, Sol 8/10, Grok 6/10. All three passed frozen integrity (166/166). Opus and Sol each passed 487 tests with one expected local-only skip and Phase 0, 2 and 3 acceptance. Grok independently reproduced the DB grouping and Swiss validity issues. Grok's focused AppTest timed out at 3 seconds and passed with an extended timeout.

| ID | Finding | Severity | Status | Evidence |
| --- | --- | --- | --- | --- |
| RD-R1-O1/O2/O6 | Future capture time, omitted row filter, malformed envelope errors | high / medium / low | fixed | Separate capture/import fields, time and replay guards, provider and applied filter retained, structured refusal. Provider and capture evidence regressions. |
| RD-R1-O3/G1/G6 | DB cancellation and whole-station scope unclear, sibling stops split into runs | high | fixed | Group by native dated DB trip, scope and stop status in UI/export, retained plan/changed fields and station-only path limit. Synthetic three-stop regression and offline replay of 977 actual points. Planned-clock matching remains the documented basis. |
| RD-R1-O4/G2 | Swiss gap and mixed mode | high | fixed locally | Per-period dates for inspection and membership, explicit rail plus mixed-mode marker, declared excluded count and synthetic tests. No live payload because the provider object still returns HTTP 403. |
| RD-R1-S1 | Source run label interpreted as Markdown | medium | fixed | Plain-text renderer and synthetic AppTest regression. |
| RD-R1-O5/G3 | Archive duplicate rows, ordering and local-time warnings | medium | fixed | Native stop order, retained dedup count, distinct conflicting records resulting in unresolved order, explicit-offset clocks accepted and fold/gap warnings shown. Synthetic tests and 439-row actual replay. |
| RD-R1-G4/G5/O7 | Future window boundary, local German date projection, raw provenance | medium | fixed | Newly selected declared window must reach a validity start, ISO offsets projected into Berlin, raw German body retained with private permissions. Local comparison reproduces 776/456 and verifies raw hashes. |
| RD-R1-G7/G8 | Large full export and minor source display details | medium / low | accepted scope | Paginated work and finding lists, deferred sidebar run options, Swiss raw payload stored once. Full exports intentionally keep every record. D-1 retains per-page fetch time; import time remains on its legacy capture. NS multi-section details remain in the source work. |

## Real-data council round 2

Sol and Opus approved 9/10 each, with 490 tests passed and one expected local-data skip, all three phase acceptance scripts exit 0, and all 166 hashes unchanged. Sol ran 17 independent checks. See real-data-council-r2.json for the report and probe paths. Grok R2 cancellation requested because the R3 freeze supersedes it.

## Real-data council round 3

Swiss live transport and dated native mode join changed five paths. The new 167-file snapshot passed 492 offline tests, Phase 0, 2 and 3 acceptance, and actual Swiss capture, intake and AppTest/export. R3 tasks and scope in real-data-council-r3.json.

Opus R3 approved 9/10 and independently verified all 167 hashes, 491 tests with one expected local-data skip, and all nine live-adapter fixture tests. Its findings are fail-closed coverage limits, except that unresolved explicit mode values are undercounted. The parent reproduced this with synthetic `unknown`, `all`, `train` and `intercityRail` declarations. The actual Swiss capture had no mode declarations, so these exclusions did not affect its counts. The parent also checked all 362 exported records and found no midnight EndTime projection in that sample. Other low notes are overlapping GTFS releases, duplicate calendar lines and raw-copy disk use.

Grok R3 approves 9/10. No open material finding and no new ledger row. A private copy of the 167-file freeze passed six synthetic probe groups: Swiss calendar, exceptions and route types; disagreement, ambiguity and declared mode; intake, gap filter and refusal; DB native trip, station scope and same train/date; archive order, conflict and clocks; declared rolling-window bounds. Focused pytest imported that copy and passed 48 tests, with 1 skip, in 2.89s. Freeze and copy hashed 167/167 with no extras before and after. The parent 492-test suite, live Swiss capture and Train Archive sample were not re-run here. An explicit hour count with no declared windows still marks a start past the new edge as entering; both declared windows mark it `membership_unknown` / `starts_beyond_current_window`. That matches the locked rule. Probe report: `/tmp/nightdesk-r3-grok-probe.json`.

Sol R3 approved 9/10. The independent checks passed 491 tests with one expected local-data skip, 52 additional probes and Phase 0, 2 and 3 acceptance. All 167 hashes matched. ND-R3-SOL-1 is a low diagnostic limitation: unresolved counts do not distinguish absent IDs, inactive or out-of-release dates and conflicting references. Retained XML and ZIP evidence supports follow-up. Exclusion stays conservative. The report path is in real-data-council-r3.json.


## European Sleeper national-feed council R1

Opus approved 8.5/10 against 171 frozen hashes. Independent suite 493 passed and one local-data skip. Sol failed on usage quota with no score. Grok dispatched on the same freeze.

| Finding | Status | Verification |
| --- | --- | --- |
| Dataset name alone could assert GTFS or Infrabel provenance | Fixed locally | GTFS import receipt and known Infrabel mapping hashes, copied-ingest and altered mapping regressions, real CLI/AppTest replay |
| Sign-prefixed or non-integer reported delays could display as empty | Fixed locally | Plus accepted, unparsed value retained with visible warning, synthetic RDT regression |
| Partial source coverage absent from comparison Markdown and UI | Fixed locally | Real ES 475 comparison displayed partial Infrabel evidence and exported it offline |

Grok reviewed the unchanged 171-file freeze, not the later worktree. Score 8/10, changes requested. Those three "Fixed locally" rows are not in this freeze: `es_runs.py` still accepts a dataset whose name ends with `_gtfs`, `_minutes` still returns null for `+8` and `8.5` with no warning field, and the comparison limits still do not count unreviewed stops. Freeze hashes matched 171/171 before the probes and again after. No freeze or product file was written. Synthetic probes: `/tmp/nightdesk-es-r1-probe.py` and `/tmp/nightdesk-es-r1-plus`. Focused pytest on the freeze copy: 18 passed in 0.87s (`test_es_national.py`, `test_gtfs.py`, `test_cli.py`, `test_demo.py`). Parent real-data counts, live reuse terms, and Swiss/Train Archive ES identity were not rechecked.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| ES-R1-G1 | Two stops in one Dutch service with the same station code and different `Stop:RDT-ID`s both become `nl-rdt-stop:SAME`. Native stop ids stay in extra. | medium | fixed | Repeated station code in the same service refused. Synthetic duplicate check and October archive replay verified. |
| ES-R1-G2 | A cancelled stop with empty clocks is kept, then sorted after timed stops. The run banner says `source_stop_sequence_unresolved`, including on a fully timed run. The point still has `missing_time` in its own unresolved object. | medium | fixed | Dutch points stay in archive file order. Clockless stop regression retains missing_planned_time and no pass window is inferred. |
| ES-R1-G3 | `+8` and `8.5` become null in `rdt_arrival_delay_min` / `rdt_departure_delay_min`. The raw strings remain. No warning key is added, so the new UI columns display empty. | medium | fixed | Signed whole minutes and visible warnings for unparsed nonempty delays. Synthetic +8 and 1.5 regression. |
| ES-R1-G4 | Scheduled provenance is `dataset.endswith("_gtfs")` plus kind `scheduled`. Observed provenance is dataset name `infrabel_d1` or `infrabel_punctuality`. No mapping hash or GTFS import receipt is required. | medium | fixed | GTFS import receipt and approved mapping hashes. Synthetic copied rows and altered mapping refused. Real ES 475 replay passed. |
| ES-R1-G5 | Comparison Markdown shows the encoded point id and source refs, not the raw GTFS stop id, and does not count stops left out of the review. The JSON report contains both. | low | fixed | Native stop IDs and unreviewed counts in report, UI and export. Synthetic assertions and real ES 475 AppTest. |
