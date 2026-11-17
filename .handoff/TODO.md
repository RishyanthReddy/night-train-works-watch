# Build TODO

Authority: KICKOFF.md section 9; user now authorised Phases 1–3 in order, task by task (2026-11-17).
Implementation/checks: current Codex agent. Council at each phase end: Kiro Opus medium, Codex Sol high, Grok 4.7 high.
Latest checkpoint: finish Phase1 fixes/review/commit, then stop before Phase2 for user continuation.
No remote creation, push, merge or deploy. P0.9 skipped. Stop after Phase 3. P3.6 account/remote actions remain gated.

## Phase 0 — execute in order
- [x] P0.1 Existing baseline fedda2c verified; data/ ignored and SPEC superseded. Fresh uv sync --frozen exit 0; uv run --offline pytest exit 0 (111 passed).
- [x] P0.2 Existing CLI/config verified with help and passing tests.
- [x] P0.3 Existing models/audit inspected; passing baseline tests.
- [x] P0.4 Existing CSV/XLSX/JSON profiler inspected; 42 targeted tests passed.
- [x] P0.5 Scalar GenericRow mappings, C1–C5, confirmation, ingest/rejects, flatten.
- [x] P0.6 Two synthetic admin mappings.
- [x] P0.7 Generic comparison and local Markdown/JSON exports.
- [x] P0.8 Three synthetic fixtures; meaningful integration/edge-case checks.
- [x] P0.9 Skipped by user.
- [x] Six real CLI acceptance checks, including before-confirm refusal and no keys/network.
- [x] Council: two rounds, one fix round. Opus 6.5→9/10; Sol 8→9/10. Both APPROVE same snapshot. DeepSeek unavailable and waived by user.
- [x] Scope/secret/data checks; approved product commit d220f62; handoff, swap check and final evidence complete.

## Current goal — Phases 1–3, task order enforced

### Phase 1 — One planner task end to end
- [x] P1.1 `timeutil.py`: the time rules of section 7 with the listed tests.
- [x] P1.2 `model.py`: `Revision`, `WorkNotice`, `PathLeg`, `BoundaryEvent`, `JourneyLink`, `RunRow`, `RunPoint`,
- [x] P1.3 `store.py`: captures and immutable revisions under the bundle root; idempotent import (N1);
- [x] P1.4 `mappings/infrabel_punctuality.yaml` (`RunRow`) and `runs.py`: `TrainRun` and `Segment`
- [x] P1.5 `links.py`: load `JourneyLink` rows from a mapped file; confirm one by hand (CLI/UI);
- [x] P1.6 `changes.py`: `ChangeSet` for a selected pair of revisions, and for a pair of captures under
- [x] P1.7 `match.py`: date -> weekday -> clock window vs the planned pass window (D6) -> place by
- [x] P1.8 `border.py`: the one narrow rule of section 2 (same event kind, same reviewed point, same
- [x] P1.9 `review.py`: decision bound to a revision hash; follow-up with owner; stale marking (N6);
- [x] P1.10 `export.py`: train/date dossier as Markdown and JSON — before/after, sources, exposures,
- [x] P1.11 `ui/app.py`: plain working **queue** and **dossier** screens, no styling (design research
- [x] P1.12 `audit.py`: hash chain; `nightdesk audit verify` (catches an edited or removed line);
- [x] P1.13 Fixture `syn`: one synthetic dataset in two captures (v1, v2) with **no rejected rows**,

- [ ] Phase 1 close: acceptance, viewed screenshots, offline tests and swap pass; R3 fixes applied;330 main offline tests pass, queue scaling/CLI pass. Focused R4 running (93-file freeze); approval/local commit pending. Stop before Phase2.

### Phase 2 — Trust and edge cases
- [ ] P2.1 `stations.py` + alias rows under `mappings/aliases/` (each row with a source, reviewed;
- [ ] P2.2 Harden identity and dates: uncertain identity, service date vs calendar date across
- [ ] P2.3 Scheduled runs from the saved CC0 GTFS (`adapters/gtfs.py`): expand `calendar_dates`, times
- [ ] P2.4 `estimate.py`: every delay request returns `Refusal("prediction_not_validated", detail,
- [ ] P2.5 Text door: `llm/client.py` (plain HTTPS to Mistral; `mistral`, `replay`, `off`), the
- [ ] P2.6 Security fixtures, all authored and synthetic: (a) a notice containing injected
- [ ] P2.7 `nightdesk demo check`: demo mode loads only assets listed in a manifest as synthetic or
- [x] P2.8 Optional notice version extraction skipped by recorded scope decision.

- [ ] Phase 2 acceptance in real app, viewed screenshots, offline tests, swap check, council, local commit and handoff.

### Phase 3 — The swap, isolation, security
- [ ] P3.1 **Unseen-shape rehearsal**, whole path from file to export, once with all keys unset: a
- [ ] P3.2 Isolation test: two bundles with colliding train numbers, work ids and request ids but
- [ ] P3.3 Model policy tests: a synthetic bundle marked `nda: true` -> a model request is refused
- [ ] P3.4 Tamper tests: edit a line, remove a line, cut the tail of a copy of the audit log; verify
- [ ] P3.5 `docs/THREAT_MODEL.md` (one page): untrusted documents -> model -> gates; assets; what can
- [ ] P3.6 Aikido preparation, our own repo and code only: the **user** creates the account

- [ ] Phase 3 acceptance in real app, viewed screenshots, offline tests, swap check, council, local commit and handoff.

### Phase 4 — Not authorised: looks, sustainability, handover
- [ ] P4.1 **Design research before any styling** (the plain screens of phase 1 exist already).
- [ ] P4.2 Style the queue and dossier to the approved direction, readable from the back of a room;
- [ ] P4.3 `co2.py` + one **scenario card**: passenger-km x share that would use the alternative mode
- [ ] P4.4 `docs/DAY_OF.md` (section 10 made concrete with real commands) and `docs/DEMO.md` (short
- [ ] P4.5 Final rehearsal and freeze: full test run, clean-setup install check, tag the commit.
- [ ] P4.6 Optional, only after everything above passes, and only after the user approves the extra
