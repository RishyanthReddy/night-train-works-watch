# Real data in Nightdesk

Use a local practice bundle, such as `test-live-rail`. Fetching saves a source capture and prints the path to its intake file. Confirm the mapping and import that file separately. Imports, evidence views and exports run offline. Keep raw captures and exports under the bundle. Use a separate, manifest-approved bundle for a public demo.

| Source | Fetch or stage command | Mapping under `mappings/` | Evidence in the app |
| --- | --- | --- | --- |
| Infrabel D-1 | `nightdesk fetch-infrabel --bundle test-live-rail` | `infrabel_d1.yaml` | Reported observations with planned and real times. Point labels belong to the D-1 feed. |
| Infrabel works | `nightdesk fetch-infrabel --works --bundle test-live-rail` | `infrabel_works.yaml` | Long-term works with source point identifiers and validity. Source-deleted records stay in the raw export. |
| German saved works | `nightdesk stage-strecken-info <manifest.json> --bundle test-live-rail` | `strecken_info_works.yaml` | Original capture times, rolling-window policy, work validity and source membership findings. A manifest and matching raw works file are required. |
| NS maintenance | `nightdesk fetch-ns --bundle test-live-rail` | `ns_maintenance.yaml` | Maintenance titles, dates and source station evidence. Multi-section notices retain each section. |
| DB Timetables | `nightdesk fetch-db-timetables --bundle test-live-rail --eva 8000207 --date YYYY-MM-DD --hour HH` | `db_timetables.yaml` | The requested plan hour and full station changes, which may span other hours. The exact native stop ID joins the feeds. Run evidence presents published status and source feed per stop. |
| Swiss SIRI-SX | `nightdesk fetch-swiss-siri --bundle test-live-rail --gtfs-reference <official Swiss GTFS.zip>` | `swiss_siri_works.yaml` | Planned situations with a declared rail mode or an exact Swiss journey ID and active GTFS service date. Retains validity periods, proof of the mode match and any known mixed-mode scope. |
| Train Archive | `nightdesk fetch-train-archive --bundle test-live-rail --provider ch-opentransportdata --date YYYY-MM-DD --route IC8` | `train_archive_reports.yaml` | Source trips and stop reports, including predictions and any carried-forward delay. Pass `--trip-id` instead of `--route` for one native trip ID. |

Supply credentials through the local secret runner or the process environment. Use `NS_API_KEY`, `DB_CLIENT_ID` with `DB_API_KEY`, `SWISS_OTD_TOKEN`, or `TRAIN_ARCHIVE_TOKEN` for the corresponding source. The Swiss and Train Archive download requests carry no gateway credential. German saved works, the two Infrabel feeds and saved GTFS need no credential.

Use the Swiss timetable release for the service dates you need. Pass `--gtfs-reference` twice for two timetable years. The capture preserves both the source XML and the GTFS references with hashes. Some situations have no usable mode or dated journey and are excluded from the partial rail capture. If every candidate has unresolved rail scope, the command refuses the capture. [Swiss timetable catalogue](https://data.opentransportdata.swiss/en/group/timetables) · [Swiss GTFS field definitions](https://opentransportdata.swiss/en/cookbook/timetable-cookbook/gtfs/)

```sh
uv run --offline nightdesk mapping confirm mappings/infrabel_works.yaml --bundle test-live-rail
uv run --offline nightdesk ingest "<capture path printed by the fetch>" \
  --mapping mappings/infrabel_works.yaml --bundle test-live-rail
```

In the app, select the bundle, then a Works capture or Run capture. **Works evidence** lets you inspect and export source works and compare two captures from the same dataset. An expired record or a record entering a rolling window appears with its reason. Partial captures cannot establish additions or removals. Use the page controls for large captures. A full export retains all records and may take time for a large source file.

**Run evidence** works with a single capture and no path revision. Scheduled, published and observed times have separate columns. Archive trip IDs stay scoped to the provider and feed. A date filter on works describes the recorded validity range. The underlying notice may contain additional constraints on days and clocks.

Use `nightdesk evidence runs <capture>` to list source-run selections, `nightdesk evidence run <capture> <selection>` to export one, and `nightdesk evidence works <capture> --before <earlier-capture>` to export works and comparisons. Pass the same `--bundle` used for intake. Saved GTFS still uses `nightdesk gtfs import` and appears under Run evidence as scheduled evidence.

Mistral is optional in the running app. A live proposal requires bundle consent, a confirmed work mapping that enables external processing, and `MISTRAL_API_KEY`. Proposals still need review before import. Offline replay uses the existing local cache rules.

## European Sleeper national feeds

Use one local practice bundle for the Infrabel observations and the chosen dated ES timetable. The existing `mappings/infrabel_punctuality.yaml` imports saved [CC0 monthly Infrabel observations](https://opendata.infrabel.be/explore/dataset/stiptheid-gegevens-maandelijksebestanden/). Select a month or an ES-only extract and retain its source alongside the capture. Use `fetch-infrabel` for the previous day and `gtfs import` for the schedule. Retain the licence of the actual GTFS file. Transitous lists ODbL-1.0 for the community timetable.

Use `nightdesk evidence runs <capture> --bundle <bundle>` to locate each dated run selection and `nightdesk evidence run <capture> <selection> --bundle <bundle>` to inspect its station IDs. Save a reviewed JSON file under the bundle with this shape, replacing the placeholders with the selected IDs and reviewer's name.

```json
{
  "reviewed_by": "<reviewer>",
  "scheduled": {"capture": "<GTFS capture ID>", "selection": "<scheduled run selection ID>"},
  "observed": {"capture": "<Infrabel capture ID>", "selection": "<observed run selection ID>"},
  "stations": [
    {"scheduled_point": "<GTFS point ID>", "observed_point": "<Infrabel point ID>"}
  ]
}
```

Verify the service direction and each station identity against the source records. For an overnight train, the Infrabel date may be one day after the GTFS trip's start date. The comparison requires the same ES train number and at least one identical planned instant for each selected station. It shows both source records and leaves unreviewed stations outside the comparison. Open **Run evidence → Reviewed European Sleeper comparison** or run `nightdesk evidence es-comparison <review.json> --bundle <bundle>`. Both export Markdown and JSON locally.

This comparison checks the bundled Infrabel mapping version and the local GTFS import receipt. If an older schedule lacks the receipt, repeat its original `gtfs import` command to record it.

For the [Rijden de Treinen archive](https://www.rijdendetreinen.nl/en/open-data/train-archive), save a monthly CSV.gz and use the following commands. The stage command filters to ES 452 and 453 for the selected month and prints the local intake path. Source service IDs, reported delays, and cancellation flags are available in Run evidence and its export. Scheduled times and delays retain their published meaning. The archive contributes no observed clock. Credit Rijden de Treinen under CC BY 4.0.

```sh
uv run --offline nightdesk stage-rijden-archive services-2026-10.csv.gz --month 2026-10 --bundle test-es-national
uv run --offline nightdesk mapping confirm mappings/rijden_archive.yaml --bundle test-es-national
uv run --offline nightdesk ingest "<staged capture path>" --mapping mappings/rijden_archive.yaml --bundle test-es-national
```

The CC BY and ODbL inputs stay in local practice under the current CC0/synthetic demo rules. Live-feed reuse terms and Swiss/Train Archive ES identity remain unverified.
