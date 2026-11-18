# Phase 2 council R3 — Codex Sol focused read-only review

**Verdict: APPROVE. Score: 9/10.**

No new product findings. **P2-R2-S1 is verified fixed**, and the four low residuals P2-R2-O1–O4 are verified fixed in the scoped paths. No material regression was found in the five-file correction. This closes my R2 changes-requested objection; it is not a claim that arbitrary future malformed inputs are exhaustively covered.

## Reviewed boundary and evidence

Read `.handoff/phase2-r3-evidence.md` first, then the handoff skill, global/project memory, all three R2 reports, review ledger, KICKOFF section 0, common gates, model policy and Phase 2. Read all five changed files, relevant UI/CLI paths and the test/acceptance helpers. Compared actual R3 text against the retained R2 review copy after verifying that copy against all 128 R2 hashes. The full diff is `delta.diff` in this review directory.

| Item | Independent result |
|---|---|
| **P2-R2-S1: replay metadata** | `cache.replay` now requires a dict, exact integer version 1 (Boolean and float versions refused), string source_text/dataset/licence, and a string optional bundle **before** comparison, hashing or licence set membership. Independent probes cover null/list/object/Boolean/integer/float values for the four string fields, malformed versions and missing required fields. Direct cache failures are static ValueError; `propose` returns `accepted=false`, `proposal=null`, `reasons=[replay_input_mismatch]` and exactly one refusal audit event, with no capture or mapping mutation. |
| **S1 actual CLI and production UI** | Separate list and object licence probes run the installed `nightdesk text propose` command with imports from the copy. Each exits 1 with JSON refusal, empty stderr, no traceback and a new `text_request_refused` audit. Production `render_text_intake` via Streamlit AppTest shows exactly `Proposal refused: replay_input_mismatch`, no AppTest exception, unchanged empty fields/quotes, manual drafting origin, one new refusal audit and no capture. The full suite also exercises seven malformed metadata cases across API/CLI/AppTest. This is UI behavior evidence, not a fresh visual claim. |
| **S1 normal/rejected proposal behavior** | Valid external replay works with the optional bundle absent or a valid string. A malformed proposal still produces `replay_proposal_invalid`; no capture is created. Existing local cache/hash/consent regressions pass in the full suite. |
| **P2-R2-O1: deep JSON** | Independently supplied 50,000-level JSON, under the response byte limit, is contained in replay, mocked model envelope and mocked model content. Replay gives `replay_input_mismatch`; model paths give `mistral_transport_or_response_invalid`; all return no proposal, audit the refusal and create no capture. Separate TypeError/RecursionError fallback probes give static `text_input_or_response_invalid` and never echo a synthetic exception marker. The full suite also passes the new deep-JSON regressions. |
| **P2-R2-O2: corrupt compression** | Authored a compressed ZIP with an invalid DEFLATE block. First independently confirmed that direct `ZipFile.read` raises actual `zlib.error`; production import then gives static `gtfs_unreadable_archive`, `gtfs_import_refused` audit and no capture. Additional mocked EOFError/LZMAError parser failures also follow that refusal path. The actual corrupted-deflate project regression passes. |
| **P2-R2-O3: timezone provenance** | Independent four-way source/mapping timezone matrix verifies `source_field`, `declared_mapping`, or `none` according to actual evidence. Missing both retains `timezone=None`. No new timezone feature added. |
| **P2-R2-O4: ordinary month prose** | Both reported ordinary-prose sentences pass. Known month declarations still check the range; December outside the November range refuses. Explicit colon/dash unknown months refuse with `declared_month_unknown`. Independent English/German cases and existing range regressions pass. |

The four production changes are small and confined to metadata validation, static exception containment, provenance labelling and month declaration precision. No UI, dependency, config, mapping or fixture changed from R2. R1 high/medium fixes were not reopened: the actual 429-test run includes their regressions. P2-R1-G2 remains resolved in favor of agency-timezone conversion; the relevant source and regression are unchanged and the regression passes. I did not re-fetch the official spec in this network-denied execution review; the R2 reports supply the prior primary-source verification. P2.8, Phase 3 and accepted Phase 1 limits were excluded.

## Freeze and isolation

