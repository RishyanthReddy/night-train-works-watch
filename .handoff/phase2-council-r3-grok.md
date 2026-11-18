# Phase 2 council R3 — Grok 4.7

Verdict: **APPROVED**
Score: **9/10**
Reviewer: Grok 4.7, read-only. No product, checkout, `data/`, or checkout `.handoff` writes by this review. No delegation, commit, push, live model call, credential use, or browser session.
Baseline: branch `phase2`, HEAD `1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e` before and after.
Scope: the five-file R3 delta on the 128-file freeze. P2.8, Phase 3, accepted P1-R6-O1, and the G2 stop-zone conversion were not reopened.

No new open ledger rows. The five R2 corrections hold. P2-R1-G2 stays closed: do not convert `stop_times` through `stops.stop_timezone`.

## Freeze

`.handoff/phase2-council-r3-snapshot.json`: 128 files.
Before and after, on the checkout and on the copy: matched 128, missing 0, hash mismatch 0, extra product files under `src/`, `tests/`, `mappings/`, `pyproject.toml`, `uv.lock`: 0.
Against `.handoff/phase2-council-r2-snapshot.json`: the only hash changes are the five paths in `.handoff/phase2-r3-delta.json`. `changed_equals_delta` true.
`git diff --check` exit 0. HEAD unchanged.
Checkout `*.pyc` outside `.git`, `.venv`, `data`, `.handoff`, and `Praha`: 50 before the runs and 50 after. `.venv` mtime stayed `1794933299`. The five delta mtimes were unchanged.
Checkout `.handoff/phase2-acceptance-workspace.txt` still points at `nightdesk-phase2-accept-25rwg999`. This review's pointer was written only in the copy and names `nightdesk-phase2-accept-3u6qh2x8`.

The five-file diff was taken against `/tmp/phase2-r2-grok-copy` after those five files hashed to the R2 snapshot. Production changes are only:

- `llm/cache.py`: `json.loads` `RecursionError` becomes `replay_input_mismatch`; `version` must be `type is int` and equal 1; `source_text`, `dataset`, and `licence` must be `str`; optional `bundle` must be `str`. This runs before the public-licence set test.
- `llm/client.py`: `_send` catches `RecursionError`. `propose` catches `TypeError` and `RecursionError` and uses the static allowlist, otherwise `text_input_or_response_invalid`.
- `intake/text.py`: a month word that is not in `TEXT_MONTHS` is `declared_month_unknown` only when the separator is `:` or `-`; other following words are prose. Known months still use the full-range check. `timezone_basis` is `none` when neither the source field nor the mapping timezone is present. `validate_proposal` also catches `RecursionError` as `proposal_schema_invalid`.
- `adapters/gtfs.py`: `zlib.error`, `EOFError`, and `lzma.LZMAError` join the archive `except` and become `gtfs_unreadable_archive`. `gtfs_instant` and the agency-zone call at the stop-time loop are unchanged.
- `tests/test_phase2_council.py`: appended cases only. Prior assertions were not edited.

## Commands and exits

Copy: `/tmp/phase2-r3-grok/copy` (resolves to `/private/tmp/phase2-r3-grok/copy`). rsync excluded `data/`, `.git`, `.venv`, `.handoff`, `Praha`, `__pycache__`, `*.pyc`, and `.pytest_cache`. Checkout `.venv` was symlinked. No `uv sync`.
`PYTHONPATH=/tmp/phase2-r3-grok/copy/src`. Interpreter: `/tmp/phase2-r3-grok/copy/.venv/bin/python`, not `-I`.
Every run unset `MISTRAL_API_KEY`, `NS_API_KEY`, `SWISS_OTD_TOKEN`, `DB_CLIENT_ID`, `DB_API_KEY`, and `TRAIN_ARCHIVE_TOKEN`.
Sandbox profile: `(version 1)(allow default)(deny network*)`.
`PYTHONDONTWRITEBYTECODE=1`. Pytest addopts: `-p no:cacheprovider --basetemp=/tmp/phase2-r3-grok/pytest-<name>`.
Import check printed `/private/tmp/phase2-r3-grok/copy/src/nightdesk/llm/cache.py`.

