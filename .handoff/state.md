# State
_Updated: 2026-11-17 by Codex gpt-6.1-sol_

## Goal / scope
Complete KICKOFF.md Phase 0 P0.1–P0.8 only; skip P0.9. No Phase 1, remote, push, merge or deployment.
User authorised building in this chat and requested a TODO, local commit, council and handoff.
Implementation/checks are by the selected agent. User waived unavailable DeepSeek; final council is Opus + Sol.

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

## In progress
- Opus/Sol council round 2 APPROVED 9/10 each; phase0-council-r2-snapshot.json hashes still match.
- Final approved-snapshot local commit and post-commit checks pending. No remote configured or used.

## Limits / deferred
- Append-only audit only: hash chain/seal, typed rail revisions/checks and UI are Phase 1+.
- Phase 0 has no fetcher, model calls, secrets or network requirement.
- Historical untracked scripts/fetch_public.py is untouched; it needs requests if used separately and is not the Phase 0 product.
- Ordinary raw/raw generic comparison is labelled unvalidated; mixing it with mapped input is refused.
- Unknown/duplicate keys do not establish identity; absent selected rows do not establish cancellation/withdrawal.
- Swap: new local input plus confirmed mapping YAML; reviewed aliases/adapters/config only when later needed. Flatten is explicit.
- Deeply nested/oversized native JSON can fail the file safely with a low-level error; crash recovery is not guaranteed. See nonblocking review ledger.
- Earlier planning/research memory is preserved locally under history/20261117-before-phase0-closure/; it is not silently staged.
