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
