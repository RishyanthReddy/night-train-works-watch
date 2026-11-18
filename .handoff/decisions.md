# Decisions

## 2026-11-17 — Phase 0 build authority
Decided: selected Codex agent implements/checks P0.1–P0.8; council only after completion. P0.9 skipped, stop before Phase 1.
Why: current user instructions and KICKOFF.md allowed paths.
Rejected: delegating implementation, creating/pushing a remote, taking later phases under this goal.

## 2026-11-17 — Council availability
Decided: finish with Kiro Opus 5.5 medium and Codex Sol high.
Why: Cursor DeepSeek refused weekly usage; user explicitly chose “Finish with Opus and Sol”.
Rejected: silently substituting another model. DeepSeek gets no score.

## 2026-11-17 — Local generic intake and comparisons
Decided: confirmed mapping hashes are scoped to a bundle; records/rejects/captures/audit/exports stay under its output root.
Missing/ambiguous times remain unresolved with raw values; unknown enums retain raw evidence.
JSON key absence is distinct from explicit null. Duplicate/missing keys never imply a field-level identity.
Mapped/raw modes and distinct datasets cannot be mixed as compatible records.
Comparison reports describe selected-table rows, never official removals, cancellations or national approval.
Why: KICKOFF.md common gates, provenance rules and council reproductions.

## 2026-11-17 — Audit and exports
Decided: lock and append audit batches; no chain/seal until Phase 1. Each export pair is addressed by both JSON and rendered Markdown.
Why: avoid quadratic ingest and duplicate sequences; preserve earlier exports when rendering changes.
Rejected: claims of tamper-proofing or truth.

## 2026-11-17 — Dependencies
Decided: remove unused requests and its network-only dependency subtree in Phase 0.
Why: installed certifi metadata was MPL-2.0, outside the plan’s dependency rule; Phase 0 needs no fetcher.
Historical fetch_public.py stays untouched outside the current product; a later fetcher can use standard-library HTTPS.

## Preserved project decisions
KICKOFF.md remains the governing product plan and supersedes old SPEC.md.
The future app uses Mistral only; ES external processing stays off until the user has asked ES and enabled consent (KICKOFF sections 0/8).
Historical decisions and their original evidence are preserved locally at history/20261117-before-phase0-closure/decisions.md.

## 2026-11-17 — Continue through Phase 3
Decided: user authorised new goal for Phases 1–3 in task order, TODO updates and council at each phase end. Updated council is Opus/Sol/Grok per current skill. No Phase 4. Existing no-remote/push restriction carries forward; P3.6 external account/connection waits for user action.
Optional P2.8 notice-version extraction is skipped so required work stays bounded.

## 2026-11-17 — Streamlit transitive dependency exception
User explicitly approved “Allow certifi for Streamlit” after the dry run showed MPL-2.0 certifi. Exception is limited to Streamlit’s transitive dependency; no UI stack change or remote action.

## 2026-11-17 — Phase1 council rule clarifications
Completeness is a capture property: unresolved C4 times/C5 enum warnings do not remove received rows or make a declared-complete capture partial. Rejects, missing/unparsed files and uncertain identity still do.
Grade A follows the explicit section2 A definition and section7 worked example: both exact endpoints on an ordered known path plus time overlap. A missing work line is shown as missing evidence; line-only or one-endpoint evidence remains B, and path_unresolved always caps at B. This resolves the ambiguous section2 B line-unknown wording without a fallback reaching A.
Explicit predecessor relationships are append-only audit metadata over immutable revision content/source files. First valid relationship wins; conflicting later attempts are recorded as rejected.
Review staleness uses capture observations up to each decision's basis; returning content does not revive an older review automatically. An answer after the change can close a reopened question, and a later change reopens it again.

## 2026-11-17 — Phase1 R2 integrity and exposure consistency
Decided: use one verified reader/index per operation, never a shared global cache. Retain mapping/manifest declarations, audit artifact hashes, recompute effective completeness, and refuse inconsistent flags or relationship metadata. Unproved legacy declarations remain incomplete.
Why: R2 tamper and quadratic-read reproductions; verified by current integrity/scaling regressions.
Decided: exact ordered point evidence keeps A despite weak line disagreement, shown as line_mismatch. Line-only B needs an overlapping named-line segment; unknown line evidence stays unknown. Resolved off-path endpoints retain literal W5 B semantics when time overlaps; the queue follows the canonical A/B outcome, never inventing no-match from that absence.
Why: section2 place gates downgrade; section7 worked example; match-v3 regression tests. Rejected an undocumented off-path no-match rule.
Decided: group queue tasks by train/date; retain every source leg and require explicit selection when more than one exists. No source winner chosen automatically.
Why: section2 one-row contract; AppTest and grouping regressions pass.

## 2026-11-17 — Stop before Phase2 checkpoint
Decided: finish Phase1 blockers, verification, council and local commit, then stop before Phase2 and await user continuation.
Why: latest user instruction “bfore phase 2 stop ... blockers ... fix them first”. Original remaining Phase2/3 scope is preserved behind this checkpoint.

## 2026-11-17 — Phase1 closure limit
Decided: close Phase1 after unanimous R4 approval; document pre-existing mixed-request sequence candidate expansion as nonblocking and defer further scoping to later identity hardening.
Why: no automatic journey link or positive result; builder audit proved all12500 entries in two probes unknown/unlinked. Avoid expanding a completed two-file fix into a new matching rule. User requires stopping beforePhase2. Rejected claiming general linear performance or silently hiding the limit.

