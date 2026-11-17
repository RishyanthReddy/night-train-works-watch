**Verdict: APPROVE, 9/10.** I found no reproducible Phase 0 (P0.1–P0.8) blocker in this snapshot. All 34 files in `phase0-council-r2-snapshot.json` matched their hashes before and after my review. I wrote no checkout files: every runtime output went to `/tmp/p0r2opus`.

**Commands I ran myself**

| Command | Exit | Result |
|---|---|---|
| Snapshot SHA256 check (before and after) | 0 | 34 files, 0 mismatches |
| `uv run --offline pytest -q` | 0 | 191 passed |
| The brief's `sandbox-exec … (deny network*)`, with the six keys unset, then `uv run --offline pytest -q` | 0 | 191 passed |
| `uv run --offline python tests/phase0_acceptance.py` (from `/tmp`, isolated workspace) | 0 | details below |

In the acceptance run:
- **Before confirm:** ingest was refused with exit 1.
- **Steps 1–5:** compare gave `changed=2 added=1 unchanged=2 only_in_old=0`, and the alt mapping produced the same fields, extra and unresolved values as v1.
- **Network denied:** stdout was identical, and the loopback probe got EPERM.
- **Other formats:** JSON and XLSX sniff and ingest worked, and the merged-header XLSX was refused, then flattened, then ingested, all with the network denied.

**Round 1 findings, checked against current code with my own synthetic inputs in `/tmp`**

- **F1 (case alias):** fixed. `Data/ES/…`, `DATA/es/…`, `DATA/OUT/test-other/…` and `data/OUT/Test-Other/…` are all refused with exit 1, because of the inode check in [config.py:44](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/config.py:44).
- **F2 (slow audit, no lock):** fixed.
  - 6,000 rows now take 1.22 s and 24,000 rows take 5.05 s, which is linear.
  - Four concurrent ingests produced 30,017 events with continuous `seq` numbers, and `rejects` still reads the bundle.
- **F3 (huge numbers):** fixed. `1e5000`, `1e100000000`, a 2,000-digit value and `1e-5000` each become a `number_out_of_range` reject for that row only. The rest of the file is ingested, and the run took 0.08 s.
- **F4 (mixed comparisons):** fixed. Comparing a mapped file with an unmapped one exits 1 with `mode_mismatch`. Two different datasets exit 1 with `dataset_mismatch`.
- **F5 (unknown enum):** fixed. `bogus` becomes `other`, and the raw value is kept in `unresolved` with reason `unknown_enum`.
- **F6 (whitespace key):** fixed. A required `"   "` key is rejected with `required_missing`.
- **F7 (apostrophes):** fixed. `O'Brien` renders correctly. `[x](http://evil)` is backslash-escaped and `<b>` is HTML-escaped.
- **F8 (flatten output):** fixed. `flatten --out` is refused when the input is es data or the output is in another bundle, including case variants.
- **F9 (key typo):** fixed. `--key recordid` exits 1 and names the missing key.
- **S1 (missing time):** fixed. A missing required time is accepted with `missing_time`, the raw value and the timezone in `unresolved`. Times on both 2026 clock-change nights give `ambiguous_local_time`. A malformed time still rejects the row with `invalid_datetime`.
- **S2 (JSON absent keys):** fixed. An absent key and an explicit null now compare as `changed=1`, in both mapped and unmapped mode.
- **Exports:** an `--out` outside the bundle, or in another bundle, exits 1. Running the same export again is accepted without creating a duplicate pair.

**Limits and optional later fixes (not blockers)**
- **Deeply nested JSON:** a file with about 100,000 levels of nesting makes `sniff` print a raw `RecursionError` traceback ([table.py:191-204](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/table.py:191)). It exits 1 and writes nothing, so it fails safely, but the message is unclear.
- **Huge JSON integers:** a JSON integer over 4,300 digits stops the whole file with Python's own error message instead of a per-row reject. It also exits 1 and writes nothing.
- **Crash between capture and audit:** if the process dies after the capture folder is renamed but before the audit events are appended ([mapping.py:431-448](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:431)), a re-run reuses the capture without audit events. This is acceptable without the Phase 1 chain. I did not test it.
- **Hard links:** a file hard-linked out of `data/es` is not detected; symlinks are resolved. A user has to create the link on purpose, so I don't count it as a bypass.
- **Out of scope:** I did not review P0.9, Phase 1+ or `scripts/fetch_public.py`. I did not read anything under `data/raw`, `data/snapshots` or `data/es` in the repo.
