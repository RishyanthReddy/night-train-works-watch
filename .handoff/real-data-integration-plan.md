# Real-data integration plan

The user authorized this work after Phase 3 and requested a final council review. The Phase 3 baseline is the local product commit 383c2c8. The existing Infrabel D-1 work and Mistral prompt correction are pending worktree changes. Preserve existing offline workflow and evidence gates.

1. **Observation workflow.** Open and export a genuinely sourced run directly from one selected capture. Leave the existing path-comparison workflow for actual path revisions. Keep scheduled, observed and changed information distinct.
2. **Public and saved inputs.** Rehearse Infrabel D-1, long-term Infrabel works and saved European Sleeper GTFS. Add a local-only German work importer for saved captures. Preserve complete validity intervals, source identities and rolling-window provenance. Historical comparisons must use original capture times and declared coverage. Do not infer removals from partial captures.
3. **Authenticated sources.** Verify NS maintenance encoding and coverage, DB planned/changed event semantics, Swiss planned SIRI-SX rail filtering and credential-free redirect handling, and an authorized Train Archive file with an independently verifiable train identity. Source knowledge from public documentation does not replace credentials or establish live availability. The recorded temporary credentials were used for probes. Do not assume they persist. Use fresh secure injection when ready to test each adapter.
4. **Text.** Recheck the Mistral wire contract and run a single synthetic proposal through the full validation path. Preserve consent and explicit review. Operational notices and other restricted sources stay within existing licence and bundle rules. Rijden de Treinen, piebro, ViaggiaTreno and the RFC workbook are complementary source categories. Only stage usable data after verifying rights, schema and evidentiary semantics. The restricted workbook remains local.
5. **Acceptance and review.** Require a provider-specific capture, schema check, source-linked intake, offline replay and proof of the app/export workflow per usable source. Check missing credentials, empty or partial pages, redirected credentials, date boundaries, same-number collisions, demo isolation, and no inference from schedules or predictions. Run the full offline suite, CLI and app acceptance. Freeze the verified diff and request the specified Opus, Sol and Grok council. Resolve material findings before marking completion.

## Provider research

- [Infrabel works catalogue and schema](https://opendata.infrabel.be/explore/dataset/langetermijnplanning-tcr-spoornetwerk/) and [CC0 terms](https://opendata.infrabel.be/pages/license/). Verify horizon from the live data. Long-term works are not in-year coverage.
- [DB Timetables product](https://developers.deutschebahn.com/db-api-marketplace/apis/product/timetables) and [API contract](https://developers.deutschebahn.com/db-api-marketplace/apis/product/timetables/api/280074). Exa found the provider documentation for station, plan and change endpoints. Station access previously succeeded. Treat changed times as published changes, not observed movements.
- [Swiss SIRI-SX cookbook](https://opentransportdata.swiss/en/cookbook/event-cookbook/siri-sx/) and [planned API quota](https://api-manager.opentransportdata.swiss/portal/catalogue-products/tedp_siri_sx-1). Exa confirmed XML and mixed-mode events. Plan describes a credential-free second request after the gateway redirect.
- [NS API portal](https://apiportal.ns.nl/). Firecrawl web search did not find a primary Disruptions v3 schema. Verify the existing approved endpoint against an actual response before implementing field inference.
- [Train Archive connector documentation](https://www.train-archive.eu/connect). Web search confirmed a public source catalogue, daily Parquet and CSV.gz. Daily delay rows can carry earlier delays forward and contain predictions. Do not present them as observed movements or infer a match from a train number that the feed omits.
- [Mistral structured output](https://docs.mistral.ai/inference/conversations/structured-output/custom). Web search confirmed custom schema output exists. Existing proposal rules still govern any model response.
- German works schema comes from KICKOFF Appendix A, the supplied field mapping, and the existing local saved captures. Unknown reuse remains local-only.

## Implementation checklist

- [x] Add source-run inspection and exports without a path revision.
- [x] Import Infrabel D-1 and long-term works, and replay the independently saved European Sleeper schedule.
- [x] Import and compare the two manifested German works captures with original time, completeness and source filter.
- [x] Capture, import and exercise NS maintenance, DB plan and full changes, and an exact Train Archive source-route selection.
- [x] Fetch live Swiss SIRI-SX with the required User-Agent on both hops and gateway authorization on the first only. Join dated native journey IDs to the official timetable calendar and prove real offline intake and export. Unmatched mode remains unresolved. [Endpoint notice](https://opentransportdata.swiss/en/change-in-data-provision-switch-to-new-endpoints/) · [GTFS field definitions](https://opentransportdata.swiss/en/cookbook/timetable-cookbook/gtfs/)
- [x] Test a dated European Sleeper archive match using ordered Swiss calls and times. This sample did not establish a match; the archival IC8 import remains independently verified and ES coverage is unverified.
- [x] Validate one consent-gated synthetic Mistral reply, revoke consent and replay offline.
- [x] Run offline full tests, Phase 0/2/3 CLI acceptance and real-capture AppTest workflows. Evidence in state.md and sources.md.
- [x] Collect and resolve council findings. Opus, Sol and Grok each approved round 3 at 9/10 on the same 167-file snapshot. Review evidence and accepted limitations are in `real-data-council-r3.json` and `review.md`.
