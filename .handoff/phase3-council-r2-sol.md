# Phase 3 council R2 — independent Sol retry review

**APPROVE — 9/10. No material findings.** Independently verified P3-R1-S1, P3-R1-O1 and P3-R1-O2 against the frozen R2 product. No regression found in the tested local scope. No finding IDs added. Parent may copy this report into the handoff; this reviewer made no checkout/handoff/venv/Git writes.

## Corrections independently verified

- **S1 — fixed.** `src/nightdesk/changes.py:98–113,134–144` checks the raw envelope's date projections against canonical dates and checks individual periods against the canonical range before permitting expiry/entry. The result for contradictory evidence is `membership_unknown / canonical_raw_validity_conflict`, retaining canonical dates, parsed raw bounds and the source reference. My eight ordinary confirmed JSON intake cases used renamed source columns, real persisted captures and no load/time mocks: old/new envelope conflicts, old/new individual-period conflicts, matching raw clocks, and matching inclusive raw dates. Conflicts remain in the eligible R2 presence list; consistent clocks/dates still permit proven expiry/entry. Two further persisted-revision probes verified timezone-offset projections in the declared Europe/Berlin zone. The full suite independently passed the real dossier, JSON/Markdown export and audit regression for conflicting evidence.
- **O1 — fixed.** `changes.py:227–228` excludes only proved `expired_out_of_window` and `entering_window` classifications from the R2 presence lists. My 24 independently authored persisted-revision comparisons covered both sides, complete/incomplete captures and six unresolved cases: absent zone, unknown zone, empty individual periods, malformed individual period, DST fold and DST gap. Each retains a source-linked unknown annotation; each complete/equal-filter capture pair retains its selected-source presence row. Incomplete captures still produce no added/removed conclusions. Audit payloads were asserted against returned membership evidence for every case.
- **O2 — fixed.** `changes.py:116–122,149–171` gathers direct and role declarations from both captures and refuses contradictory explicit hours. My seven conflicting-policy probes covered direct declarations, role declarations, both together, conflicting roles, fixed policy, null policy and boolean hours. Two additional probes covered a declaration present only in the old or only in the new capture. All reported `rolling_window_conflict` with declarations and selected hours retained. Three equal-policy probes retained the exact previous edge with no selection, integer selection and equal float selection. Two absence controls proved explicit hours fill absent policy and filter mismatch still blocks entry. Three edge-second probes confirmed -1 second retains ordinary presence, equality and +1 second permit entry. Together with the S1/O1 cases: **51 independent probes passed**.

The R1→R2 snapshot comparison independently confirms exactly three changed paths and no new paths: `src/nightdesk/changes.py`, `tests/test_window_membership.py`, `docs/THREAT_MODEL.md`. Dependencies and all other frozen product files are unchanged. The threat-model correction honestly documents historical local checkpoint refs and verification of the intended branch before any future authorised push. I made no claim about all refs lacking data and performed no Git object scan or ref mutation.

## Isolation and commands

Review directory: `/tmp/phase3-sol-r2-retry-2svlkeu5` (macOS canonical alias `/private/tmp/phase3-sol-r2-retry-2svlkeu5`). Isolated product: `copy/`. Copied only `src`, `mappings`, `tests`, `docs/THREAT_MODEL.md`, `pyproject.toml`, `uv.lock`, excluding bytecode/caches; created `.handoff` only in the copy. Checkout `.venv` is a symlink, protected against writes by the OS sandbox. No installation, sync or dependency change occurred. No original `data/`, `.git` or private source tree was copied. Original data content was neither read nor copied; no Praha access occurred.

The guard proved product imports resolve inside `copy/src`, Python isolation flag is 0, bytecode is disabled, all six specified credential variables are absent, loopback `connect_ex` is denied with errno 1, and directory reading of original `data/` is denied. Zero `.pyc` files were left under copied src/tests. The socket probe made no successful connection. No external request, live model, account action, external scan, push, delegation or Phase 4 work occurred.

All executed product checks used this prefix, from the isolated `copy/` directory:

```sh
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/private/tmp/phase3-sol-r2-retry-2svlkeu5/copy/src \
  UV_CACHE_DIR=/private/tmp/phase3-sol-r2-retry-2svlkeu5/uv-cache \
  /usr/bin/sandbox-exec -f /private/tmp/phase3-sol-r2-retry-2svlkeu5/deny.sb \
  uv run --offline --no-sync python -B
```

Sandbox profile:

```scheme
(version 1)
(allow default)
(deny network*)
(deny file-write* (subpath "/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a"))
(deny file-read* (subpath "/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/data"))
```

The stdlib command runner was invoked as `/usr/bin/python3 -B /tmp/phase3-sol-r2-retry-2svlkeu5/run.py NAME SUFFIX...`; it launches the exact sandboxed prefix above and records command arrays, outputs and exits. These are the verification suffixes:

