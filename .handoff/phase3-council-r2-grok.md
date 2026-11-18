# Phase 3 council R2 — Grok

Verdict: **APPROVE**
Score: **9/10**
Material blockers: none

Focused review of the R2 correction on branch `phase3` at `7c6919c97ad0184dcc321c16a03df90433ecd90c`. The product delta versus the R1 snapshot is exactly `docs/THREAT_MODEL.md`, `src/nightdesk/changes.py`, and `tests/test_window_membership.py`. No checkout, handoff, venv, or git write was made. No `data/` or Praha path was copied or read. No delegation, network service, live model, key, scanner, or Phase 4 action.

## Freeze

SHA-256 of every path in `.handoff/phase3-council-r2-snapshot.json`, compared with the checkout files.

- Before the copy and tests: 145 entries, 145 matches, 0 missing, 0 mismatch.
- After pytest, probes, and acceptance: 145 entries, 145 matches, 0 missing, 0 mismatch.
- R1 snapshot and R2 snapshot both have 145 paths. The only hash changes are the three files above.
- Those three files in `/tmp/phase3-council-r2-grok/copy` still match the checkout. `pyproject.toml` and `uv.lock` match too.
- Copy contained no `data/`, Praha, `__pycache__`, or `*.pyc` before the runs. After the runs, `find` of `__pycache__` and `*.pyc` under the copy printed 0.
- `git status --short` before and after is byte-identical, sha1 `a5f153059a4077b6bebbcfe14a71ec8f546a23bf`, 122 lines. Checkout `.venv` mtime stayed `1794933299`. Checkout `.handoff/phase2-acceptance-workspace.txt` and `phase3-acceptance-workspace.txt` mtimes stayed `1794982067` and `1794982069`. Acceptance pointers were created only under the copy's `.handoff`.
- `git remote -v` printed nothing. `git ls-files -- data` printed nothing. `git diff --cached --name-only -- data` printed nothing. `git diff --numstat HEAD -- uv.lock pyproject.toml` printed nothing.
- `git rev-list --count HEAD` = 8. `git rev-list --objects HEAD -- data` = 0. `git rev-list --objects --branches -- data` = 0. `git rev-list --count --all` = 310.
- `git rev-list --objects --all -- data` lists pathnames under `data/snapshots/de`, `data/snapshots/it/2026-11-14/infolavori.txt`, and `data/snapshots/nl/2026-11-14/railinfo.json`. `git log --all --source --pretty=format:'%S' -- data` lists only `refs/t3/orchestration-v2/checkpoints/...`. Non-`refs/t3` sources: 0. Blob contents were not read.

`git push -h` on this machine says `--all` pushes all branches, `--branches` is an alias of `--all`, and `--mirror` mirrors all refs. A future push of the reviewed branch is the allowed scope. `--all` would publish every local branch. `--mirror` would also publish the checkpoint refs that still name historical data paths. No push was run.

## How the checks ran

Isolated copy: `/tmp/phase3-council-r2-grok/copy` (`src`, `mappings`, `tests`, `docs/THREAT_MODEL.md`, `pyproject.toml`, `uv.lock`). Checkout `.venv` was a symlink. `.handoff` existed only inside that copy.

Ordinary Python, not `python -I`: `sys.flags.isolated == 0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=/tmp/phase3-council-r2-grok/copy/src`. `nightdesk.__file__` and `nightdesk.changes.__file__` resolved under that copy, including through `.venv/bin/python`. The six credential variables were unset. Sandbox profile `/tmp/phase3-council-r2-grok/sb.sb` denies network and denies writes under the checkout. A connect to `1.1.1.1:443` returned errno 1. A checkout write returned errno 1 and left no file.

Pytest, whole process sandboxed, `uv run --offline --no-sync`:

```
sandbox-exec -f /tmp/phase3-council-r2-grok/sb.sb \
  env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/phase3-council-r2-grok/copy/src \
  uv run --offline --no-sync pytest -q -rs -p no:cacheprovider --basetemp /tmp/phase3-council-r2-grok/pytest
```

Result: **475 passed, 1 skipped, 46.44s, exit 0**. The skip is `tests/test_window_membership.py:108`: `local restricted practice captures absent; synthetic cases remain mandatory`. Parent `.handoff/phase3-r2-final-tests.log` says `476 passed in 48.66s` and `EXIT: 0`. This review did not run that local capture and did not open `data/snapshots`.

Independent probes: `/tmp/phase3-council-r2-grok/probes.py`, same sandbox and environment, exit 0. Log: 77 `PASS` lines, 0 `FAIL`, `FAILURES 0`.

Acceptance ran from the copy with the same `PYTHONPATH`, bytecode disabled, and the six variables unset. The driver was not placed in a second sandbox, because these scripts call `sandbox-exec` themselves and macOS refuses a nested sandbox. Each `nightdesk` command is inside the script's own `deny network*` child. Phase 0 also compares an ordinary pass with a denied pass.

| Script | Exit | Observed |
|---|---|---|
| `tests/phase0_acceptance.py` | 0 | Network-denial probe `exit 0 errno 1`. Ordinary and denied stdout matched. Merged-header refusal, flatten, ingest passed. |
| `tests/phase2_acceptance.py` | 0 | `PHASE2_ACCEPTANCE_PASS; no live model request`. Replay refusals exit 1. GTFS import `accepted=22 rejected=0`. Demo check: 27 hashed assets. |
| `tests/phase3_acceptance.py` | 0 | Nine `[network denied]` commands. Merged XLSX refused (`A1:M1`). NDA propose exit 1, `bundle_external_processing_disabled`. Tail-cut verify exit 1, `external_seal_or_count_mismatch`. Unsealed verify exit 0; limits say source truth is not proved. Demo check: 27 hashed assets. `PHASE3_ACCEPTANCE_PASS`. |

