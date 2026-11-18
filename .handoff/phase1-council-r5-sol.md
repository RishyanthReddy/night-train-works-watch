# Phase1 council R5 — Codex Sol focused read-only review

**APPROVE — 9/10. No reproducible material blocker in the five-file delta.**

Reviewed HEAD `ff4581bd05815305f8b9b475b9ba7472291c4217` with the approved Phase1 base recorded in state. Read current state, decisions, next, sources, review ledger, the R4 Opus note and relevant KICKOFF boundary/Phase1 rules. Scope: `src/nightdesk/desk.py`, `src/nightdesk/links.py`, `src/nightdesk/ui/app.py`, `tests/test_phase1_queue_scale.py`, and new `tests/test_boundary_scope.py`. No Phase2 review or implementation.

No checkout or handoff edits, checkout data reads, delegation, network fetch, commit or push. Execution used this report's `ws/` copy of src/tests/mappings/config and synthetic fixtures only. `.venv` is a read-only-use symlink to the existing environment; no sync/install/rewrite command was run. Per the task, the parent records the ledger.

## Integrity

- Before execution: all **94/94** SHA256 entries in `.handoff/phase1-council-r5-snapshot.json` matched the checkout (initial command output).
- After execution: **94/94** match in both checkout and temporary copy; manifest unchanged; `python3 check_hashes.py` exit **0**, retained in `integrity.log`.
- Git product diff is the four tracked files above plus the new boundary-scope test. `git diff --check` on the tracked delta exited **0**.

## Reproducible checks

Run the commands from this review directory. `run.sh` changes into its temporary `ws/` and executes:

```sh
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/nightdesk-p1-r5-sol-rjpn9ypq/ws/src:/tmp/nightdesk-p1-r5-sol-rjpn9ypq/ws/tests \
  PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/nightdesk-p1-r5-sol-rjpn9ypq/pytest-tmp' \
  sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  uv run --offline --no-sync "$@"
```

| Command | Exit | Evidence |
|---|---:|---|
| `./run.sh pytest -q` | 0 | `full.log`: **336 passed in 37.39s**, including AppTest |
| `./run.sh pytest -q /tmp/nightdesk-p1-r5-sol-rjpn9ypq/test_independent.py` | 0 | `probes.log`: **16 passed in 0.88s** |
| `./run.sh python tests/phase0_acceptance.py` | 0 | `phase0.log`: six acceptance steps, JSON/XLSX, merged-header refusal/flatten/import; network-denial probe errno **1** |
| `./run.sh python /tmp/nightdesk-p1-r5-sol-rjpn9ypq/scale.py` | 0 | `scale.log`: actual mixed-request queue and boundary-call assertions |
| `./run.sh python /tmp/nightdesk-p1-r5-sol-rjpn9ypq/cli_probe.py` | 0 | `cli.log`: real capture confirm/import, link import, local review and sealed audit verification; API mismatch/choice/JSON export assertions |

The one-off scaling/CLI scripts retain their synthetic workspaces; use a fresh output-directory name before rerunning those scripts. An initial independent probe incorrectly expected an unchanged ambiguous neighbour to appear in the queue; selecting its revision directly corrected the harness. The initial CLI harness parsed a labelled output line as an identifier; extracting its identifier corrected the harness. Neither required a product change.

## Findings and acceptance

No material findings requiring severity/file/line entries or code changes.

- **Unlinked scope:** one sourced `boundary-scope-v1` unknown per leg; no pair calls, and unchanged unlinked neighbours do not enter the queue just because capture locators differ. Covered by new regression and independent `test_unchanged_unlinked_legs_not_queued_when_other_leg_changes`.
- **Explicit link/date eligibility:** only the selected journey's members reach pairing. Independent coverage checks exhaustively compare 84 ordered combinations of wildcard, matching date, different date and unsupported rule against the former semantics. Different national request IDs retain a genuine comparison.
- **Competing choices:** existing/new tests cover same train with same or different sequence, and an independent different-train sequence collision. All stay unknown until an explicit valid choice. Too many choices remain ambiguous; a before-only choice does not select a changed after record. Foreign revision IDs are rejected by both queue and dossier. Excluded records receive `boundary_leg_not_selected`, not an automatic winner or link.
- **Evidence preservation:** selections survive JSON export; chosen IDs and `boundary-scope-v1` appear in the audit event; audit verification passes. Full suite covers UI multiselect propagation. The independent CLI probe also exports a real mismatch after valid explicit selection.
- **Boundary semantics:** 11 independent cases through `_checks` preserve exact agreement, different request IDs, genuine instant mismatch, point/kind/time/review unknowns, incomplete capture, operating-date mismatch even when the selected date is removed, not-operating unknown and uncertain identity. Missing/ambiguous neighbour probes stay unknown, including after one explicit historical source choice. Existing removed-date queue/dossier and missing-neighbour regressions also pass.
- **Visual evidence:** actually viewed supplied unlinked, ambiguous and chosen PNGs. They show the unlinked explanation, source-choice warning, and chosen before/after records with a genuine mismatch. This is inspection of supplied screenshots, not a fresh browser session; the later different-sequence guard is supported by automated tests, not a new visual claim.

## Mixed-request measurement

`scale.py` builds distinct national request IDs, two legs per request, and asserts all unlinked rows have exactly one border entry. No selected link makes **zero** boundary calls. Selecting just `aa:0`/`bb:0` makes exactly **four** calls across both contexts, at every size.

| Legs / requests | Unlinked queue seconds | One two-member link seconds |
|---|---:|---:|
| 100 / 50 | 0.159 | 0.191 |
| 200 / 100 | 0.296 | 0.366 |
| 400 / 200 | 0.576 | 0.721 |
| 800 / 400 | 1.217 | 1.658 |

This independently resolves the R4 mixed-request explosion for the reviewed shape. These are local synthetic measurements, not a general performance guarantee. Phase2 remains held. Stop after this report.
