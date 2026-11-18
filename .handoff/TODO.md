# Build TODO

Authority: KICKOFF.md section 9; user now authorised Phases 1–3 in order, task by task (2026-11-17).
Implementation/checks: current Codex agent. Council at each phase end: Kiro Opus medium, Codex Sol high, Grok 4.7 high.
Latest checkpoint: Phase1 follow-up committed; user authorised Phase2 continuation.
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

- [x] Phase1 close: acceptance/screenshots/swap/current330 offline tests/CLI pass; R4 unanimous9/10; product commit 6d11e5c,93 blobs verified. STOP before Phase2 per user.

### Phase 2 — Trust and edge cases
- [x] P2.1 `stations.py` + alias rows under `mappings/aliases/` (each row with a source, reviewed;
- [x] P2.2 Harden identity and dates: uncertain identity, service date vs calendar date across
- [x] P2.3 Scheduled runs from the saved CC0 GTFS (`adapters/gtfs.py`): expand `calendar_dates`, times
- [x] P2.4 `estimate.py`: every delay request returns `Refusal("prediction_not_validated", detail,
- [x] P2.5 Text door: `llm/client.py` (plain HTTPS to Mistral; `mistral`, `replay`, `off`), the
- [x] P2.6 Security fixtures, all authored and synthetic: (a) a notice containing injected
- [x] P2.7 `nightdesk demo check`: demo mode loads only assets listed in a manifest as synthetic or
- [x] P2.8 Optional notice version extraction skipped by recorded scope decision.

- [x] Phase2close:429offlinechecks, actualCLI/app/viewedscreenshots/swap, R3unanimous9/10, localproductcommit 493d570;128blobsverified, handoffupdated.

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

### Phase1 follow-up — user-authorised2026-11-18; Phase2 starts after closure
- [x] Fix P1-R4-O1: explicit journey/date boundary scope; one unlinked summary; explicit ambiguous-leg selection.
- [x] Mixed-request/ambiguity and prior checks/browser/council pass:337 tests, R6 allthree9/10. Local commit recorded in state.

P2.1 evidence: phase2-p21-tests.log,347 passed34.29s networkdenied/sixcredentialsunset. Reviewed aliases/importCLI, bundle isolation/tamper tests, ambiguity/no guess, unchanged revision plus sourced match-v4 evidence and queue/dossier/export parity. P2.2 verified below.

P2.2 evidence: phase2-p22-tests.log,67 targeted checks pass16.42s networkdenied/sixcredentialsunset; regressionfirst reproduced uncertainwork→A and multi-dateeventreuse→agreement, now unknown. Singleton midnight/offset/DST/halfopen and incompletecaptures retained. NextP2.3.

P2.3 evidence: phase2-p23-tests.log,65 tests pass0.48s networkdenied/sixcredentialsunset; CC0subset hashes and overnight/DST/variants/normalpipeline/CLI checks. P2.4 in progress.

P2.4 evidence: tests/test_estimate.py + test_desk.py3passed0.81s networkdenied; refusal exported and rendered/clicked in AppTest, no numeric field/value. Existing multi-date boundary assertion updated to P2.2 unknown rule.

P2.5/P2.6 evidence: phase2-p25/p26-tests.log,10/12checks pass incl manualAppTest and mockedfixedhost/consent/revocation/replay; phase2-interim-tests.log371passed35.28s. No live model calls or spend. P2.7: phase2-p27-tests.log15passed0.97s; demo CLI27hashedsyntheticassets, recursive reference and tamper/refusal tests. Full end-of-phase checks remain.

Phase2 builder acceptance: phase2-final-tests.log381passed36.09s EXIT0; frozen offline sync45packages EXIT0; Phase0/Phase2 actual CLI EXIT0. Five viewed native-browser screenshots cover three unknowns, malicious refusal and nonnumeric delay refusal. Protected/scope checks pass. Council and local commit remain pending; Phase2 is not closed.

### Phase2 council R1 fixes — execute before R2
- [x] O1/S1: static audited errors; visible-ASCII key validation; replay/envelope shape validation; UI accepts only validated proposal objects. Malformed input/key regressions in test_phase2_council.py.
- [x] S2/O3/O4/G4: indexed calendar evidence (at most2 date parses per exception), output-row limit, CSV/encrypted archive refusal, unsupported frequencies refused.
- [x] G1: queue/dossier stay usable with unknown until explicit run observation choice; UI selector and audited/exported choices. API and full-AppTest pass.
- [x] O2/G3/O5/O6/O7: normalized injection markers; declared drafting origin carried through form/CLI; mapping timezone retained with basis; month declaration within full date range.
- [x] G2 reviewed against official GTFS: agency timezone retained correctly; valid foreign stop zone cannot shift stop_times, invalid stop zone refused. Disputed conversion recommendation recorded in decisions/review.
- [x] R2 final checks415passed39.00s EXIT0/networkdenied, actualPhase0/Phase2CLI EXIT0, scope/protected checks.128-file review freeze; council/local commit remain pending.

### Phase2 council R2 fixes
- [x] S1: replay version/string metadata validated before licence set membership; malformedlist/object API/actualCLI/AppTest refusal regressions pass.
- [x] O1/O2: deeply nested JSON and corruptcompressedZIP normalized to audited refusal; no partialcapture.
- [x] O3/O4: no-source/no-mappingtimezone basis=none; ordinary month prose accepted, explicit unknownmonth/contradictions stillrefused.
- [x] Focused71tests3.81s EXIT0/networkdenied/sixkeysunset.
- [x] Finalfullsuite429passed40.09s/networkdenied, actualCLIPhase0/2EXIT0; R3freeze128files. Focusedcouncil/localcommit remainpending. Phase3 stillhelduntilPhase2closes.
