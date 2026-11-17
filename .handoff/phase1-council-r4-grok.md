# Phase 1 council R4 — Grok review

**APPROVE — 9/10.** No material, reproducible Phase 1 regression found. The R3 cubic queue enumeration blocker is fixed, and the two R3 nonblocking boundary findings are fixed. No Phase 2 requirement is included. The approved certifi exception was not reopened.

## Scope check

- `.handoff/phase1-council-r4-snapshot.json`: **93 entries, 93 matching SHA256 hashes before the runs and 93 matching after. Zero missing, zero mismatches.**
- Snapshot file SHA256: `f72830b4087866dbefc9bf540d8174fb3f72c608f0cdf43d38a295a6abc9bbfc`.
- Against `.handoff/phase1-council-r3-snapshot.json` (92 entries): the only added path is `tests/test_phase1_queue_scale.py`. The only changed hash is `src/nightdesk/desk.py`. No paths were removed.
- `desk.py` checkout and copy SHA256 both `b3ae878acfc890242963e90b303d5d8ffc1b377e7798ecb14590adb403b05a6b`, matching the R4 snapshot.
- Checkout `git status --porcelain` was identical before and after. No checkout edit, handoff write, checkout `data/` read, delegation, commit, push, or network fetch was performed.
- Product code executed from `/tmp/nightdesk-phase1-r4-grok/workspace`. `nightdesk.desk.__file__` was `/tmp/nightdesk-phase1-r4-grok/workspace/src/nightdesk/desk.py`. The checkout `.venv` was symlinked and not rewritten. No `uv sync`.

## Sol blocker — fixed

`_index_context` (`desk.py:71–87`) builds sequence, capture position, and run train/date indexes on the operation context and returns when `legs_by_sequence` is already present. There is no module-level or cross-context cache. Two contexts in one process did not share index objects or revision ids.

`_boundary_findings` (`desk.py:90–102`) checks only sequence−1 and sequence+1 candidates for the selected leg, ordered by capture position. On a shuffled capture with two legs at the same sequence, the call order matched a capture-order nested loop restricted to pairs whose sequences differ by +1. Reverse and non-adjacent pairs are not checked. `border.py` is unchanged from R3 and still defines adjacency as `sequence + 1`.

Independent instrumentation, not the project test:

| Case | Result |
|---|---|
| 100 / 400 / 800 legs, all sequence 1, two sides | sequence reads **200 / 800 / 1600**, exactly `2n`; `check_boundary` calls **0** |
| 500 sequential legs, two sides | **1996** calls, exactly `4*(500-1)`; every call was sequence `k, k+1` |
| 30 sequential legs, two sides, counting run-list iteration | **2** scans, one per context |

Real imports of legs-only synthetic captures, all sequence 1, distinct trains, one date, no works, runs, or links. Both captures complete. Queue returned exactly n rows. `check_boundary` calls during queue and one dossier: **0**.

| Legs | Import (s) | Queue (s) | One dossier (s) |
|---:|---:|---:|---:|
| 200 | 0.508 | 0.261 | 0.320 |
| 400 | 0.976 | 0.511 | 0.637 |
| 800 | 1.924 | 1.057 | 1.289 |

These are this run's local synthetic timings, not a general throughput claim. Queue time scaled about 1.96× from 200 to 400 and 2.07× from 400 to 800. The 800-leg queue was **1.057s**, against the R3 measurement of **58.965s** for the same shape of synthetic queue. The project tests encode the same bounds: `tests/test_phase1_queue_scale.py:13–45`.

## Opus nonblockers — fixed

On the synthetic three-leg capture with the first v2 leg removed and the explicit journey link selected:

- The remaining `bb:202` dossier has exactly one `adjacent_leg_not_observed`, result `unknown`, rule `adjacent_leg_presence`, rule version `border-presence-v1`.
- Detail names the after capture and the before neighbour revision, includes that neighbour's source record, and the limits text is: "Neighbour evidence is from the other selected capture; no current boundary check or cancellation is inferred."
- No `left_at` / `right_at` is attached, and the removed row stays `source_record_removed` with after-check `leg_not_observed`. The before side does not invent a missing neighbour.
- The existing `bb`/`cc` agreement remains. The old instant mismatch is not kept once `aa` is absent.
- The same dossier without `link_identifier` has no `adjacent_leg_not_observed`.
- A link that covers `bb` and `cc` but not `aa` produces no presence finding, and the `bb`/`cc` agreement remains.
- `cc:303` is not adjacent to the removed leg and does not receive the finding. It also stays out of the queue when its own fields and adjacent checks are unchanged.
- `no_run_selected` appears once. The duplicate append is gone (`desk.py:150–154`).
- Queue `checks_after.border` equals the dossier summary for that leg.
- `comparison_checked` and `dossier_checked` audit payloads record `boundary_presence: border-presence-v1` (`desk.py:280` and `desk.py:336`). The removed-neighbour run recorded 5 such version fields, all that value.