| Suffix | Exit and evidence |
|---|---|
| `/tmp/phase3-sol-r2-retry-2svlkeu5/guard.py` | 0; `guard.log`, `guard-result.json`; import/env/network/data-denial checks above. |
| `-m pytest -q -p no:cacheprovider --basetemp=/tmp/phase3-sol-r2-retry-2svlkeu5/pytest-full` | **0; 475 passed, 1 skipped in 58.44s**, `full-tests.log`, `full-tests-result.json`. Only expected restricted local German data test skipped; synthetic cases passed. |
| `-m pytest -q -p no:cacheprovider --basetemp=/tmp/phase3-sol-r2-retry-2svlkeu5/pytest-probes-final /tmp/phase3-sol-r2-retry-2svlkeu5/probes/test_focused.py` | **0; 51 passed in 0.49s**, `focused-probes.log`, `focused-probes-result.json`. |
| `/tmp/phase3-sol-r2-retry-2svlkeu5/run_acceptance.py` | **0; actual Phase 0, 2 and 3 acceptance each exit 0**, `cli-acceptance.log`, per-phase logs. |
| `/tmp/phase3-sol-r2-retry-2svlkeu5/check_hashes.py` | **0; original 145/145 and copy 145/145 match**, `after-hashes.log`, `after-hashes.json`. |

CLI acceptance adaptation: `run_acceptance.py` executes the unchanged copied scripts with `runpy` and removes only the exact redundant `sandbox-exec -p '(version 1)(allow default)(deny network*)'` prefix on child commands. All parents and children retain the inherited outer OS denial, including checkout write and original-data read denial. This follows the brief's macOS nested-sandbox workaround; no product/test file was patched. Removed wrapper counts: Phase0 19, Phase2 7, Phase3 9. Actual CLI subprocesses and expected refusal exits appear in `phase0-acceptance.log`, `phase2-acceptance.log`, `phase3-acceptance.log`. Phase0 stdout parity and socket errno1 check passed; Phase2 printed `PHASE2_ACCEPTANCE_PASS`; Phase3 printed `PHASE3_ACCEPTANCE_PASS`, including NDA refusal and externally sealed tail-cut failure. Demo check passed 27 hashed CC0/synthetic assets.

Harness corrections disclosed: the first guard attempt exited 1 because its assertion compared resolved `/private/tmp` against unresolved `/tmp`; resolving the expected root fixed the assertion. The first probe run exited 1 with 41 passes and 10 frozen-instance setup errors because the probe attempted to assign frozen WorkNotice fields. Constructing validated replacement instances fixed only the reviewer probe. Final 51/51 passed. Initial probe evidence is preserved in `focused-probes-initial.log` and corresponding command/result JSON. No product defect or edit resulted. An exploratory combined read command exited 1 because `tests/conftest.py` does not exist; this was unrelated to verification.

## Freeze evidence

Before copying/execution: original **145/145 match, 0 mismatches**; copy **145/145 match**. Evidence: `before-hashes.json` and setup command output. After all tests/probes/CLI: original **145/145 match**, copy **145/145 match**, 0 mismatches and 0 copied bytecode files. Evidence: `after-hashes.json`, `after-hashes.log` (exit0). The report is the only subsequent write, under this review directory.

R2 manifest SHA256: `d393958db195bad0c792e5cd61750a3b8a8d426e8a65d61ee499d3944198e8f8`.

Verified before and after:

| Changed product path | SHA256 |
|---|---|
| `src/nightdesk/changes.py` | `ba30e395b1fff1c140cf44dc8e0ba02ff416d4bac3e6eba08af064713241f0e9` |
| `tests/test_window_membership.py` | `266440f48ce2ca6a794fd943329ef916517b94025b260af6d30d2b393eadcd8b` |
| `docs/THREAT_MODEL.md` | `6beafa8aabb1754b6b0cc78a091a9952474d57db580e48d8012f64a91e13b09b` |

## Limits and conclusion

Full regression includes the authored Phase3 swap, collision/isolation AppTest, NDA policy, sealed-audit-copy and spreadsheet safety tests. Existing real dossier/export/audit conflict tests passed. No visual/browser review was performed or claimed. Parent German real-data counts and parent browser evidence were not independently reproduced; original captures were excluded and the local-data skip is intentional. Live Mistral, live Aikido entitlements/results, account/remote state and historical Git blob contents were not checked. No new evidence reopens accepted lows P1-R6-O1 or P2-R3-O1. G1 remains the documented local checkpoint-ref limitation; no deletion or history rewrite was attempted.

**Independent verdict: APPROVE, 9/10.** S1/O1/O2 fixed; no remaining material finding within this focused R2 review and no regression found in the executed checks. This verdict does not authorise any remote, account, external scan, push or later-phase action.
