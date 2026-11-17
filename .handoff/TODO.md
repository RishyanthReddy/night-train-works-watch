# Build TODO

Source: KICKOFF.md section 9; start authorised by the user on 2026-11-17.
Coordinator: Codex. Builder: Kiro Opus 5.5 medium.
Council: Kiro Opus 5.5 medium, Codex Sol high, Cursor DeepSeek V4.1 Flash 1017 max.
No GitHub repository creation, push, merge or deployment is authorised.

## Phase 0 (current; execute in order)
- [x] Run `uv sync --frozen`: exit 0, `Checked 23 packages in 3ms`.
- [x] Run `uv run --offline pytest`: exit 5, collected 0 items; no tests yet.
- [x] Pending Opus plan gate approved revision2; coordinator agrees. User start approval preserved; council only at phase end.
- [ ] P0.1 Ignore all data/, mark SPEC first line superseded, first local commit.
- [ ] P0.2 CLI help, bundle configuration and smoke test.
- [ ] P0.3 Canonical Phase 0 models and bundle-local append-only audit.
- [ ] P0.4 CSV/XLSX/JSON profiling.
- [ ] P0.5 Scalar GenericRow mappings, gates, flattening, mapping confirmation.
- [ ] P0.6 Two synthetic admin mappings.
- [ ] P0.7 Source-linked generic comparison and Markdown/JSON export.
- [ ] P0.8 Three synthetic admin fixtures and meaningful checks.
- [ ] Run all six acceptance steps through the real CLI, including network denied / keys unset.
- [ ] Coordinator verification and three-member independent council code review.
- [ ] Fix any blockers (at most two fix rounds), repeat affected checks and review.
- [ ] Local approved-snapshot commit, handoff update and swap check.
- [ ] Phase 0 report with real output; honour the Phase 0-only boundary of this chat.
- [x] P0.9 skipped as requested (no fetcher or scheduler).

## Later phases (not dispatched)
- [ ] Phase 1 P1.1–P1.13: planner workflow; council phase review and Opus integration checkpoint.
- [ ] Phase 2 P2.1–P2.7: trust and edge cases; P2.8 optional; council phase review.
- [ ] Phase 3 P3.1–P3.6: swap/isolation/security; council + Opus integration checkpoint.
      P3.6 requires the user's GitHub/account action; no repo creation or push before permission.
- [ ] Phase 4 P4.1: design research; user must approve direction before P4.2.
- [ ] Phase 4 P4.2–P4.5: styling/scenario/handover/freeze; final council + Opus integration.
      P4.6 optional additions require approval of their extra paths.

## Evidence and running tasks
- Setup/test output: coordinator tool calls on 2026-11-17; baseline is not green.
- Git status: unborn `phase1-core`, existing untracked files preserved.
- T3 capabilities: all three named council models advertised and child-enabled.
- Council plan round1: Opus task suffix 3f198720-3717-4764-9af2-87f9f97d739d blocked; Sol fb9641f9-063f-47ba-b497-883b07ba44c5 blocked; Carbon 2d752836-0ad8-45a8-ab70-1e6b859e5a49 failed (provider API error).
- Findings resolved: review.md; Opus revision2 APPROVE (bf360436-2538-4af0-a90c-95d3538e2130). Carbon retired by user; no retry. Product implementation not started.
