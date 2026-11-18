# Phase 2 council R3 — Opus focused read-only review

**Verdict: APPROVED. Score: 9/10.**

All five R2 items (S1, O1, O2, O3, O4) are fixed in the five-file delta. I found no material regression. One low, nonblocking residual is in the same class as O2: a corrupted **bzip2** ZIP member raises a raw `OSError("Invalid data stream")`. The refusal is still audited and nothing is imported. One behaviour note on O4 follows; it matches the declared design. No new feature is requested.

## Freeze and isolation

- Checkout `/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a`, branch `phase2`, HEAD `1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e` before and after.
- `phase2-council-r3-snapshot.json`: 128 entries, 0 mismatches in the checkout before and after, and 0 in my copy before and after all runs.
- R3 vs R2 snapshot: exactly 5 entries differ, `adapters/gtfs.py`, `intake/text.py`, `llm/cache.py`, `llm/client.py` and `tests/test_phase2_council.py`. This equals `phase2-r3-delta.json`.
- Copy: `REVIEW=/tmp/nightdesk-p2-r3-opus-MMBK`, made with rsync excluding data, .git, .venv, .handoff, Praha, __pycache__ and .pytest_cache. The checkout `.venv` is symlinked read-only, and an empty `.handoff` exists in the copy only. `nightdesk.__file__` resolves to `REVIEW/copy/src`.
- Wrapper `REVIEW/run.sh`: `env -u` for the six keys, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=copy/src`, `PYTEST_ADDOPTS="-p no:cacheprovider --basetemp=REVIEW/pytest-*"`, `sandbox-exec '(version 1)(allow default)(deny network*)'`. It runs ordinary Python, not `-I`.
- Both acceptance scripts resolve `REPO` to the copy. The Phase 2 `main` wrote its pointer to `copy/.handoff` only. Phase 0 used its default isolated temp workspace. No `data/out/test-formats-*` directory appeared in the checkout.
- I made no checkout, data or .handoff writes, no git mutation, no delegation, no live Mistral call, used no real keys and spent nothing. During the review, files under checkout `.handoff/` (state/next/sources/review, the new `phase2-council-r3-tasks.json`), `AGENTS.md` and `.git/objects` got newer mtimes. Those writes came from the parent or another process, not this review. The 128-file freeze still matched.

## Commands and exits

| Command (via `run.sh`, cwd copy) | Exit | Result |
|---|---|---|
| `freeze.py` checkout and copy, before and after | 0 | 128/128 match each time; R2→R3 diff = the 5 delta files |
| `.venv/bin/python -m pytest -q tests` | 0 | **429 passed in 43.03s** (`full.log`) |
| `.venv/bin/python -m pytest -q -s -rA probe_r3` | 1 | 31 passed, 1 failed. The failure is my over-strict probe assertion at depth 200 (see S1), not a defect (`probe.log`) |
| `.venv/bin/python tests/phase2_acceptance.py` | 0 | `PHASE2_ACCEPTANCE_PASS; no live model request`, GTFS accepted=22 rejected=0 (`phase2-acceptance.log`) |
| `.venv/bin/python tests/phase0_acceptance.py` | 0 | `PASS: real JSON/XLSX sniff and ingest ... network denied` (`phase0-acceptance.log`) |

## Per-item verification

**P2-R2-S1 (replay metadata typing): fixed.** At `cache.py:44-48`, the body is checked to be a dict, `type(version) is int` and `== 1`, `source_text`, `dataset` and `licence` are checked to be strings, and `bundle`, when present, must be a string. All of this runs before the licence set membership at line 55. My probes beyond the new tests all return `replay_input_mismatch` with a `text_request_refused` event: version `1.0`, `"1"` and `2`, a top-level list, licence `null`, bundle `null`, and a non-UTF-8 file. `proposal: null` still returns `replay_proposal_invalid`, and a valid replay is still accepted. The new test covers API, actual CLI (exit 1, no Traceback, code on stdout) and production `render_text_intake` AppTest (no exception, visible error, refusal audited, no capture) for 7 shapes. It passed in my full run.

**P2-R2-O1 (deep JSON): fixed.** `cache.py:42` maps RecursionError to `replay_input_mismatch`. `client.py:56` maps it to the static transport code, and `client.py:88` adds a RecursionError/TypeError fallback with the static `text_input_or_response_invalid`. Besides the 50k-depth tests, I probed proposals nested *under* the json.loads limit, at depths 200, 500, 900 and 990:
- Replay at depth ≥500 gives `replay_proposal_invalid`, which is pydantic's recursion guard surfacing as a ValidationError. Depth 200 passes the schema and gets the ordinary audited `field_quote_missing_or_extra` rejection (`text_proposal_checked`, accepted false). My probe wrongly expected `text_request_refused` there.
- Model content at depths 500 to 990 gives `proposal_schema_invalid`, audited, with no capture and no exception.

**P2-R2-O2 (corrupt deflate): fixed.** At `gtfs.py:127`, `zlib.error`, `EOFError` and `lzma.LZMAError` are caught and become `gtfs_unreadable_archive`. My probes on deflate with flipped bytes, a zeroed second half of the stream, and a CRC mismatch all give `gtfs_unreadable_archive` with `gtfs_import_refused` audited and no capture. The actual CLI exits 1 with no Traceback.

**P2-R2-O3 (timezone basis): fixed.** At `text.py:110`, the basis is `source_field`, `declared_mapping` or `none`, matching the evidence file. Probes: proposal timezone `''` with a mapping timezone gives `declared_mapping` and Europe/Brussels. A source timezone with no mapping timezone gives `source_field`. The new test covers the case with neither (basis `none`, timezone None).

**P2-R2-O4 (month prose): fixed.** At `text.py:65-69`, an unknown word is refused only after a `:` or `-` separator. The probe matrix: `Month:December`, `Monat: Dezember` and `month\tDecember` give `month_contradicts_dates`. `MONTH - foo` and `Month:\nfoo` give `declared_month_unknown`. `Monat November`, `Month: November`, `a month of may` and `months: foo` are accepted.

## Findings

### P2-R3-O1 — low, nonblocking: corrupted bzip2 member escapes normalization as raw OSError

- **Repro:** a ZIP_BZIP2 GTFS archive with 38 bytes of the first member flipped. `import_gtfs` raises `OSError: Invalid data stream`, from `bz2` inside the `_table` read at `gtfs.py:44`. The `except` at `gtfs.py:127` does not list OSError. `import_gtfs` still catches OSError, so `gtfs_import_refused` is audited and nothing is captured. The CLI exits 1 with `error: Invalid data stream`, and no Traceback.
- **Impact:** this fails closed. The message is a fixed stdlib library string, not source or secret text. It is only an inconsistency with the static `gtfs_unreadable_archive` code that O2/O4 established. No wrong row or partial import results.
- **Optional fix:** add `OSError` to the tuple at `gtfs.py:127` (or catch it around the archive reads only), plus a one-line bzip2 test. Approval does not depend on this.

### Note (not a finding): known month words in ordinary prose are still checked

`the month may vary` with November dates returns `month_contradicts_dates`, because `may` is in `TEXT_MONTHS`. This is the declared behaviour ("known unseparated month still checked against full range"). It fails closed with a visible reason, so I do not file it.

### Informational, pre-existing, unchanged by this delta

On the Mistral path, `cache.save` runs before `validate_proposal`. A deep or invalid model proposal is therefore cached with a `text_cached` event before being rejected. It is audited, and there is no capture. Not in R3 scope.

## G2 / scope

I did not reopen G2. Agency-timezone conversion is unchanged in this delta (`gtfs.py:31-36`), and no stop-zone conversion was added. The delta adds no UI, config, dependency, fixture or mapping changes, and I found no Phase 3, P2.8 or P1 scope expansion.

## Artifacts

`REVIEW/run.sh`, `REVIEW/freeze.py`, `REVIEW/full.log`, `REVIEW/probe.log`, `REVIEW/copy/probe_r3/test_probe_r3.py`, `REVIEW/phase2-acceptance.log`, `REVIEW/phase0-acceptance.log`.
