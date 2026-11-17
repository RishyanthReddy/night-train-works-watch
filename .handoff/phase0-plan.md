# Phase 0 execution plan — revision 2

Scope and approval: execute KICKOFF.md Phase 0 P0.1–P0.8 only, in order;
P0.9 skipped. User explicitly said to start on 2026-11-17. No Phase 1 code.
This document makes the existing plan's commands concrete; material changes
require the user's decision. KICKOFF.md remains unchanged.

Allowed product paths: .gitignore; pyproject.toml; uv.lock; SPEC.md first line only;
src/nightdesk/{cli,config,model,audit,generic,export,gates}.py;
src/nightdesk/intake/**; src/nightdesk/fetch/**; mappings/**; tests/**; .handoff/**.
Generated runtime outputs under data/out/<bundle>/ are ignored, never staged.
Preserve all existing files, restricted downloads, Praha and nested .handoff/.
Never read restricted input into a delegate, test fixture or demo.

## Decisions within the existing Phase 0 contract
- Python 3.12, existing pinned dependencies; argparse and simple functions.
- Fixed parser allowlist, safe YAML; mapping is data, never eval or execution.
- GenericRow scalar targets only; rail types, dotted destinations/list parsers,
  timeutil, revision store, UI and hash-chain/seal are deferred as KICKOFF says.
- CSV/XLSX/JSON table reading is shared intake code; errors identify row/field/reason.
- Keep unused source fields in extra and every accepted/diff row's provenance.
- Record rejects explicitly and exclude rejected rows from accepted comparisons.
- `compare <old-file> <new-file>` hashes the files, then resolves already ingested
  accepted JSONL and rejects in the selected bundle, matching absolute source path
  and content sha256. It never parses raw table rows as a validation bypass.
  No matching ingest (including an edited file) is refused with ingest instructions.
  Different mapping hashes for the same path/content are ambiguous and refused.
  Repeated captures under the same mapping hash may use the latest capture for
  provenance only. The original mapping must still match its recorded hash and be
  confirmed in this bundle; edited/missing mappings require confirmation + re-ingest.
  Rejected rows are exported separately as excluded (field/reason/source), not as
  accepted or missing rows. An old key rejected in the newer file is excluded from
  the only-old category when its raw key can be established; never call it removed.
  Preserve the raw reject row locally to explain exclusions without inventing values.
  This is a small Phase 0 ingest-artifact index, not the Phase 1 revision store.
- Mapping confirmation is scoped to bundle and exact YAML sha256, with actor/time.
  The user authorised the acceptance command; the CLI records the local actor.
- Generic comparisons are descriptive selected-table differences. Missing keys
  are not cancellations or confirmed removals; no key/duplicate key is uncertain.
  No rail completeness/removal semantics are implemented ahead of Phase 1.
- Bundle names and output paths must not escape or cross the selected bundle root.
- Bundles: practice (nda false), es (nda true), and safe named test bundles matching
  `test-[a-z0-9][a-z0-9-]{0,47}` (nda false), rooted at data/out/<bundle>/.
  `rejects` groups rows by capture/import rather than blending import history.
- Append-only audit in Phase 0 only; no claims of tamper-proofing or truth.
- Synthetic fixtures are visibly labelled in mappings/records/exports.
- Source-specific names stay in mappings, adapters or config only.

## Task order and evidence
P0.1: baseline commands already run: uv sync --frozen exit 0 (23 packages);
uv run --offline pytest exit 5 (no tests). Builder ignores all data/, changes only
SPEC's first line and records evidence. Review these protection changes before
the requested bootstrap commit. Use a dedicated local phase0 branch; no remote.
Coordinator mechanically reviews protection changes before bootstrap commit (no
extra council round). Stage exactly .gitignore, SPEC.md, pyproject.toml, uv.lock,
.handoff/TODO.md, .handoff/phase0-plan.md, .handoff/phase0-baseline.txt,
.handoff/review.md. These are all Phase 0 allowed paths; all existing source stubs,
KICKOFF, AGENTS, CLAUDE, scripts and research remain untracked and unmodified at
bootstrap. Later stage only implemented files within Phase 0 allowed paths.
Never stage data/, .handoff/reference/, .handoff/.handoff/, Praha, .venv or caches.
Before each commit: `git check-ignore -v data/raw/rfc/rfc.xlsm data/snapshots/de/2026-11-14/baustellen.json`,
`git diff --cached --name-only`, and scan staged content for credential assignments,
private-key markers and token patterns without printing matching secret values.
Record scan command + outcome. No baseline research is silently added.
Switch the unborn phase1-core to phase0; the old unborn branch has no ref to retain.
P0.2: help/config + smoke test; `uv run --offline nightdesk --help` exit 0.
P0.3: Phase 0 models + per-bundle append-only JSONL; validate SourceRef and aware times.
P0.4: sniff profile (columns/types/null rates/up to five samples) across three formats.
P0.5: mappings/gates/rejects/flatten and confirm+refusal; test malformed values and YAML.
P0.6: author admin_v1.yaml/admin_alt.yaml against documented fixture schemas.
P0.7: comparison+exports preserving source rows and uncertainty.
P0.8: write fixtures and run the end-to-end acceptance checks below.
Builder records task completion and exact commands/exits in its evidence file;
builder returns facts and gaps only, no self-assigned pass verdict.

## Fixture contract (document in tests/fixtures/admin/README.md before P0.6)
Every file is synthetic. v1 columns: record_id,status,owner,duration_s,notes.
v1: A1/open/alice/300; B2/open/bob/120; C3/closed/cara/90; D4/open/dan/60.
v2: A1 status waiting; B2 owner bea and duration_s 150; C3 unchanged;
D4 duration_s BROKEN (reject only in v2); E5/open/erin/180 added to selected table.
Notes identify synthetic rows and stay equal unless specified.
v1 accepted 4/rejected 0; v2 accepted 4/rejected 1 (D4,duration_s,parse error).
Comparison: 2 changed, 1 unchanged, 1 only-new/added-to-selected-table, D4 excluded
with before-source and rejected-after-source; no confirmed removed/cancelled row.
admin_alt has exactly v1's content, renamed/reordered columns and duration minutes;
300->5, 120->2, 90->1.5, 60->1. `minutes_to_seconds` accepts finite decimals only
when multiplication by 60 yields integer seconds, rejecting fractional seconds.
Assert v1 vs alt accepted `fields` equal (ignore distinct SourceRef); retain extra.

## Real CLI acceptance (from repository root)
Prefix proposed `nightdesk` commands with `uv run --offline` to use the installed CLI.
1. `uv run --offline nightdesk sniff tests/fixtures/admin/admin_v1.csv`
2. First ingest v1 before confirmation: nonzero refusal naming unconfirmed mapping.
   `uv run --offline nightdesk mapping confirm mappings/admin_v1.yaml --bundle practice`
   `uv run --offline nightdesk ingest tests/fixtures/admin/admin_v1.csv --mapping mappings/admin_v1.yaml --bundle practice`
   `uv run --offline nightdesk ingest tests/fixtures/admin/admin_v2.csv --mapping mappings/admin_v1.yaml --bundle practice`
3. `uv run --offline nightdesk rejects --bundle practice`
4. `uv run --offline nightdesk compare tests/fixtures/admin/admin_v1.csv tests/fixtures/admin/admin_v2.csv --key record_id --bundle practice --out data/out/practice/`
5. `uv run --offline nightdesk mapping confirm mappings/admin_alt.yaml --bundle practice`
   `uv run --offline nightdesk ingest tests/fixtures/admin/admin_alt.csv --mapping mappings/admin_alt.yaml --bundle practice`
   Compare canonical field values to v1 (provenance differs by source file by design).
6. Repeat 1–5 with the six service credential variables unset and network access
   denied at the process/OS level. `uv --offline` alone does not prove network denial.
   Exact wrapper, from repository root:
   `env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' /opt/homebrew/bin/uv run --offline <command>`.
   Run a Python socket.connect to literal 1.1.1.1:443 under this wrapper: require
   PermissionError (and assert all six credential names absent); no connection must
   succeed. Coordinator verified denial and uv-under-sandbox on 2026-11-17.
   Execute steps 1–5 separately under that wrapper, substituting every practice
   with test-offline-p0 (first verify it has no imports), including
   `--out data/out/test-offline-p0/`. If already used, take a new safe test slug;
   never delete history to make a test pass. Same wrapper with `pytest` runs tests.
   Each reviewer similarly uses a unique test-<reviewer>-<run> bundle and output
   root for its whole sequence, both to avoid contamination and test refusal.
   Actor/time/capture metadata may differ; accepted fields/rejects/diff must agree.
All success commands exit 0; intentional refusal nonzero. Read exported files and
verify sources, synthetic label, changed/added/unchanged rows and broken-row exclusion.
Also exercise changed-YAML reconfirmation, cross-bundle confirmation refusal,
missing/duplicate comparison keys, edited/un-ingested/ambiguous inputs, real CLI
sniff+ingest for JSON/XLSX and merged-header refusal -> flatten -> successful ingest.
Run `uv run --offline pytest` with the same denial: must collect actual tests and exit 0.
Inspect `git diff`, all new files and data ignore status; scope violations block review.

## Reviews, commits and checkpoints
Plan gate satisfied: Kiro Opus medium approved revision 2 on 2026-11-17; coordinator Codex approves the same execution plan.
User approved KICKOFF and start. Latest user direction: council at END of Phase 0 only.
Council: Kiro claude-opus-5.5 medium; Codex gpt-6.1-sol high; Cursor deepseek-v41-flash-1017 reasoning_effort max.
After build: all three independently run meaningful checks and the CLI; score /10,
report blockers and limitations. No checkout changes while reviewers run.
Coordinator persists findings in .handoff/review.md after all reviewers finish.
At most two builder fix rounds; new review tasks after fixes, never reuse a review turn.
Commit only an approved snapshot; record hash and verify its paths. No push or merge.
Update TODO/state/next/sources and report the swap slot: input file + mapping YAML,
flatten for supported multi-header files, small adapter only for unsupported logic.
Stop at Phase 0. Later Opus integration checkpoints: after Phase 1, Phase 3, Phase 4.
