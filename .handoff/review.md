# Review ledger

| ID | Finding | Severity | Status | Fixed by |
|---|---|---|---|---|
| P0-PLAN-01 | Sol: compare raw-path command must resolve accepted same-bundle ingests; reject missing/stale/ambiguous artifacts. | blocker | fixed | Coordinator: phase0-plan revision2 pins resolution, rejects and tests; council recheck pending. |
| P0-PLAN-02 | Sol/Opus: exact network denial, credential unset wrapper and fresh bundle roots missing. | blocker | fixed | Revision2 exact sandbox-exec wrapper; actual probe PermissionError, uv starts successfully (phase0-baseline.txt). |
| P0-PLAN-03 | Opus: fixture schema/outcomes and decimal minute conversion unspecified before mappings. | blocker | fixed | Revision2 fixture contract specifies four v1 rows, v2 outcomes, alt equivalence and integer seconds. |
| P0-PLAN-04 | Opus: concurrent reviewers/repeated captures contaminate practice outputs; grouped rejects and safe test bundles needed. | blocker | fixed | Revision2 unique named test bundles and per-capture rejects; implementation not yet built. |
| P0-PLAN-05 | Opus: bootstrap commit lacks reviewer/stage list/data-ignore and secret checks. | blocker | fixed | Revision2 coordinator mechanical check and explicit allowed staged paths; no research staged. |
| P0-PLAN-06 | Carbon run failed after feedback: Requests ending with a model turn are not supported. | historical | wontfix | User retired Carbon from council; replaced by Cursor DeepSeek in latest AGENTS. No Carbon approval required. |

2026-11-17: Independent Kiro Opus medium APPROVED revision2, verifying P0-PLAN-01..05 addressed. Task bf360436-2538-4af0-a90c-95d3538e2130; raw verdict delivered to coordinator. Coordinator Codex approves same plan. Council only at end of Phase0.