| Command | Exit / result | Log |
|---|---|---|
| `freeze.py` checkout, then copy, before tests | **0**, 128/128, five-file delta only | `freeze-before-checkout.json`, `freeze-before-copy.json` |
| `python -c` import check | **0** | `import-check.log` |
| `python -m pytest -q --tb=line` | **0**, **429 passed in 42.47s** | `full.log` |
| `python tests/phase2_acceptance.py` with `.handoff` created in the copy | **0**. `different` / `different_boundary_points`, `clock` / `ambiguous_local_time`, `partial` / `incomplete_capture`. Demo check 27 assets. The two replay stdout lines are equal. Injected, wrong-year, and month-contradiction exit 1 (`text_addresses_model`, `invalid_work_dates`, `month_contradicts_dates`). GTFS accepted=22 rejected=0, `path_unresolved`. `PHASE2_ACCEPTANCE_PASS; no live model request` | `phase2-acceptance.log` |
| `python tests/phase0_acceptance.py` | **0**. Six steps, identical stdout with the six variables unset, network-denial errno 1, JSON/XLSX, merged-header flatten then ingest | `phase0-acceptance.log` |
| First `probe.py` | **1**. `ModuleNotFoundError: No module named 'test_text'` at probe line 29. No product assertion ran. The log was then overwritten | not retained |
| Rerun `probe.py` after adding `copy/tests` to `sys.path` | **0**, `PROBE_PASS`, 0 failures | `probe.log` |
| `pytest --collect-only tests/test_phase2_council.py` | **0**, 48 tests collected | `collect.log` |
| `freeze.py` checkout after the suite and again after the probe | **0**, 128/128 | `freeze-after-checkout.json`, `freeze-after-probe.json` |
| `git diff --check` | **0** | runner stdout |

The parent's separate 71-test command (`test_phase2_council.py`, `test_text.py`, `test_text_security.py`, `test_gtfs.py`, 3.81s) was not repeated as its own process. Those modules are inside the 429.

No live Mistral request. The only key material was the in-process fake `synthetic-secret\n` and `synthetic-placeholder`. The newline key was absent from the audit. The placeholder was absent from the deep-JSON result and audit. No real socket was opened: the probe's connect to `1.1.1.1:443` raised `PermissionError` errno 1.

No new browser claim. The malformed-metadata AppTest is the new UI evidence and it ran inside the 429. The five existing screenshots were not opened again.

## R2 items

| ID | Result |
|---|---|
| P2-R2-S1 | Fixed. List, object, int, null, bool version, float version, and string version are refused with `replay_input_mismatch`, `proposal` None, and `text_request_refused` before licence set membership. A metadata-valid replay whose proposal fields are a list still returns `replay_proposal_invalid`. The 429 covers list/object licence, dataset, source text, bundle, and bool version through the API, the installed CLI (`Traceback` absent, exit 1), and `AppTest` (`app.exception` empty, visible error). |
| P2-R2-O1 | Fixed for the requested paths. A 50,000-deep array under the 256 KiB limit is `replay_input_mismatch` for replay and `mistral_transport_or_response_invalid` for the mocked model envelope and model content. Audit kind is `text_request_refused`. The result and audit do not contain `RecursionError` or the nested payload. No capture. |
| P2-R2-O2 | Fixed. The authored deflate ZIP, with 38 compressed bytes XOR'd, raises `zlib.error` (`Error -3 while decompressing data: invalid distance too far back`) from `ZipFile.read`. `import_gtfs` raises only `gtfs_unreadable_archive`, writes `gtfs_import_refused`, and adds no capture. Monkeypatched `EOFError`, `lzma.LZMAError`, and `zlib.error` from `_table` take the same path. |
| P2-R2-O3 | Fixed. Source timezone present: `Europe/Brussels` and `timezone_basis=source_field`. Source absent and mapping present: same zone and `declared_mapping`. Both absent: `timezone` None and `timezone_basis=none`. The accepted row is not given a false mapping claim. |
| P2-R2-O4 | Fixed. `3 month period`, `month of December`, `3monthperiod`, and `monthofDecember` are accepted on the November notice. `Month: NotAMonth`, `Month - NotAMonth`, and `Month:NotAMonth` return `declared_month_unknown`. `Month December`, `Month: December`, `Month:December`, and `Monat Dezember` on that notice return `month_contradicts_dates`. On 2026-11-17..2027-01-05, December and January are accepted and October is refused. |