## 2026-11-18 — Mixed-request boundary scope follow-up
Decided: user reopened the accepted Phase1 limit. Only the selected explicit journey link/date establishes eligible boundary legs. No link gives one sourced unknown; sequence collisions require an explicit revision choice, available in UI/API and included in audit/export. Request ids never establish a cross-network join. Operating-date fields remain for boundary comparison rather than filtering, preserving removed-date mismatches.
Why: requested fix and passing mixed-request/ambiguity/date/UI regressions. Rejected guessed request-id joins, automatic source winners, suppressed unknowns and changes triggered only by capture id.

Follow-up self-review also treats competing source records for the same linked network/train as ambiguous even if their sequence numbers differ. An explicit choice narrows them; no source winner is inferred. Regression covers both same/different sequence ambiguity. Final336-test offline run passes33.53s.

## 2026-11-18 — Phase2 continuation authorised
Decided: finish/review/commit the current Phase1 mixed-request follow-up, then start Phase2 as next phase/goal using task order, TODO, actual offline/browser checks, council and local commits.
Why: user explicitly requested “after this start phase-2 ... resume goal ... same approach”. Earlier stop-beforePhase2 is superseded after this fix closes. No remote/push/Phase4 authorization added.

## 2026-11-18 — Phase2 evidence boundaries
Decided: GTFS uses explicit feed namespace, scheduled times and unresolved path only; time conversion follows the GTFS noon-minus12 elapsed-time definition, separately from unresolved local-time folds in ordinary source records. Text proposals require field quotes and deterministic typed gates; explicit human import remains separate. Dataset permission and audited bundle consent precede every live Mistral request. Public demo uses a hashed provenance allowlist.
Why: KICKOFF P2.1–P2.7, official GTFS/Mistral docs and passing focused/full checks. Rejected inferred national ids, numeric delay prediction, provider selection as consent, automatic proposal approval and licence claims without a manifest/source record. No live model call is required; none made.

## 2026-11-18 — Council R1 timezone objection and bounded fixes
Decided: retain agency_timezone for GTFS stop_times, even when stops declare another valid zone. Validate stop_timezone names as input quality; never reinterpret stop_times through them. Official GTFS reference explicitly says arrival/departure use agency.agency_timezone, not stops.stop_timezone (https://gtfs.org/documentation/schedule/reference/#stop_timestxt, reopened2026-11-18). Grok G2 timing-change recommendation is disputed; a regression now fixes the intended agency-based instant and invalid-zone refusal.
Decided: same train/date run variants require an explicit observation selection; without one the queue/dossier stays usable and works checks stay unknown. Selection identifies source observation and is audited/exported. No guessed trip or national train correspondence. Reject unsupported frequency feeds and bound output expansion before normalizing rows.
Why: R1 concrete reproductions and Phase2 scope. Rejected automatic trip winner, unsupported frequencies declared complete, or changing the official time basis to match a reviewer expectation.

## 2026-11-18 — Infrabel D-1 live integration

Use explicit fetch and existing confirmed offline intake. D-1 point labels remain feed-local because the API has no PTCAR number. The operator-filtered snapshots remain incomplete for operational comparison. Record raw sources and use a synthetic path pair to exercise the live observations in the dossier.

## 2026-11-18 — Real-data evidence

Use provider-scoped identifiers, original capture times when evidenced, and separate scheduled, published and observed fields. Keep native time and location evidence in the retained record. These boundaries follow the user-provided source mapping, provider documentation in real-data-integration-plan.md, and actual replay and AppTest checks in sources.md. Use independent evidence tabs so a source record can be read without an invented path. The German snapshot without a manifest remains unverified for chronological intake. Unknown-licence captures remain local and cannot enter the manifest-gated public demo. Swiss download and Train Archive ES limits are explicit in state.md.

Require source time at or before import time and retain both for envelope captures. R1 independently reproduced false expiry from a future time. Two declared rolling windows now bound a window-entry finding at both captures. A whole-station DB reply is evidence of station events only. The archive keeps native stop order and version, and Swiss validity gaps remain separate. Regression and actual saved-capture checks are logged in review.md.

Swiss rail classification may rely on explicit mode in the notice or an exact date-qualified SJYID match to an active trip and documented rail route type in an official Swiss GTFS release. The raw archives, hash, release date coverage, and example references remain local evidence. Affected place or line names do not establish mode. If nothing qualifies and mode is unresolved, refuse the capture. For Train Archive keep a separate coverage conclusion for each checked sample. A shared station or a same-number trip alone cannot qualify an ES match. The planning thread advisory and live/offline results are recorded in sources.md.

## European Sleeper coverage research

Proposed first increment is Belgian observed coverage with Infrabel D-1/monthly data and an attributed, local-only Dutch archive pilot. A separate scheduled and published live pilot can use the community feed if reuse terms are confirmed. Preserve provider-native keys and review service-date, direction and station links. Keep Swiss and Train Archive coverage unknown until the dated provider identity is proven. The user authorized the national-feed build and requested a final three-member council.

Require a recorded local GTFS import receipt with the ZIP hash and a supported rule version for the schedule side, plus the reviewed Infrabel mapping hash for the observation side. Users explicitly select runs and station pairs. An exact common planned instant and consistent source order are required for each pair. This follows the Opus synthetic spoofed-dataset check and a regression that rejects copied normalized GTFS rows without a receipt. The comparison records local provenance without asserting source authenticity.


## Public demo and real-data checkpoint

The named demo bundle requires manifest-approved ingress in the core file, batch, alias and replay paths. Live provider staging and unrestricted GTFS import stay in practice. The public launcher locks to the demo bundle, checks its exact data first and binds loopback. Practice and NDA ingestion keep their existing workflows. This implements the parent review's mechanical gate without a global licence override. The demo uses the previously approved synthetic assets and one already-tracked CC0 Infrabel run, with source evidence shown separately.
