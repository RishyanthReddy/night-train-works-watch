# Example data

Two real European rail captures that their licences allow publishing. Nothing else from
`data/` belongs here: every other source this project reads records its licence as `UNKNOWN`,
so those captures stay on the machine that made them and are listed in
[`data-catalogue.json`](../data-catalogue.json) instead.

Both files are real captures, unedited. Their hashes are in the catalogue.

## `infrabel-works/capture.json` — Belgium, CC0

The long-term works export from Infrabel: 9,536 records, captured 2026-11-18. `_capture` at the
top of the file holds the provenance the fetcher recorded — source URL, raw-file sha256, capture
time, filter and licence.

Licence: **CC0** — public domain, no conditions.

Ingest it:

```sh
uv run nightdesk ingest example-data/infrabel-works/capture.json \
  --mapping mappings/infrabel_works.yaml --bundle test-mine
```

That should print around `accepted=8693 rejected=0 filtered=843 licence=CC0`. The 843 filtered
rows are records the mapping's `logically_deleted: "No"` filter drops; they are counted, not lost.

## `rijden-archive/services.csv.gz` — Netherlands, CC BY 4.0

Saved archive reports for October 2026, filtered to trains 452 and 453: 35 MB compressed, one row
per train and stop.

**Attribution, required by the licence:** *Rijden de Treinen, Open data about train services
(CC BY 4.0)* — <https://www.rijdendetreinen.nl/en/open-data/train-archive>. If you show anything
derived from this file, keep that line with it.

Stage it:

```sh
uv run nightdesk stage-rijden-archive example-data/rijden-archive/services.csv.gz \
  --month 2026-10 --bundle test-mine
```

That writes a capture into the bundle's `source-captures/` and reports `"rows": 359`.

## Why not the others

| Source | Licence recorded by the capture | Here? |
| --- | --- | --- |
| Infrabel works | `CC0` | yes |
| Rijden de Treinen | `CC BY 4.0` | yes |
| DB OpenBoards, DB Timetables | `UNKNOWN` | no |
| NS maintenance | `UNKNOWN` | no |
| Swiss SIRI | `UNKNOWN` | no |
| Train Archive | `UNKNOWN` | no |
| German / Italian / Dutch snapshots | `UNKNOWN` | no |

An unclear licence is not a licence to publish. Those captures are reproducible with your own
key — see "Where each key comes from" in the top-level README — and the catalogue holds their
hashes so you can confirm you fetched the same bytes.