- Checkout: `/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a`.
- Branch `phase2`, HEAD `1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e`, independently checked before and after.
- All **128** R3 snapshot entries match the checkout and review copy before and after. R2 and R3 have identical path sets; their hash delta is exactly `.handoff/phase2-r3-delta.json`: `adapters/gtfs.py`, `intake/text.py`, `llm/cache.py`, `llm/client.py`, `tests/test_phase2_council.py`.
- Review directory: `/tmp/nightdesk-p2-r3-sol-_hnr0867` (macOS resolves /tmp to /private/tmp). Copy excludes data, .git, .venv, .handoff, Praha, __pycache__, *.pyc and .pytest_cache. Only dependency reuse is a symlink to the existing .venv, used with `uv run --offline --no-sync`.
- Empty `.handoff` was created **inside the copy only**. Phase 2 acceptance writes its workspace pointer there. Synthetic acceptance workspaces are temporary; no checkout data was read or written.
- The environment probe passed: `nightdesk.llm.cache.__file__` resolves under copy/src, all six credential variables are absent, ordinary Python is not isolated, bytecode writing is disabled, and a socket connection raises PermissionError under the network-denying sandbox.
- No delegation, git mutation, checkout source/.handoff writes, live Mistral call, real key access, spend or browser activity. Tests use in-process synthetic placeholders only with mocked transport. No fresh image/visual verification claimed.

## Actual commands and exits

`REVIEW=/tmp/nightdesk-p2-r3-sol-_hnr0867`. Exact wrapper is retained as `run.sh`:

```bash
cd "$REVIEW/copy"
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REVIEW/copy/src" \
  PYTEST_ADDOPTS="-p no:cacheprovider --basetemp=$REVIEW/pytest-$label" \
  sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  uv run --offline --no-sync "$@"
```

| Actual command | Exit / result | Evidence |
|---|---|---|
| `bash "$REVIEW/run.sh" full pytest -q` | **0 — 429 passed in 42.97s** | `full-tests.log` |
| `bash "$REVIEW/run.sh" independent-final pytest -q -s "$REVIEW/test_independent_r3.py"` | **0 — 62 passed in 0.70s** | `independent-final.log`, authored `test_independent_r3.py` |
| `bash "$REVIEW/run.sh" phase2 python tests/phase2_acceptance.py` | **0 — PHASE2_ACCEPTANCE_PASS** | `phase2-acceptance.log` |
| `bash "$REVIEW/run.sh" phase0 python tests/phase0_acceptance.py` | **0 — all six steps and JSON/XLSX/flatten/import pass** | `phase0-acceptance.log` |
| Initial independent probe run with 2,000-level nesting | **1 — 61 passed, 1 failed**; reviewer expected a decoder error code, but that nesting decoded and was safely refused as `proposal_schema_invalid`. Changed only the temporary probe to the specified 50,000 levels; final run above passes. | `independent.log` |
| Snapshot/delta verifier, before and after | **0 — 128 checkout/copy matches, HEAD/branch unchanged** | `freeze-before.json`, `freeze-after.json`, `snapshot.json`, `delta.diff` |
| `git diff --check -- src tests mappings pyproject.toml uv.lock` | **0** | `freeze-after.json` |
| Unrestricted `git diff --check` | **2 — trailing whitespace in the parent's updated `.handoff/state.md:28`**, outside the frozen product and five-file correction. Documentation housekeeping only; not a product finding. This reviewer left it unchanged. | `freeze-after.json` |

Phase 2 acceptance independently preserved three unknown cases (`different_boundary_points`, `ambiguous_local_time`, `incomplete_capture`), identical replay stdout, three poisoned-notice refusals, the 27-asset demo check and GTFS **22 accepted / 0 rejected**, scheduled/unresolved only. Phase 0 checks its network-denial probe and actual CLI import/export flow. The pre-existing Phase 0 stdlib-only child socket probe uses `-I`; all application/tests/probes use ordinary Python as requested.

## Parent ledger disposition

No new open rows. Mark/retain **P2-R2-S1 fixed**, independently verified by the API/actual CLI/production AppTest probes above. Retain **P2-R2-O1, O2, O3, O4 fixed**, independently verified above. Keep correct agency-timezone conversion and existing accepted scope limits. Parent may copy this report and its evidence; this review did not modify the checkout ledger or handoff files.