Unmodified v1/v2 still shows one `boundary_instants_differ` and one `agrees_on_checked_fields` on `bb:202`, and does not show `adjacent_leg_not_observed`. The CLI/API check on `aa:101` still has grade A count 1 on the before side.

Same-network adjacent absence produces **zero** presence findings. That matches the existing `border.py:34–35` refusal of same-network pairs, and the different-network `bb`/`cc` agreement still appears. This is the existing boundary rule, not a new removal claim.

Declared-incomplete v2, with `aa` omitted, is not a regression: comparison reason is `incomplete_capture`, `changes.removed` is empty, and the omitted leg stays `record_presence_unknown`. The remaining linked leg also gets one unknown `adjacent_leg_not_observed` and is queued as `checks_changed` (`desk.py:105–115`). The finding does not carry a current instant and its limits text refuses a cancellation. Present-pair agreement is withheld by the unchanged incomplete-capture gate in `border.py`. No change requested.

## Commands

Wrapper for every product command:

```sh
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/nightdesk-phase1-r4-grok/workspace/src \
  UV_CACHE_DIR=/tmp/nightdesk-phase1-r4-grok/uv-cache \
  PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/nightdesk-phase1-r4-grok/pytest-temp' \
  sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  uv run --offline --no-sync <command>
```

Working directory was the temporary copy. Logs: `/tmp/nightdesk-phase1-r4-grok/logs/`.

| Command | Exit | Result |
|---|---:|---|
| `python -c` import `nightdesk.desk` | 0 | Loaded the copy |
| `pytest -q tests/test_phase1_queue_scale.py tests/test_phase1_presence.py tests/test_border.py tests/test_desk.py` | 0 | **23 passed in 5.01s** |
| `pytest -q` | 0 | **330 passed in 22.46s** |
| `python tests/phase0_acceptance.py` | 0 | Six acceptance steps, identical denied-network stdout; alternate YAML; JSON/XLSX; merged-header refusal, flatten, ingest |
| enumeration probe | 0 | Counts above; `ENUMERATION_OK` |
| boundary probe | 0 | Cases above; `BOUNDARY_OK` |
| queue benchmark | 0 | Table above; `BENCH_OK` |
| CLI integration | 0 | Below; `CLI_OK` |
| snapshot hash before and after | 0 | `HASH_OK` both times |

Credential check: all six names absent. Loopback connect failed with **errno 1**.

CLI, bundle `test-r4-cli`, actual `nightdesk` process: unconfirmed v1 import exit 1; confirm/import v1 and v2 exit 0, both complete, rejected 0. API confirmed the instant mismatch and grade A, and no presence finding on the unmodified pair. Review exit 0. v2 reimport kept capture `1b050949299c4df57b6e0b4672a8352221ef1c83ade8ffb5b6ead600e30be6ed`. v3 import marked that reviewed revision stale. `syn_bad` imported `complete=False rejected=1`; rejects lists `invalid_work_dates`. Seal valid, count 86, hash `99a201f5de0fac79ba9d90144452d9693cafef19bf59e6cc2af7abe3406a63ba`. Verify with that seal exit 0. One-byte audit corruption made verify exit 1 (`invalid event schema`). Restored bytes verified exit 0.

The first enumeration and boundary launches exited 1 in the harness: a probe treated the module `__cached__` attribute as a cache, and the copied capture manifests resolved `../../../../mappings` from a shallower directory. Neither executed a different product. The CLI's first launch reached a valid seal and then stopped in the reviewer's hash parser before the tamper step. The reruns above are the recorded results.

## Visual evidence

I viewed these saved screenshots. I did not start a browser or server.

- `.handoff/phase1-r3-prepared-adjacent.png`: selected journey link and reviewed points `syn:border1,syn:border2`; an agreement limits block for the checked point; then `unknown: adjacent_leg_not_observed` with rule `adjacent_leg_presence` and rule version `border-presence-v1`.
- `.handoff/phase1-r3-removed-date.png`: Synthetic dates before/after captures and `mismatch: operating_dates_differ` under `adjacent_same_boundary_event` / `border-v1`.
- `.handoff/phase1-r3-group-choice.png`: dossier asks for a source leg and says no source leg is selected automatically.
- `.handoff/phase1-r3-group-dossier.png`: both selected captures show the source present, with the sentence that an absent source record does not establish cancellation or withdrawal.

## Verdict

**APPROVE, 9/10.** No material Phase 1 regression. Stop. Parent records the ledger. No Phase 2 work.
