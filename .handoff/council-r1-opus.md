**Verdict: CHANGES REQUESTED. Score 6.5/10.**

The six Phase 0 acceptance steps pass through the real CLI, both normally and with the OS network denied. Four reproducible defects remain: a case-sensitivity bypass of the bundle/NDA input guard, a quadratic-time audit writer, one numeric cell that aborts or hangs a whole ingest, and comparisons that report "compared" across mapped and unmapped tables. I did not modify any file; all snapshot hashes still match afterwards.

## Commands run (from the repo, outputs in /tmp/ndrev)
| Command | Exit | Result |
|---|---|---|
| Snapshot SHA256 check against `phase0-council-r1-snapshot.json` (before and after) | 0 | no mismatch |
| `uv run --offline pytest -q` | 0 | 171 passed |
| The brief's `sandbox-exec … deny network*` + `env -u` (six keys) `uv run --offline pytest -q -p no:cacheprovider` | 0 | 171 passed |
| `uv run --offline python tests/phase0_acceptance.py` | 0 | see below |

Acceptance results: an ingest before confirm is refused with exit 1 (`mapping_not_confirmed`). The sniff profile is correct. Confirm prints the sha. v1 gives `accepted=4 rejected=0`. v2 gives `accepted=5 rejected=1`. `rejects` shows `row=7 field=duration_s reason=invalid_number`. Compare gives `changed=2 added=1 unchanged=2 only_in_old=0`. The alt mapping gives fields, extra and unresolved identical to v1. Output is identical with the network denied (the probe returned errno 1).

Also confirmed:
- Editing the mapping after confirm (I appended a comment) is refused with exit 1 and writes an `ingest_refused` audit event.
- The lowercase paths `data/es` and `data/out/<other>` are refused.
- `--out` outside the bundle is refused.

## Findings

**F1. High (blocker): the NDA and cross-bundle input guard can be bypassed by changing letter case.** [mapping.py:275-283](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:275)
- **Cause:** the check compares `Path.resolve()` prefixes case-sensitively, but the default macOS filesystem (APFS) is case-insensitive.
- **Reproduction** (in /tmp/ndrev/w1, synthetic data):
  - `nightdesk ingest data/es/secret.csv --bundle practice` exits 1, as intended.
  - `nightdesk ingest Data/ES/secret.csv --mapping mappings/admin_v1.yaml --bundle practice` exits 0 with `accepted=1`. "SECRET TEXT" is then in `data/out/practice/captures/…/rows.jsonl`.
  - `DATA/OUT/test-other/x.csv` into practice also exits 0.
- **Fix:** compare `os.stat` identity or normalise case, or check `st_dev`/`st_ino` of the ancestors. Add a test.

**F2. Medium (blocker for the real-data swap): audit appends take quadratic time.** [audit.py:68](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/audit.py:68), [mapping.py:412-422](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:412)
- **Cause:** every `append_event` re-reads and re-validates the whole log, and ingest writes one event per row.
- **Measured:** 3,000 rows took 21.4 s; 6,000 rows took 86.6 s (4× time for 2× rows).
- **Impact:** a 100k-row source would take hours.
- **Fix:** read the log once and append in batch, or keep a running seq.
- **Related, Low:** there is no lock. Two concurrent writers can produce duplicate `seq` values, and `read_events` then refuses the bundle permanently.

**F3. Medium: one numeric cell aborts or hangs the whole ingest.** [mapping.py:227-241](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:227)
- A `duration_s` cell of `1e5000` fails later, during `canonical_json` at line 402, with exit 1 ("Exceeds the limit (4300 digits)…"). No reject row, no capture and no audit event are written for the other row.
- A cell of `1e100000000` runs at full CPU for more than 30 s (killed by `timeout`, exit 124), because `int(Decimal)` builds a gigantic integer.
- **Fix:** bound the exponent or digit count before converting and reject with `invalid_number`.

**F4. Medium: `compare` reports "compared" across mapped and unmapped tables.** [generic.py:36-52, 124-127](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/generic.py:36)
- If only one side was ingested, one side has typed mapped fields and the other has raw strings.
- **Reproduction:** `nightdesk compare e.csv e2.csv --key record_id` printed `status=compared … changed=1 only_in_old=1`. The diffs (`60` → `"90"`, `note` appearing as a field) are artefacts of the two modes.
- The per-side `mode` appears only inside the JSON and Markdown export, not in the CLI summary.
- **Fix:** refuse, or set `identity_uncertain` with a reason such as `mode_mismatch`, when the modes or datasets differ.

**F5. Low: the raw value of an unknown enum is lost.** [mapping.py:243](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:243), [mapping.py:338-340](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:338)
- `state=bogus_state` became `"unknown"`. The column counts as consumed, so the raw value is in neither `extra` nor `unresolved`.
- KICKOFF C5 says an unknown value is "never dropped"; at least the raw value should be kept in `unresolved`.

**F6. Low: a whitespace-only required key is accepted.** [mapping.py:327](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:327)
- `record_id="   "` passed the `required` check and can then be used as a compare key.

**F7. Low: the Markdown export double-escapes HTML entities.** [export.py:16-17](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/export.py:16)
- `html.escape` runs first, then the `#` is backslash-escaped, so `O'Brien` is written as `O&\#x27;Brien` and renders literally as `O&#x27;Brien`.
- This is not an injection, but it shows the data incorrectly.

**F8. Low: `flatten --out` has no bundle check.** [flatten.py:68-72](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/flatten.py:68)
- `nightdesk flatten data/es/secret.csv --header-rows 1 --out data/out/practice/leak.csv` exits 0 and copies es data into the practice bundle.

**F9. Low: a key typo is not reported as an error.**
- `--key recordid` exits 0 with `identity_uncertain reason=missing_or_nonscalar_key`. That is honest, but an error naming the missing key would be clearer.

## Within Phase 0 contract
These behaved as specified when I checked them:
- Mapping YAML is data only: an allowlist of parsers, duplicate keys and anchors refused, no `eval`.
- Confirm writes an audit event with actor, time and sha256, and ingest refuses an unconfirmed hash.
- Rejects carry field, reason and gate, with no raw source values in the audit log.
- `ambiguous_local_time` is not guessed.
- Exports stay inside the bundle, refuse symlinks and are immutable. Each row links to its source row with sha256 and licence.
- No claims of removal or cancellation are made, and `only_in_old` is labelled "meaning unknown".
- `GenericRow` adds an `unresolved` field that the KICKOFF schema does not list; that is an acceptable extension.

## Limits
- I did not run XLSX or JSON adversarial cases beyond what the tests cover.
- I did not test crash atomicity between the capture rename and the audit events (mapping.py:406-422).
- The network-denied pytest run used `-p no:cacheprovider`. The ordinary run may have touched the gitignored `.pytest_cache`, but no snapshot file changed.

F1–F4 should be fixed before approval. F5–F9 can wait until later.
