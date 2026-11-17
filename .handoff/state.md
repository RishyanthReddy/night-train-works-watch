# State
_Updated: 2026-11-17 by Codex gpt-6.1-sol_

## Goal / scope
Current goal: Phases 1–3 in order, one task at a time, preserving completed Phase 0. No Phase 4, remote, push, merge or deployment.
User authorised Phases1–3 with TODO/local commits/council. Latest steering: fix current Phase1 blockers first, then STOP before Phase2; await user continuation at that checkpoint.
Implementation/checks by the selected agent. Updated council: Kiro Opus medium, Codex Sol high, Grok 4.7 high.

## Done
- Existing baseline commit fedda2c preserved on phase0; initial fresh commands: uv sync --frozen exit 0 and pytest exit 0, 111 tests.
- P0.1–P0.8 implemented/verified; checklist: TODO.md.
- CLI supports sniff, mapping confirm, ingest, rejects, flatten, compare and local Markdown/JSON export.
- Round 1: Opus 6.5/10, Sol 8/10, both changes requested. Reports council-r1-opus.md / council-r1-sol.md.
- Fix round 1 addresses all listed findings; ledger review.md records fixes/evidence.
- 191 tests pass with six credential variables unset and OS networking denied: phase0-tests-r2.log.
- Six acceptance steps plus JSON/XLSX and merged-header CLI checks pass: phase0-acceptance-isolated-r2.log.
- Retained local synthetic exports and exact command output: phase0-acceptance-r2.log.
- Audit batches are locked and linear in imported rows; measured synthetic 3000/6000 rows: phase0-performance-r2.log.
- requests removed because unused in Phase 0 and it pulled MPL-2.0 certifi; frozen lock/sync succeeds.

## Phase 0 closed
- Opus/Sol council round 2 APPROVED 9/10 each; phase0-council-r2-snapshot.json hashes still match.
- Product commit d220f620748737ba5709bc161ca63b2cd5750cb6; all 34 reviewed hashes match its Git blobs and working files. No data files tracked; no remote configured or used.
- Phase 0 product is complete. New work starts from d340990 on dedicated phase1 branch.

## Phase1 closed — stop before Phase2
- Product commit 6d11e5c4ce426ea25d565c418d9e4ac2a1ff2412; all93 committed blobs and working files match the approved R4 snapshot. Four protected baseline hashes match. No tracked data or remotes.
- P1.1–P1.13 and app/swap acceptance complete; phase1-completion-audit.md maps requirements to evidence.
- Four council rounds; final unanimous APPROVE9/10: Kiro Opus, Codex Sol, Grok4.7. All93 hashes matched every R4 review; scores/reports in review.md and phase1-council-r4-*.md.
- Main330 tests pass22.04s with OS network denial and six credentials unset; Phase0 and full actual CLI pass. Latest frozen offline sync exit0 checks45 packages.
- Main800-leg all-sequence1 queue1.185s; no cubic scan. Shape-specific local measurement only; mixed requests can still produce excess unknown checks (accepted nonblocking limit).
- User checkpoint reached: STOP before Phase2. Goal remains unfinished for Phases2/3 and is to be paused pending explicit continuation. No Phase2/3 code, remote, push, merge or deployment.

## Limits / deferred
- Phase1 has no remaining blocker; mixed-request sequence candidate expansion can produce many unknown/unlinked checks (P1-R4-O1), explicitly deferred as nonblocking. No positive join is inferred.
- Phase 0 has no fetcher, model calls, secrets or network requirement.
- Historical untracked scripts/fetch_public.py is untouched; it needs requests if used separately and is not the Phase 0 product.
- Ordinary raw/raw generic comparison is labelled unvalidated; mixing it with mapped input is refused.
- Unknown/duplicate keys do not establish identity; absent selected rows do not establish cancellation/withdrawal.
- Swap: new local input plus confirmed mapping YAML; reviewed aliases/adapters/config only when later needed. Flatten is explicit.
- Deeply nested/oversized native JSON can fail the file safely with a low-level error; crash recovery is not guaranteed. See nonblocking review ledger.
- Earlier planning/research memory is preserved locally under history/20261117-before-phase0-closure/; it is not silently staged.
