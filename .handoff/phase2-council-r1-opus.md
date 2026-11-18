# Phase2 council R1 — Opus review

Reviewer: Opus (Kiro), read-only. Branch phase2, HEAD 1ff48d320d5256e0a4b292ce1f1c64eb91b9db0e.
Scope: Phase2 P2.1–P2.7 delta from HEAD, including untracked product files. P2.8 and Phase3 excluded. P1-R6-O1 not re-opened.

**Verdict: CHANGES REQUESTED. Score 7.5/10.** One high finding, a secret leak into the append-only audit log (P2-R1-O1), blocks approval. The other findings are low or medium and do not block.

## Freeze
- Before review: `python3 /tmp/p2r1_verify.py <checkout> .handoff/phase2-council-r1-snapshot.json` gave 127 entries and 0 mismatches. The same check on the /tmp copy also gave 0 mismatches.
- After review: 127 entries, 0 mismatches. HEAD is unchanged.
- Snapshot coverage gap: the snapshot does not list `scripts/fetch_public.py`, `AGENTS.md`, `CLAUDE.md` or `KICKOFF.md`, although all four are untracked. `scripts/` is outside the Phase2 allowed paths, so I did not review that file.
- **Disclosure: I wrote to the checkout by accident.** My first probe runs used `python -I`. That flag ignores PYTHONPATH and PYTHONDONTWRITEBYTECODE, so the probes imported the checkout's editable install and wrote 5 gitignored bytecode files: `src/nightdesk/{llm/__pycache__/{__init__,cache,client},adapters/__pycache__/gtfs,intake/__pycache__/text}.cpython-312.pyc`. File birth times show all 5 were created by my runs (03:08 on 2026-11-18). I deleted exactly those 5 files and the two `__pycache__` directories that I had created. The modification times of the `src/nightdesk/llm`, `src/nightdesk/adapters` and `src/nightdesk/intake/__pycache__` directories changed. No tracked or snapshot file changed, and the hashes still match. I reran every probe without `-I`, against the copy's `src`.

## Environment
- Copy: `/tmp/p2r1-opus-2151`, made with rsync excluding data, .git, .venv, .handoff and Praha. `.venv` is a symlink to the checkout's.
- Wrapper `/tmp/p2r1-run.sh` unsets the six credential variables, sets PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=copy/src and UV_OFFLINE=1, then runs under `sandbox-exec '(version 1)(allow default)(deny network*)'`.
- Sanity check: no credential variables were present, and a socket connect to 1.1.1.1:443 failed with `[Errno 1] Operation not permitted`. Exit 0.
- I did not read checkout `data/`, make live model requests, download anything or delegate.

## Commands run
| Command | Result |
|---|---|
| wrapper + `PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/p2r1-bt-full' uv run --offline --no-sync pytest -q` | 381 passed in 36.34s, exit 0 |
| wrapper `.venv/bin/python tests/phase2_acceptance.py` | Every check passed: the three dossier unknown cases, demo check of 27 assets, two identical replay outputs, three poison refusals with exit 1, GTFS 22 accepted / 0 rejected, and the final `PHASE2_ACCEPTANCE_PASS` line. The script then exited 1 on its last line, which writes `REPO/.handoff/phase2-acceptance-workspace.txt`; my copy has no `.handoff`. This failure comes from my environment, not from a product defect. |
| wrapper `.venv/bin/python tests/phase0_acceptance.py` | exit 0, PASS for JSON/XLSX/flatten |
| `/tmp/p2r1-probe/probe_text.py` | exit 0, results below |
| `/tmp/p2r1-probe/probe_key.py` | exit 0, reproduces O1 |
| `/tmp/p2r1-probe/probe_gtfs2.py` | exit 0, results below |
| `/tmp/p2r1-probe/probe_alias.py` | exit 0 |
| `/tmp/p2r1-probe/probe_demo.py` | exit 0 |

I also viewed two of the parent's screenshots, `.handoff/phase2-app-refusal.png` and `phase2-app-poison.png`. They show `prediction_not_validated` with the fix text and no number, `unknown: different_boundary_points` under border-v2, and `Proposal refused: text_addresses_model`. I did not view the other three screenshots.

## Findings

