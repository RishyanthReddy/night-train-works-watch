# Phase1 completion audit — builder checkpoint

Authority: KICKOFF.md section0 and section9 P1.1–P1.13; latest user instruction requires STOP before Phase2. This is a requirement/evidence map, not a claim that council or commit is finished.
Current product:93 files, phase1-council-r4-snapshot.json SHA256 assertions pass. Main suite330 passed22.04s with OS networking denied and six credential variables unset. All earlier tests are included; new tests verify queue enumeration bounds and missing-neighbour evidence.

| Requirement | Current evidence | Status |
|---|---|---|
|P1.1 time rules|timeutil.py; test_timeutil.py: midnight start weekday, inclusive end clipping, periodical/continuous, DST ambiguity/gap, UTC half-open, pass priority and missing/reversed time tests; current330-test run|verified|
|P1.2 all14 named rail model types|AST class-name assertion; test_rail_models.py/test_model.py in current run|verified|
|P1.3 typed mappings, immutable revisions, N1/N3/R1/R2, completeness and gates|test_store.py/status/dataset/idempotence/uncertain identity/reject/predecessor; test_phase1_integrity_scale.py artifact/declaration/source/predecessor tamper and operation-scoped loading; path/crosswalk fixtures and YAML|verified|
|P1.4 header mapping, ordered run/segment semantics, three CC0 full-run subsets including midnight|test_runs.py D1/D2/D4/D7/station-area exclusion/header drift; runs/manifest.json hashes/counts rechecked; README/source manifest records historical CC0 evidence|verified within committed subsets; optional full-data recount is historical evidence only|
|P1.5 explicit sourced and human journey links|test_links.py includes real CLI confirmation and unsupported rule/cross-bundle refusal; no guessed join|verified|
|P1.6 selected revision/capture ChangeSets, N2/N7/R2|test_changes.py; source-field presence, same subject, incomplete capture, distinct filter, source add/remove and operating-date regressions in test_phase1_presence.py|verified|
|P1.7 date/weekday/clock/pass/place checks, no fallback A|test_match.py and integrity regressions; match-v3 named-line-only window, unknown-hop reason, exact endpoints retain A with explicit line disagreement, path_unresolved cap; literal W5 off-path B recorded in decisions|verified within selected evidence rules, no prediction claim|
|P1.8 narrow boundary rule/unknown reasons|test_border.py exact instant/kind/point/date/complete-capture/link/identity; removed-date after-revision binding test; missing-neighbour sourced unknown regression; actual adjacent screenshot|verified|
|P1.9 local revision-bound decision/follow-up, stale, three statuses|test_review.py and council regressions A-B-A/reanswer; fresh actual CLI integration stale/reopened/answer, source/import/local statuses separate in models|verified|
|P1.10 local dossier MD/JSON|test_dossier.py + presence tests; before/after source absence, full work/source/extra/run evidence, unknowns/reviews/questions, escaped source fields; actual CLI local export|verified|
|P1.11 plain queue/dossier/reject/audit UI in real browser|phase1-p11/accept/r2/r3 viewed PNGs and recorded workflows; current AppTest suite; sourceleg choice/group dossier and removed-date mismatch freshly viewed; T3 screenshot-frame failure documented, separate agent-browser fallback used and closed|verified with screenshot provenance/limits preserved|
|P1.12 chain/verify/seal/edit/remove/tail/fullrewrite|test_audit_chain.py and fresh CLI seal/verify/tail/edited-event refusal. Local internal consistency only, trusted external seal required for tail/full-rewrite detection|verified within stated limit|
|P1.13 syn complete v1/v2, three networks, A/B/unlocated/unknown/mismatch; rejected syn_bad|test_batch.py and fresh CLI integration; source manifests synthetic; v1/v2 complete, syn_bad invalid_work_dates incomplete|verified|
|App acceptance import/open sourced before/after, grades/mismatch/reject, local review/owned question/export, identical reimport, stale v3|phase1-evidence.md and viewed phase1-accept/r2 PNGs; current AppTest and actual phase1-r4-cli.log cross-check same flow|verified; no real operational change asserted|
|Repeat small swap, prior Phase0|phase1-r4-phase0-acceptance.log EXIT0: six steps, alternate YAML equivalence, JSON/XLSX sniff/ingest, merged-header refusal then explicit flatten/import, network-denied probe|verified|
|Scope, data/licences/secrets, no remote/push|93-file snapshot only allowed Phase1 paths; protected baseline hashes checked; synthetic fixtures labelled, CC0 manifests hashed; certifi exception recorded; prior commit preflight no tracked data/remote or secret-pattern hit|verified for checked paths/patterns; no claim scanners prove source truth|
|Independent council findings fixed|R1/R2 closed in review.md; R3 Sol queue blocker and Opus explanation/duplicate fixed; current330 tests and800-leg queue1.185s. R4 all three approved9/10|verified: unanimous R4 APPROVE9/10;93 hashes matched|
|Local commit and final handoff|explicit candidate path list exists but must regenerate after R4; HEAD still d340990; no Phase1 commit yet|PENDING approval then local commit/hash checks/handoff|
|Stop before Phase2|state/next/TODO/decisions preserve user's checkpoint; no Phase2 implementation files|held for user continuation|

Commands: phase1-r4-offline-tests.log, phase1-r4-phase0-acceptance.log, phase1-r4-cli.log and phase1-r4-queue-scaling.log all contain EXIT:0. Initial extra CLI setup failed from resolving the venv interpreter symlink to base Python; corrected invocation passes, no code was changed for setup.

Limits: no crash-recovery guarantee or operational source truth, no national approval or whole-journey feasibility, no forecast, no Phase2 name/GTFS/text-model door, no Phase3 external scanner connection. Off-path B is conservative literal W5 semantics and may be numerous. No review score is invented; R4 results all APPROVE9/10. Mixed-request expansion is an explicitly accepted nonblocking limit (P1-R4-O1).
