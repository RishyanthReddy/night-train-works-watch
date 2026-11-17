# Phase 1 council R3 — Codex Sol review

**CHANGES REQUESTED — 8/10.** One reproducible Phase 1 performance blocker remains. The reported R1/R2 functional fixes passed the current suite and the additional checks below. No Phase 2+ requirement is included in this verdict. The approved certifi exception is accepted.

## P1-R3-S1 — High: queue boundary enumeration is cubic in the number of selected path legs

**Location:** `src/nightdesk/desk.py:99–102`, invoked for every leg/date at `src/nightdesk/desk.py:191–201`. In the UI, `src/nightdesk/ui/app.py:108` calls the queue on each rerun.

`_checks` traverses every pair of legs in the context before testing whether either member is the selected revision. `queue` calls `_checks` for every selected leg, on both sides. With n legs on one operating date this performs 2*n^3 pair iterations, even when every leg has sequence 1 and there cannot be an adjacent pair. Each pair reads sequence three times. The new operation-scoped storage indexes fix the R2 repeated-read problem, but do not fix this separate CPU loop.

Reproduction uses only the supplied synthetic path-leg row and confirmed `mappings/syn_legs.yaml`. Generate n distinct request ids and train numbers, all sequence 1, with one service date. Import before/after files differing in source_status. There are no works, runs or journey links, so this isolates the leg enumeration. Both captures import successfully, and queue returns exactly n rows.

| Legs in each capture | Before import (s) | After import (s) | Queue (s) | One dossier (s) |
|---:|---:|---:|---:|---:|
| 100 | 0.110 | 0.112 | 0.213 | 0.182 |
| 200 | 0.206 | 0.228 | 1.031 | 0.375 |
| 400 | 0.443 | 0.511 | 7.643 | 0.723 |
| 800 | 0.791 | 0.857 | **58.965** | 1.477 |

These are actual local synthetic measurements, not extrapolations or a general throughput guarantee. A separate deterministic probe calls the real `_checks` with instrumented synthetic leg objects: n=4/8/16 causes 384/3,072/24,576 sequence accesses respectively, exactly 6*n^3 across both sides.

**Impact:** an ordinary selected capture with hundreds of train legs blocks the planner's queue on each rerender; 800 legs took almost a minute with no matching work to do. This affects the Phase 1 queue/dossier workflow itself, including review and export rerenders. The existing 2x2,000-work regression exercises storage loading and does not exercise queue construction with many legs.