## Corrections

### S1 — canonical and raw dates

`_validity_conflicts` in `src/nightdesk/changes.py` (lines 98–113) compares the projected raw envelope dates with `date_start` / `date_end`, and rejects an individual period whose `vonDatum` is before the canonical start or whose `bisDatum` is after the canonical end. A conflict becomes `membership_unknown` / `canonical_raw_validity_conflict` (lines 143–144) after the parsed bounds are stored. Evidence retains canonical dates, parsed bounds, and source. The row stays in `added` or `removed` when the comparison gate passes (line 227).

Probes, synthetic only:

- Old canonical end 2026-11-20 against raw end 2026-11-18 05:00: conflict, kept in `removed`, audit reason matches.
- New canonical start 2026-11-30 against raw start 2027-03-01, explicit 2016 h: conflict, kept in `added`. The raw start is past the old edge, so the old override would have called it entering.
- Matching old clock 2026-11-18 05:00 Europe/Berlin expires at capture 2026-11-18 04:00:01Z and is not removed. The same clock at 03:00Z, and at the equal instant 04:00:00Z, stays in `removed`.
- Date-only end `2026-11-18` during that calendar day stays source membership.
- A later period on the same canonical day blocks expiry and stays in `removed`.
- A period `bisDatum` of 2026-11-20 against canonical end 2026-11-18 is a conflict and stays in `removed`.
- Matching new start at the previous edge enters and is not added. One second earlier is added.
- Real JSON confirm/ingest on 2026-11-18, four cases, no revision mock: old conflict and new conflict accepted with zero rejects, classified `canonical_raw_validity_conflict`, and kept in the R2 list. Matching old capture expired. Matching new capture entered. Licence on the evidence was `synthetic`.

### O1 — unknown notes keep R2 presence

Line 227 drops a one-sided id only for `expired_out_of_window` and `entering_window`. `membership_unknown` stays in `removed` or `added` when the gate passes, and stays out of those lists when the capture is incomplete.

Probes for missing timezone, empty periods, a malformed period, an invalid clock, the Europe/Berlin fold `2026-10-25 02:30`, and the gap `2026-03-29 02:30`, on both sides: complete comparisons keep the id and record `validity_bounds_unresolved`; partial comparisons record the same reason with empty `added`/`removed` and status `comparison_unavailable`.

### O2 — explicit hours fill only an absent policy

`_window_declarations` collects the direct filter and role `zeitraum` values from both captures (lines 116–122). Differing declarations, or an explicit hour value that does not equal a retained `ROLLIEREND` count, return `rolling_window_conflict` with the declared windows and the selected hours (lines 149–166). Equal policy keeps the captured window and records `window_basis=capture_filter` when a row enters.

Probes:

- Declared 2016 h plus explicit 100 h, start 2026-11-25: conflict, id stays in `added`.
- Equal 2016 h and a start past the edge: `entering_window`, basis `capture_filter`, not added.
- Equal 2016 h and a start inside the window: `only_in_selected_new`, in `added`.
- No declaration plus explicit 100 h: a start past that edge enters with basis `explicit_comparison_selection`; a start one second inside it stays added.
- A role window of 2016 h is not replaced by 100 h. Two role windows that disagree conflict even with no explicit hours, and the far row stays added.
- A `FIXED` declaration is not replaced. A declaration present only on the new capture, with explicit 100 h, is `filter_mismatch` at the comparison and `rolling_window_conflict` on the row. `added` is empty. It is not entering.
- Filter mismatch still describes an old expiry and blocks entering.
- Explicit `0`, `-1`, `True`, `"2016"`, and NaN do not enter. A capture that does not advance does not enter. Those rows stay in `added`.

### G1 — checkpoint refs

`docs/THREAT_MODEL.md` lines 30–33 say the intended product branch excludes restricted inputs, that local checkpoint refs can retain historical data paths, and that those refs are not to be pushed. The path check above matches that statement. HEAD, the index, and every local branch reach no `data/` object. The checkpoint refs do. This remains the accepted low **P3-R1-G1**. No ref was deleted.

## Regression

The 475 passed tests include the new intake, dossier, export, and audit coverage in `tests/test_window_membership.py`. Phase 0, 2, and 3 CLI acceptance exited 0 on the copy. `changes.py` still excludes only the two proved classifications, and filter mismatch still prevents an entering claim.

Preserved, with no new evidence against them: **P1-R6-O1** and **P2-R3-O1**.

P3.1–P3.6 were accepted in R1. This round rechecked them through the full suite and the Phase 3 CLI path (swap sniff/ingest, German text import, NDA refusal, tail-cut seal failure, unsealed limits text, demo allowlist). Aikido remains local preparation. No account, connection, or scan report was created. No remote is configured.

## Not checked

- Raw German captures and the parent's 776 expired / 456 entering counts. The copy skipped that test on purpose.
- Screenshot frames and any browser DOM. This review opened no browser and makes no visual claim.
- Live Mistral, Aikido, and any other network service.
- Blob contents of the checkpoint data paths. Only object pathnames and ref names were read.

## Limits that are not findings

- The acceptance driver processes were outside the outer sandbox. Their `nightdesk` children were sandboxed by the scripts. Pytest and the probes were sandboxed for the whole process.
- An external seal proves a stored hash and count. The unsealed live verify says source truth is not proved.
- A non-entering row with an equal explicit policy is recorded as ordinary source membership. The entering row records `window_basis=capture_filter`.
