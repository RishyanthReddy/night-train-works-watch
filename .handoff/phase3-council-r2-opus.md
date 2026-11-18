# Phase3 council R2 — Opus focused review

Verdict: **APPROVE**. Score **9/10**.

Scope: the 3-file delta against the R1 freeze (`src/nightdesk/changes.py`, `tests/test_window_membership.py`, `docs/THREAT_MODEL.md`), the S1/O1/O2/G1 corrections, and a no-regression check. I made no writes to the checkout, handoff, venv or Git. I did not read data/ or Praha, used no network, model, key or scanner, and delegated nothing.

## Material findings
None.

## Corrections verified independently
Probes are in `/tmp/opus-p3r2/probes/test_probe_r2.py`: 20 synthetic probes, each asserting the conservative outcome, 20 passed, exit 0. They are separate from the parent's tests.

- **S1** (`changes.py:98-113`, used at 136/143-144). Both Sol repros return `membership_unknown` / `canonical_raw_validity_conflict` and stay in the R2 lists:
  - Repro A: raw end Nov18 05:00, canonical end Nov20. The row stays in `removed`.
  - Repro B: raw start Mar1, canonical start Nov30, with 2016 h. The row stays in `added`.
  - Evidence keeps `canonical_validity`, parsed `validity_bounds` and `source`.
  - Consistent projections still expire on the precise raw clock: 05:00 Berlin is before 05:24Z, so the row is expired. With a 07:00 end the row is `only_in_selected_old` and listed in removed.
  - Periods outside the canonical range conflict, on both the end and the start side.
  - A raw end with an offset is projected into the declared zone (23:30Z becomes Nov19 Berlin) and conflicts.
  - A raw end at exactly midnight projects to the next day and conflicts. This is conservative.
  - Raw `gueltigkeiten` without `zeitraum` stays unknown and retained.
  - Canonical-only rows still expire.
- **O1** (`changes.py:227`). The R1 repros A and A2 (no zone) now give `removed`/`added` of 1, each with an unknown annotation. With incomplete captures both lists stay empty and status is `comparison_unavailable`. Only `expired_out_of_window` and `entering_window` are excluded. No classification names publication or cancellation.
- **O2** (`changes.py:149-169`):
  - A shorter override (100 h against a declared 2016 h, the R1 B2 repro) and a longer one (2016 h against 100 h) both give `rolling_window_conflict` and the row stays in `added`. Evidence records `declared_windows` and `selected_window_hours`.
  - An equal override (2016.0 against 2016) still classifies the row as entering.
  - A bool override with no declaration resolves to `rolling_window_unresolved`, with hours recorded as `"invalid"`.
  - A top-level window that conflicts with a role-level window in the same capture gives a conflict.
  - A declaration only on the new side gives `filter_mismatch`, the row is not entered and `added` is empty.
- **G1** (`THREAT_MODEL.md:30-33`). The doc now limits the claim to the intended branch and says local checkpoint refs can hold historical data paths. It no longer claims that all refs lack data. Local `git push -h` (git 2.54.0) shows `--all` = "push all branches" and `--mirror` = "mirror all refs", which matches the brief's correction. I deleted no refs and pushed nothing.

## Low residuals (no change required)
- L1: in `_validity_conflicts`, periods are compared by raw `vonDatum`/`bisDatum` dates, not zone-projected instants. If a period clock carries an offset that crosses midnight in the declared zone, the date check could miss it. The envelope projection still applies, and every period bound is still required to end before the capture for expiry. I found no non-conservative path.
- L2: a work with `timezone=None` whose raw fields all carry offsets can still be classified as expired, using the offset's own date. This is consistent with the evidence it states.
- The accepted lows P1-R6-O1 and P2-R3-O1 are unchanged. My R1 lows L1 and L3 are unchanged. My R1 low L2 is now covered by the S1 check.

## Commands, exits, evidence
- Freeze before: `python3 /tmp/opus-p3r2/hash.py` against `phase3-council-r2-snapshot.json`: 145 paths, 0 mismatches, exit 0. R1→R2 snapshot diff shows exactly the 3 changed paths and none removed. My R1 copy of those 3 files matched the R1 snapshot hashes, so I used it as the diff base.
- Checkout: HEAD `7c6919c97ad0184dcc321c16a03df90433ecd90c`, branch phase3, 0 staged files. `git status --short` gave 118 lines; its sha256 was identical after my runs.
- Copy: rsync of src, mappings, tests, pyproject.toml and uv.lock, plus docs/THREAT_MODEL.md, into `/tmp/opus-p3r2/copy`. The copy has 0 `__pycache__` directories before and after. `.venv` is a symlink to the checkout venv.
- Sandbox `/tmp/opus-p3r2/sb.sb` denies remote outbound, checkout writes and reads of data/. Probe inside it: network errno 1, checkout write errno 1, data/ read errno 1, `nightdesk.__file__` resolves to the copy, 0 of the 6 keys set. All runs used PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=copy/src, ordinary Python (not -I), `-p no:cacheprovider` and basetemp under /tmp.
- Full suite (sandboxed): **475 passed, 1 skipped in 49.03s, EXIT 0** (`/tmp/opus-p3r2/full-tests.log`). The one skip is `test_window_membership.py:108`, "local restricted practice captures absent". 475+1 equals the parent's 476.
- `uv run --offline --no-sync` (sandboxed, with UV cache and project env pointed at the copy) on the window suite plus all `test_phase3_*` suites: 46 passed, 1 skipped, EXIT 0.
- Acceptance: phase0 EXIT 0 (PASS), phase2 EXIT 0 (PHASE2_ACCEPTANCE_PASS), phase3 EXIT 0 (PHASE3_ACCEPTANCE_PASS). Phase3 ran 9 `[network denied]` CLI commands, including `demo check passed`. Logs are `/tmp/opus-p3r2/phase{0,2,3}-acceptance.log`. I ran the scripts outside my outer sandbox to avoid the macOS nested-sandbox refusal, with keys unset and PYTHONPATH and TMPDIR in /tmp. Each script's own `deny network*` child sandbox covered its CLI subprocesses. Their `.handoff` pointers were written only into `copy/.handoff`. Limit: the acceptance parent Python processes themselves ran without my outer denial.
- After: 145 paths, 0 mismatches, exit 0. Git status hash is the same, HEAD is the same, the index is empty, and the checkout `.handoff` pointer mtimes are unchanged (07:07:47 and 07:07:49).

## Not checked / limits
- I did not reproduce the German aggregate counts (776 expired, 456 entering, 199 long-validity). I read only the parent log counts in `phase3-german-recheck.log` and never touched the restricted data. Their correctness on that data is UNKNOWN - not checked.
- No visual claim and no browser DOM re-run. No Aikido, remote, push or Phase4 work.