**Concrete fix:** index neighboring sequence candidates once per context (or look up candidates relative to the current revision's sequence), and only check pairs involving the selected leg. Reuse dated boundary results within an operation where appropriate. Keep missing-link findings and all existing border semantics intact. Add a deterministic bounded-enumeration regression using hundreds of legs; avoid a machine-specific wall-time assertion. A persisted or global cache is unnecessary.

**Evidence:** `/tmp/nightdesk-phase1-r3-sol/queue_scale.py`, `queue_scale_800.py`, `queue-scale.log`, `queue-scale-800.log`, `queue-scale.json`, `queue-scale-800.json`, `adjacency_count.py`, `adjacency-count.log`. Both benchmark commands and the count probe exited 0.

## Verification and commands

All product execution ran from `/tmp/nightdesk-phase1-r3-sol/workspace`, or a synthetic child directory under `/tmp/nightdesk-phase1-r3-sol`. This copy contains `src/`, `tests/` including synthetic fixtures, `mappings/`, project metadata and a read-only-use symlink to the existing `.venv`. `PYTHONPATH` selects the temporary copy's source. No `uv sync` or install ran; the frozen environment was not rewritten.

The common wrapper was:

```sh
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/tmp/nightdesk-phase1-r3-sol/workspace/src \
  UV_CACHE_DIR=/tmp/nightdesk-phase1-r3-sol/uv-cache \
  PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=<own tmp>' \
  sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  uv run --offline --no-sync <command>
```

| Command after the wrapper | Exit | Observed result / log |
|---|---:|---|
| `pytest -q` | 0 | **325 passed in 23.72s**; `pytest.log`; basetemp `pytest-temp` |
| `python tests/phase0_acceptance.py` | 0 | Six acceptance steps, alternate YAML equivalence, JSON/XLSX, merged-header refusal/flatten/ingest; `phase0.log` |
| `python /tmp/nightdesk-phase1-r3-sol/integration.py` | 0 | Fresh actual CLI/API integration; `integration.log` |
| `pytest -q tests/test_r3_independent.py` | 0 | **5 passed in 1.85s**; `independent.log`; basetemp `independent-temp` |
| `python /tmp/nightdesk-phase1-r3-sol/queue_scale.py` | 0 | Actual 100/200/400-leg queue/dossier benchmark |
| `python /tmp/nightdesk-phase1-r3-sol/queue_scale_800.py` | 0 | Actual 800-leg queue/dossier benchmark |
| `python /tmp/nightdesk-phase1-r3-sol/adjacency_count.py` | 0 | Exact cubic sequence-access counts |

The integration script verifies all six credential names are absent and a loopback connection is denied (errno 1). Actual CLI results include the expected refusals: unconfirmed capture import exit 1; sealed tail-tamper verification exit 1; edited audit event verification exit 1. All ordinary import/confirm/review/rejects/seal/verify commands exited 0. The script restores its own temporary audit bytes after deliberate tampering and verifies the seal again.

The fresh integration covers complete v1/v2 imports, explicit journey-link selection, A/B/time_unknown, separate unlocated work, boundary mismatch, retained work/run/source evidence, local review with owner/question, Markdown/JSON export, idempotent v2 reimport, v3 stale/reopened state, reanswer, syn_bad rejection and effective incompleteness, external seal verification, cut-tail refusal and edited-event refusal.

Additional independent functional cases (temporary test file only):

1. Remove only the final leg from the three-leg capture; queue, removed-side dossier, before findings, export and reverse addition remain available.
2. Make the before capture incomplete: absent after leg stays unknown and produces no removed list.
3. Make the after capture incomplete: same unknown-presence guarantee.
4. Remove an operating date while renumbering the train, with an explicit source link for both numbers: correct old train/run display, after-side operating-date mismatch, queue/dossier agreement.
5. Reverse manifest role order: complete loading, grades and check-audit deduplication remain valid.

The full 325-test run includes `test_phase1_presence.py` and `test_phase1_integrity_scale.py`: whole-leg presence, removed-date boundary, source/artifact/completeness validation, authoritative predecessor, match-v3 line rules, grouping and audit deduplication, and bounded-read 2x2,000-work imports/loading. I did not treat their existence alone as proof; the suite actually passed against the copied frozen product.

## Visual evidence and limits

I actually viewed `.handoff/phase1-r3-removed.png` and `phase1-r3-added.png`: each shows the appropriate missing side, an explicit source-record-not-observed message and synthetic labelling. I also viewed `phase1-r2-works.png` and `phase1-r2-stale.png`: the scoped no-match sentence, separate unlocated warning, grades and prominent stale-review warning are visible. These are supplied browser captures, not a fresh browser session of my own. Fresh removed-date/group visual verification is **UNKNOWN — not checked**; the current AppTest regressions passed. No browser or server was started by this review.

## Snapshot / read-only result

- `.handoff/phase1-council-r3-snapshot.json`: **92 entries, 92 matching SHA256 hashes before, 92 matching after; zero mismatches.**
- Snapshot file SHA256: `bb9eaea3a480bb33e16a1cef6ca2282722c64b00137074be43eb6561d0bfca9e`.
- `hash-before.json` and `hash-after.json` retain the assertions. All applicable snapshot entries also match the temporary code/fixture copy used for the checks.
- Tracked checkout status before/after was identical (`git-before.txt`, `git-after.txt`). No checkout edit, handoff write, checkout `data/` read, delegation, commit, push or network fetch was performed by this reviewer.
- Read: KICKOFF sections 0/2/7/9 through Phase 1, global/project handoff files, review ledger, all three Phase 1 R1 reports and all three R2 reports. The parent's claimed visual automation failure was preserved as a limit, not converted into a successful visual claim.
- Setup-only note: two initial copy-preparation commands exited 1 because top-level `fixtures/` and `TODO.md` do not exist. Preparation was corrected to use `tests/fixtures/` and existing files; neither failure altered the checkout or affected a verification run.

Report saved only under `/tmp`. Parent to record P1-R3-S1 in the project ledger. Stop after this report; no fix was applied.
