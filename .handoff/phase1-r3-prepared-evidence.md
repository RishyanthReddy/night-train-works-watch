# Prepared R3 fixes — not applied to frozen checkout

Source: phase1-council-r3-snapshot.json copied after92 hash assertions. Prepared path: /var/folders/61/ynsfcdvj2493g9l_5tkw1mj40000gn/T/nightdesk-r3-fixes-pf1vu3u6

Builder independently reran Sol's deterministic probe against frozen code: sequence accesses384/3072/24576 for4/8/16 legs (6*n^3), exit0.

Changed prepared desk.py: operation-scoped indexes for leg sequences/positions and train/date runs. Only selected-leg adjacent candidates are examined; existing present-pair order is preserved. Missing neighbour observed in other selected capture yields sourced unknown adjacent_leg_not_observed only with explicit selected link; no current event or cancellation inferred. Deduplicated no_run_selected. Presence algorithm gets explicit audit rule version.

New test_phase1_queue_scale.py:100/400/800 nonadjacent legs bound sequence accesses,500 sequential legs bound check calls, remaining-leg queue/dossier missing-neighbour evidence and unlinked refusal.

Focused check:13 passed5.13s, exit0, OS network denied, all six credentials unset.

Actual synthetic benchmark in prepared copy, OS network denied, all six credentials unset, exit0:
| Legs | Before import s | After import s | Queue s | Dossier s |
|---|---|---|---|---|
|200|0.208|0.214|0.282|0.350|
|400|0.411|0.438|0.596|0.705|
|800|0.816|0.910|1.181|1.429|
Local measurements only; not a general throughput guarantee. Script queue_benchmark.py in prepared root. Full prepared suite:330 passed22.62s, exit0, OS network denied with all six credential variables unset; temporary copy only. prepared-files.json records the exact proposed bytes.

Prepared temporary app viewed in real separate browser: bb surviving leg shows unknown adjacent_leg_not_observed while its other existing neighbour still agrees. Screenshot phase1-r3-prepared-adjacent.png actually viewed. Fallback own browser closed, server stopped; temporary mutated fixture restored to frozen original bytes after check. Proposal file hashes and all main92 frozen hashes still match.