### P2-R1-O1 — HIGH, blocking: a malformed MISTRAL_API_KEY is written verbatim into the audit log and the UI/CLI output
- **Where:** [client.py:41](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/llm/client.py:41), where the header is built, and [client.py:78-81](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/llm/client.py:78), where `reason=str(exc)` is audited.
- **Mechanism:** If the key contains a CR/LF or another illegal header character, `http.client.putheader` raises `ValueError("Invalid header value b'Bearer <KEY>\n'")`. `_send` catches only OSError, KeyError, IndexError, TypeError and JSONDecodeError, so this ValueError escapes. `propose` then records `str(exc)` in the hash-chained `text_request_refused` event, returns it in `reasons`, and the CLI prints it (UI: `st.json`/`st.error`). This path requires that the user ran `nightdesk consent --allow mistral`, that the mapping was confirmed, and that the dataset flag is true.
- **Repro** (synthetic fake key, network denied): `/tmp/p2r1-probe/probe_key.py` printed `returned reasons: ["Invalid header value b'Bearer SYNTHETIC-FAKE-KEY-123\\n'"]` and `fake key in audit log: True`.
- **Impact:** This breaks KICKOFF §0 rule 4 and §8 ("Secret values never appear in … exception text or request logs"). The audit log is append-only and hash-chained, so the leaked key cannot be removed without breaking verification. A secret value with a trailing newline is a plausible real case.
- **Fix:**
  1. Before building the header, check that the key is non-empty and contains only visible ASCII (for example `re.fullmatch(r'[\x21-\x7e]+', key)`). Otherwise raise the static `mistral_key_invalid_format`.
  2. Inside `_send`, also catch `ValueError` and `http.client.HTTPException` and map them to the static `mistral_transport_or_response_invalid`.
  3. In `propose`, audit and return only reason codes from a known allowlist, the same pattern as `text.py:82-84`.
  4. Add a regression test that sets a key with a trailing `\n` and asserts the key is absent from the audit events and from the returned reasons.

### P2-R1-O2 — MEDIUM, nonblocking: the C6 injection denylist is bypassed by trivial variants
- **Where:** [text.py:21-26](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/text.py:21) and the `TEXT_INJECTION_MARKERS` list in [config.py:141](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/config.py:141).
- **Repro** (`probe_text.py` T2): each of these was appended to the valid notice and every one passed with no reasons:
  - `ignore  previous instructions` (double space)
  - `ignore\u200b previous instructions` (zero-width space)
  - `ignore\nprevious instructions`
  - `Ignore the previous instructions`
  - `disregard prior instructions`
  - `SYSTEM :`
  - `<|im_start|>system`

  Text that passes this guard is sent to Mistral once consent is given.
- **Impact:** Limited. The structural defences hold: model output needs a field quote and must pass the typed gates, it is never executed, and proposals do not import a record. The P2.6 fixture is still rejected. But C6 says text that addresses the model rejects the record, and the gate misses the cheapest variants.
- **Fix:**
  - After NFKC+casefold, remove Unicode format characters (category Cf) and collapse whitespace runs to a single space before searching for markers.
  - Add generic markers: `<|`, `previous instructions`, `prior instructions`, and a role word followed by an optional space and a colon at line start.
  - Keep stating in the docs that this is a denylist, not proof of safety.

### P2-R1-O3 — LOW-MEDIUM (performance), nonblocking: the GTFS adapter has no bound on output rows and duplicates large evidence in every row
- **Where:** [gtfs.py:158-177](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:158).
- **Mechanism:** Output size is trips × service days × stops. The existing limits cover only archive bytes, hours and total service days. Every row also copies `agency`, `calendar`, `trip`, `route` and `stop`.
- **Repro** (`probe_gtfs2.py`, synthetic, no date or trip filter):
  - A 2.2 KB zip with 20 trips × 20 stops × 60 days gave 24,000 rows. `normalized_rows` took 0.81s, the full `import_gtfs` took 8.1s, and rows.json was 33 MB.
  - A 3.3 KB zip with 40 × 20 × 120 gave 96,000 rows, and `normalized_rows` alone took 3.36s.
  - The scaling is linear, but a 128 MB national feed without a filter would produce millions of rows and several GB.
- **Impact:** A local denial of service or a stalled import during the on-day swap. This is not a correctness problem. The saved CC0 fixture is small, and `--service-date` and `--trip-id` already exist as filters.
- **Fix:** Add `MAX_GTFS_OUTPUT_ROWS` in config and refuse with a static code that tells the user to add `--service-date`/`--trip-id`. Optionally, store per-trip and per-calendar evidence once and reference it from each row.

### P2-R1-O4 — LOW: GTFS archive and CSV errors escape the audited refusal path
- **Where:** [gtfs.py:111-124](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:111) and [gtfs.py:186](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/adapters/gtfs.py:186).
- **Repro:**
  - G1: a stops field over 131,072 characters raises `_csv.Error`.
  - G2: an encrypted-flag zip raises `RuntimeError`.
  - In both cases `import_gtfs` records no `gtfs_import_refused` event, and the CLI's `main` (which catches ValueError, OSError and LookupError) prints a traceback.
  - Unsupported compression would likely raise NotImplementedError on the same path, but I did not test it.
- **Fix:** Catch `csv.Error`, `RuntimeError` and `NotImplementedError` in that try block and map them to `gtfs_unreadable_archive`.

