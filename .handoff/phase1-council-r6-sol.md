# Phase1 council R6 — focused read-only review

**APPROVE — 9/10. No material delta regression reproduced.**

Scope is only the three-file R5→R6 delta: `src/nightdesk/desk.py`, `src/nightdesk/ui/app.py`, and `tests/test_boundary_scope.py`. Read the three R5 reports and current review ledger. R5 dispositions remain accepted; no expanded audit of unchanged features or Phase2 work.

All review writes are under `/var/folders/61/ynsfcdvj2493g9l_5tkw1mj40000gn/T/nightdesk-p1-r6-sol-8apxjpup` (macOS temporary directory), plus a temporary pointer file under `/tmp`. Execution used `ws/` containing the frozen product/test fixtures and a symlink to the existing `.venv`. No checkout/handoff edits, checkout data reads, environment sync/install, delegation, network fetch, commit or push. The parent records any ledger update.

## Verdict and bounded acceptance

No material findings requiring a severity/file/line/repro entry.

- **O1 verified:** at desk.py:117–125, explicitly chosen same-network/train records with distinct non-null sequences resolve per sequence. An independent eight-case scope matrix confirms default multiple records stay ambiguous, explicit distinct selections resolve, partial selections exclude the other sequence, and duplicate/null sequence choices stay ambiguous.
- **O2 verified:** at desk.py:189–190, a deselected adjacent sequence retains exactly one `unknown/boundary_leg_not_selected` finding in the reentry shape. Independent tests exclude the left and right neighbour separately; the finding has input refs, the expected sequence, and `boundary-scope-v1`. No positive result is invented for the excluded boundary.
- **Integration verified:** independent synthetic aa→bb→aa fixture starts with two ambiguous boundaries; full explicit selection produces two real after mismatches and two before agreements. Each partial selection produces one after mismatch plus one unknown. Queue summaries equal dossier summaries. JSON export retains selections/findings; escaped Markdown retains the mismatch reason; comparison/dossier audit events retain choice IDs and scope rule; local audit verification succeeds.
- **Capture isolation:** using changed revisions in both captures, selecting after revisions resolves only the after capture; before remains ambiguous. Content-identical revision IDs legitimately select the shared revision wherever it appears.
- **UI verified through AppTest:** selecting all reentry records renders two mismatch text entries and clears the source-choice warning; deselecting sequence3 renders one mismatch, one excluded-neighbour unknown and the warning. Help at app.py:117 describes distinct leg numbers. This is automated UI verification; no fresh browser/screenshot/visual check is claimed.
- Full suite retains the existing mixed-request scale assertions (unlinked zero pair calls; selected two-member link four calls at 800 legs). No new timing/general scaling claim.

## Commands and exits

Run from `/var/folders/61/ynsfcdvj2493g9l_5tkw1mj40000gn/T/nightdesk-p1-r6-sol-8apxjpup`. `run.sh` changes into its `ws/` and runs:

```sh
env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN \
  -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH='/var/folders/61/ynsfcdvj2493g9l_5tkw1mj40000gn/T/nightdesk-p1-r6-sol-8apxjpup/ws/src:/var/folders/61/ynsfcdvj2493g9l_5tkw1mj40000gn/T/nightdesk-p1-r6-sol-8apxjpup/ws/tests' \
  PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/var/folders/61/ynsfcdvj2493g9l_5tkw1mj40000gn/T/nightdesk-p1-r6-sol-8apxjpup/pytest-tmp' \
  sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  uv run --offline --no-sync "$@"
```

| Command | Exit | Result / evidence |
|---|---:|---|
| `./run.sh pytest -q test_r6_independent.py` (absolute test path) | 0 | **14 passed, 4.43s**, `probes.log` |
| `./run.sh pytest -q` | 0 | **337 passed, 39.46s**, `full.log` |
| Environment probe in independent tests | 0 | All six variables absent; bytecode/cache/basetemp flags asserted; imported desk path is own copy; socket denied with `PermissionError`, errno1 |
| `python3 check_hashes.py` | 0 | **94/94** checkout and **94/94** copy after execution; manifest unchanged; `integrity.log` |

The actual standalone CLI/Phase0 acceptance commands were not rerun in this bounded R6 review. Integration above exercises the changed API/UI/evidence paths; the full suite includes existing CLI tests.

Initial review-harness runs needed correction: a wrapper string-replacement typo misnamed `PYTEST_ADDOPTS`; the full suite was rerun with the exact required variable/settings above. Probe assumptions were corrected for macOS `/var` path normalization, empty defaultdict keys, Markdown escaping, shared content-addressed revisions, and distinct comparison/dossier audit payload schemas. Initial logs are retained as `full-initial.log`, `probes-initial.log`, `probes-second.log`. These were harness corrections; product files were unchanged.

## Freeze integrity

Before execution: **94/94** R6 entries matched the checkout. Exactly the three declared files differ between R5 and R6 manifests; R5 baseline text for each was independently hash-checked in the prior retained review copy before generating the three diff artifacts here.

After all final tests: **94/94** matched the checkout and **94/94** matched the execution copy. Manifest SHA256:

`26b79edc414a0d68e8bb4bfc2373bb15f79d83d9d796281ff9cc2a86d654e1f2`

| Changed file | R6 SHA256 |
|---|---|
| `src/nightdesk/desk.py` | `6cedf90b2146ddd1a414fb8874dcd179d55a6a27084d8dbcf4ca29701430e311` |
| `src/nightdesk/ui/app.py` | `15251a6c3f77ef9b244610e533c3358286f0da6e576b6e699a395ebaa0f43558` |
| `tests/test_boundary_scope.py` | `2b16e6fcb6df74c2ff1888a4592f8d88d0f0658346212774da32ceb4543c8b69` |

Evidence: `initial.json`, three `.diff` artifacts, `r6-manifest.json`, `integrity-final.json`, `integrity.log`, `run.sh`, and the test/log files in this directory. Stopped after report; parent owns commit/Phase2 continuation.
