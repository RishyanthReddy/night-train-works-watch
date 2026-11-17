# Direct Phase 0 work — Codex

Fresh start commands: `uv sync --frozen` exit 0, Checked 23 packages in 4ms. `uv run --offline pytest` exit 0, 111 passed in 0.34s. Existing partial implementation preserved. Prior baseline commit: fedda2c.

Old handoff refers to a Kiro task in another thread. Cancellation returned task_not_found (belongs to another thread); not claimed cancelled. No delegates started for implementation in this thread.

P0.5: 45 mapping/flatten tests passed. Initial test exposed bool-as-version acceptance; fixed with explicit integer version guard. Confirmed hash scoping, changed hash refusal, negative seconds, nested extra preservation, ambiguous time retention, namespace checks, merged XLSX flatten, and safe YAML refusal exercised.

P0.6: both mapping files loaded successfully as GenericRow, synthetic_admin, synthetic, five scalar fields. P0.7: 9 targeted generic/export tests passed; source references, uncertain-key multiset diff, JSON roundtrip, escaped Markdown and bundle export boundaries exercised.

Pre-council: 171 tests passed; acceptance-isolated.log records a fresh synthetic CLI run. Earlier full suite network-denied: 168 passed; three regression tests then added (defaults, capture refs, audit text). Baseline protected hashes unchanged. Council snapshot records all product/test/mapping hashes.

Fix round 1: all Sol S1/S2 and Opus F1–F9 addressed, including low findings within Phase 0. 191 tests passed with keys unset and OS networking denied (phase0-tests-r2.log). Fresh six-step CLI acceptance plus real JSON/XLSX/merged-header checks passed (phase0-acceptance-isolated-r2.log); retained workspace outputs in phase0-acceptance-r2.log.
Audit benchmark: 3000 rows 0.174s, 6000 rows 0.316s; exact output phase0-performance-r2.log. Multi-process seq allocation is covered by regression tests. No chain or seal is claimed.
Prepared fixes first ran in an isolated temporary copy. Offline relock initially failed due missing cached Windows metadata; `uv lock` with network exited 0 and only removed requests/certifi/charset-normalizer/idna/urllib3. Frozen offline sync then succeeded. Source files outside allowed paths were not written. AGENTS.md and CLAUDE.md hashes changed during this session; coordinator did not edit or stage either. They remain unrelated untracked instruction files. Protected KICKOFF/scripts/package initializer/SPEC tail remain unchanged.
A retained older Markdown export exposed a format-only hash collision after the rendering fix. Pair filenames now hash both JSON and rendered Markdown; old files are preserved. A regression verifies renderer changes produce a new pair. Generic rule version is generic-v2.

Council round 2: Opus APPROVE 9/10, Sol APPROVE 9/10. Both independently ran 191 tests and CLI acceptance; all 34 source snapshot hashes match. Nonblocking file-level JSON/crash limitations are retained in review.md. No product change after approval.
