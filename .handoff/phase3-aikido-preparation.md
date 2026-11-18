# Local Aikido preparation — no external scan run

Scope is our own committed code and permissive dependency lock only. No account was
created, no repository connected, no files uploaded and no scanner token requested.
No remote exists in this checkout. ES repos, data/, NDA files, local caches/sniff
samples/exports/audits and keys never enter a cloud scanner. This preparation does
not constitute an Aikido report or a security certification.

Verified local evidence: phase3-security-scan.json lists all reachable Git blobs and
tracked/new product files checked with selected private-key/GitHub/OpenAI-style token
patterns, AST check for eval/exec/compile in src/nightdesk, no tracked data and no
configured remote. Pattern scanning is limited; absence of matches is not proof.
Frozen dependency installation and offline tests are recorded separately.

The user action later: authorise private own-code GitHub repo creation/push separately,
review the exact commits and absence of data/keys, then create an Aikido account and
select only that repository (not all repos and never an ES repo). Official docs say
repository connection starts a scan automatically, so the connection itself remains
the approval boundary. No connection will be made merely to explore account setup.
Retain scanner findings/severities/commit/time/scope locally, fix confirmed code issues,
rerun checks and keep the actual report for the proposed slide. No report exists yet.
Plan pricing, account entitlement and free-plan repository limits are UNKNOWN—not
established for this user; verify them before any paid action.

Official pages read2026-11-18 (read-only documentation, no account interaction):
- https://help.aikido.dev/getting-started/setting-up-your-account/create-account-and-connect-your-repositories
- https://help.aikido.dev/code-scanning/connect-your-source-code/connect-github-account-to-aikido
- https://help.aikido.dev/code-scanning/scanning-practices/ignore-via-code-with-aikido-files

The exclusion-file documentation is future configuration guidance only. We have not
created .aikido (outside Phase3 allowed paths) or weakened any scanner coverage.
Ignored local files are kept outside Git; exclusions are not a replacement for that.

Local checkpoint limit verified during council: refs/t3 can retain older data paths
although HEAD/index exclude data/. Do not delete those user/tool refs here. Any future
authorised push must name only the reviewed branch after a branch-object check; never
mirror or include refs/t3. git push -h confirms --all means branches and --mirror means
all refs; neither is the intended bounded own-code push. No push was performed.
