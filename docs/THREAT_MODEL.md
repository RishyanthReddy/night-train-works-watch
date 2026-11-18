# nightdesk threat model

Scope: local planner practice tool. Untrusted CSV/XLSX/JSON, notice text and model
proposals enter deterministic gates, then bundle-scoped captures/revisions, selected
comparisons, limited checks, human review and local exports. No timetable approval,
dispatch, automatic messaging or delay prediction. Synthetic examples are labelled.

Assets: NDA source text, API credentials, bundle separation, source provenance,
immutable revisions, local decisions and the integrity of exported evidence.
Trust boundaries: source files → parser/mapping; notice → optional Mistral proposal;
proposal → schema/quote/time/identity gates; bundle → its own output files;
local audit → a separately retained trusted seal/count. A user or process with full
filesystem access can replace files and seals; this tool is not a host sandbox.

| Threat | Control | Limit |
|---|---|---|
| Prompt injection or invented fields | No model output execution/actions; bounded JSON, quote/schema/common/work gates; explicit human import; role/instruction markers reject | Quotes prove presence, not meaning. Denylist has language limits and false positives. |
| Cloud disclosure or key leakage | External processing defaults off; dataset flag plus explicit audited per-bundle Mistral consent and mapping confirmation; fixed HTTPS host, no redirect; environment-only keys; static errors | Live transport/billing not exercised; tests mock it. Consent follows asking the data owner. |
| Cross-bundle leakage | Resolved containment, isolated captures/aliases/cache/review/export/audit; explicit selections, no shared mutable model cache | Files copied outside the guarded roots by a user remain their responsibility. |
| Bad clocks, ids, absent/partial rows | Typed deterministic gates; uncertain identity/time unknown; exact sourced links, effective completeness before presence conclusions | No guessed cancellation, boundary equivalence or national train correspondence. |
| Hostile spreadsheets/archives | Values-only spreadsheet loading (`data_only=True`, `keep_vba=False`, `keep_links=False`); no macros or formula execution; bounded GTFS archive/date/row expansion | This is not malware detection. Parser/library/host compromise remains possible. |
| Audit edits/deletions/tail cuts | Hash chain; verify a read-only copy against trusted earlier external seal **and count** | Internal consistency is not source truth. Unsealed prefixes and recomputed chains are insufficient. |
| Misleading public demonstration | Hashed allowlist of synthetic/CC0 assets; transitive references checked; NDA bundle refused | Licence declarations depend on retained source evidence, not a legal scanner. |

Verification checklist: frozen `uv.lock` install; pattern scan of tracked files and
all reachable Git blobs (counts and limitations in `.handoff/phase3-security-scan.json`);
model output validated and never evaluated/executed; authored `.xlsm` and formula
rehearsal reads values without running macros; demo check passes; offline collision,
consent and sealed-copy tamper tests pass. Pattern scans and tests are evidence, not
proof that all secrets or vulnerabilities are absent. The intended product branch
excludes restricted/NDA inputs and keys; none is sent to a scanner or public demo.
Local orchestration checkpoint refs can retain historical data paths. Never push
those refs, mirror or all refs; verify the intended branch's objects before any push.

Aikido preparation is local only. No account, repo connection or scan exists from this
work. User creates/connects a private own-code repo only after separately authorising
its creation/push. ES repos and NDA data are excluded. Plan/limits require verification
at that time; no scanner report or security certification is claimed.