## Unchanged R2 approvals

| ID | Result |
|---|---|
| P2-R1-G1 | `desk.py` and `ui/app.py` hashes match the R2 snapshot. The multitrip selector test remains in the 429. Not reopened. |
| P2-R1-G2 | The agency clock stays. Service day `2026-11-09`, clock `35:00:00`, agency `Europe/Brussels`, every stop zone set to `Europe/London`: planned arrival `2026-11-10T10:00:00+00:00`, stored stop zone `Europe/London`, `agency_timezone` `Europe/Brussels`. Calling `gtfs_instant` directly with `Europe/London` is `2026-11-10T11:00:00+00:00`; `normalized_rows` does not do that. `Not/AZone` raises `gtfs_stop_timezone_invalid`. |
| P2-R1-G3 / O2 | `config.py` hash matches R2. The injection regressions remain in the 429. Not reopened. |
| P2-R1-G4 | `frequencies.txt` still raises `gtfs_frequency_service_not_supported`, writes `gtfs_import_refused`, and adds no capture. |
| P2-R1-O1 | Fake key `synthetic-secret\n` returns `mistral_key_invalid_format` and does not build a connection. `synthetic-secret` is absent from the audit. The 429 still includes the CR, LF, space, and non-ASCII cases. |

This review did not re-fetch https://gtfs.org/documentation/schedule/reference/#stop_timestxt. The page text is **UNKNOWN — not re-fetched this session**. The executed instants match the agency-zone rule already upheld in R2.

## Checked, not filed

- `ui/app.py` is outside the delta. `Get proposal only` calls `propose`, which now returns the static refusal instead of raising. The manual import form's `json.loads` is still in an `except (ValueError, OSError)` at `app.py:258`, and the demo replay button still calls `json.loads` on a registry path before `propose`. Those paths were not executed with a deep payload. They are not part of the five requested fixes. No open row.
- `month-long` uses a hyphen, so an unknown word in that position stays `declared_month_unknown`. That is the requested colon/dash rule. Not filed.
- The injection denylist can still refuse ordinary rail prose such as a spaced `system:` line. `config.py` did not change. The previous instruction to keep that conservative C6 bound stands. Not filed.

## Not checked

- A fresh fetch of the GTFS reference page.
- A live Mistral call, billing, or a real TLS handshake to the model host.
- A new browser session, or a second viewing of the five Phase 2 screenshots.
- A separate 71-test process. The full 429 covers those files.
- P2.8, Phase 3, and P1-R6-O1.
- Checkout `data/`.

## Ledger for the parent to copy

No new open row.

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P2-R2-S1 | Replay metadata types are checked before licence set membership. List, object, null, non-string, and bool version return audited `replay_input_mismatch`. Invalid proposal objects still return `replay_proposal_invalid`. | medium | fixed | R3 Grok: copy probe plus 429, CLI, and AppTest. |
| P2-R2-O1 | Deep JSON on replay, model envelope, and model content returns a static audited refusal. Result and audit omit `RecursionError`. | low | fixed | R3 Grok: `probe.log` `PROBE_PASS`. |
| P2-R2-O2 | Authored corrupt deflate raises `zlib.error` from the zip reader and `gtfs_unreadable_archive` from `import_gtfs`, with `gtfs_import_refused` and no capture. `EOFError` and `lzma.LZMAError` are in the same handler. | low | fixed | R3 Grok: `probe.log`. |
| P2-R2-O3 | `timezone_basis` is `source_field`, `declared_mapping`, or `none` from the evidence actually present. Missing both stores timezone None. | low | fixed | R3 Grok: `probe.log`. |
| P2-R2-O4 | Ordinary month prose is accepted. Colon or dash plus an unknown token is `declared_month_unknown`. A known month outside the notice range is `month_contradicts_dates`. | low | fixed | R3 Grok: `probe.log` and the 429. |
| P2-R1-G2 | Agency noon-minus-12 stays `2026-11-10T10:00:00+00:00` when the stop zone is `Europe/London`. Do not adopt the 11:00Z stop-zone conversion. | medium | wontfix | R3 Grok: `normalized_rows` on the copy. Clock unchanged. |