### P2-R1-O5 — LOW (provenance): text imports through the CLI or UI are always labelled `proposed_by: manual`
- **Where:** [text.py:87](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/text.py:87) (default mode), [cli.py `_cmd_text`](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/cli.py:233) (no mode option) and the UI form (calls `submit_text` without a mode).
- **Mechanism:** In the UI, fields copied from a Mistral or replay proposal into the form are stored as `manual`. The import audit event records `mode: 'manual'`.
- **Repro:** `probe_text.py` T6 printed `proposed_by manual`. Through the UI the same follows by code reading; I did not test it there.
- **Impact:** The record does not say a model drafted it. A human did review and submit it, so this is not a gate bypass.
- **Fix:** Carry the provider of the last proposal into `submit_text` when the submitted fields equal the proposed fields. Alternatively, record `drafted_by` in `extra` and the audit event.

### P2-R1-O6 — LOW: a text notice without a `timezone` field ignores the mapping's declared timezone
- **Where:** [text.py:75](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/text.py:75) and [text.py:104-113](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/text.py:104).
- **Repro:** `probe_text.py` T5/T5b. The proposal without `timezone` was accepted, and the stored work has clock 23:00:00 and timezone None, even though the mapping declares Europe/Brussels.
- **Impact:** Conservative. The matcher reaches `timezone_unknown`, so no positive result is produced, but usable data stays unresolved.
- **Fix:** Default to `mapping.timezone` when the field is absent, or reject with a visible `timezone_required_for_clock` code.

### P2-R1-O7 — LOW: the month-declaration check is narrow and falsely rejects ranges that span months
- **Where:** [text.py:62-66](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/text.py:62).
- **Repro** (T3):
  - A work from 2026-11-17 to 2027-01-05 declared `Month: December` is rejected with `month_contradicts_dates`, although December lies inside the range.
  - `Month December` (no colon) and `Month - December` are not checked at all.
- **Fix:** Test whether the declared month falls in any month from date_start to date_end. Keep the documented scope ("declared `month:` form only").

## Verified without findings
- **Model policy** (mocked transport, `probe_text.py` T7/T8):
  - No consent gives `bundle_external_processing_disabled` with 0 connections.
  - Consent without mapping confirmation gives `mapping_confirmation_required` with 0 connections.
  - With all gates passed, exactly one connection goes to `api.mistral.ai`.
  - After revocation, requests are refused again.
  - Injected text is refused before sending.
  - The es cache lives under `data/out/es/llm/cache`. The practice bundle cannot replay the es cache ("input belongs to another bundle"). The es bundle cannot replay an external file (`nda_replay_requires_own_bundle_cache`).
  - A key in valid format never appeared in the audit log or any file.
  - Not checked: TLS verification and redirects. By code reading, `http.client` with the default context verifies certificates and never follows redirects.
- **Aliases** (`probe_alias.py`):
  - Matching is exact after case and whitespace normalisation. An ambiguous name returns both candidates and no id. An NFD diacritic stays unresolved.
  - Tables are isolated per bundle. A second table requires an explicit selection. A tampered table fails with `alias_table_hash_mismatch`. `reviewed: 'yes'` is refused.
- **Demo** (`probe_demo.py`): a tampered asset gives `demo_asset_hash_mismatch`. The es bundle is refused. A capture not in the manifest is refused. A capture in the manifest passes.
- **GTFS time:**
  - `25:30:00` on 2026-11-17 gives 2026-11-18 00:30Z.
  - On the DST days, 01:30 on 2026-10-25 and 02:30 on 2026-03-29 both give 00:30Z, which matches the GTFS rule (local noon minus 12 hours, plus elapsed time).
  - The adapter sets scheduled-only, `path_unresolved` and `line=None`. Trip variants stay separate (runs grouping key now includes `kind` and `trip_id`).
- **Dates and identity** (code read, plus the test suite and acceptance run): uncertain identity gives `identity_uncertain` (time_unknown). A boundary leg with several operating dates gives `boundary_service_date_binding_unknown`. The clock-change, partial-capture and different-point cases stay unknown with their reasons.
- **Delay requests** (`estimate.py`): always a Refusal with no number, also included in the dossier and markdown export.
- **Core code:** no source-specific column names were added to the core diff.

## Not checked
- A live Mistral request, billing or the real TLS handshake.
- A real (non-fixture) GTFS feed.
- The browser UI: I ran no browser session and viewed only two of the five screenshots.
- `scripts/fetch_public.py`, which is outside the snapshot and the Phase2 paths.
- P2.8 and Phase3.

## Score: 7.5/10. CHANGES REQUESTED for O1, with a one-pass fix and a regression test. O2–O7 are recommended but not blocking.
