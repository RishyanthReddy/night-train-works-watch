# Nightdesk

A change desk for a cross-border night-train operator.

Two separate things live in this repo, and you can use either without the other:

1. **A data pipeline.** It fetches train data from several European railway APIs, saves every
   pull as a file with its source, licence and capture time, and can compare two pulls of the
   same source. Useful on its own if your problem is "we need train data from several countries
   in one shape".
2. **An example tool.** A local desk where an operations planner sees what changed between two
   pulls, checks the border handover, records a decision and exports a receipt. Useful if your
   problem is "two countries disagree about the same train and someone has to decide".

![Route map of night train 452 from Hannover to Brussels South](docs/img/route-map.png)

*The explainer at [`docs/explainer-train-452.html`](docs/explainer-train-452.html) walks through
one real morning of train 452 — same train, three countries, three files.*

---

## Try the example first (offline, no keys)

```sh
uv sync
uv run nightdesk demo check     # verifies the demo files by hash; no network
uv run nightdesk demo serve     # opens the desk on 127.0.0.1
```

The demo runs on CC0 and synthetic files only. Nothing it shows is live, and nothing leaves the
machine.

Without `uv`, use a Python 3.12 virtualenv:

```sh
python3.12 -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/nightdesk demo serve
```

![The desk showing a leaving time that changed from 23:00 to 23:01](docs/img/desk-change.png)

*The desk: what changed, where it came from, the border-handover check, and the work records
that may explain it — for one train and one date.*

---

## If you are starting without me

Everything below runs with no keys and no network. In order:

1. **Get it running.**
   ```sh
   uv sync
   uv run nightdesk demo check          # verifies the demo files by hash
   ```
2. **Open the desk** — `uv run nightdesk demo serve`. That is the thing we are showing.
3. **Do the pipeline by hand, once**, so the desk stops being magic:
   ```sh
   uv run nightdesk mapping confirm mappings/infrabel_works.yaml --bundle test-mine
   uv run nightdesk ingest example-data/infrabel-works/capture.json \
     --mapping mappings/infrabel_works.yaml --bundle test-mine
   uv run nightdesk stage-rijden-archive example-data/rijden-archive/services.csv.gz \
     --month 2026-10 --bundle test-mine
   ```
   The first prints `accepted=8693 rejected=0 filtered=843 licence=CC0`; the second reports 359
   rows. Those are real Belgian and Dutch captures, in [`example-data/`](example-data/), published
   because their licences (CC0 and CC BY 4.0) allow it. The Rijden file carries an attribution
   line you must keep.
4. **See what has already been pulled** — [`data-catalogue.json`](data-catalogue.json) lists every
   capture held on this machine: source, licence, size, sha256, capture time. Nothing is published
   from it that a licence does not allow.
5. **What is not here** — the German, Swiss, NS and Train Archive captures record their licence as
   `UNKNOWN`, so they stay off the repository. Get your own key — see "Where each key comes from"
   below — and `uv run nightdesk doctor` will say what is still missing.

---

## Add your keys

Every source is optional. The Belgian file needs no key at all, so you can start with an empty
key file.

```sh
cp .env.example .env      # then fill in the keys you have
uv run nightdesk doctor   # shows which sources are ready, never prints a key
```

Keys are read from `.env` in the project root, or from one machine-wide file at
`~/.agents/secrets/nightdesk.env` (mode 600) so every checkout on the same machine can use them.
A real environment variable always wins over both files, and `.env` is git-ignored.

`nightdesk doctor` tells you exactly which variable is missing for each source and where to get
it. It never prints a value.

### Where each key comes from

All four are free, and each person gets their own — a key belongs to an account, so someone
else's `.env` will not work on your machine. The Belgian files need none of this.

| Variable | Where | What to do |
| --- | --- | --- |
| `DB_CLIENT_ID`, `DB_API_KEY` | [DB API Marketplace — OpenBoards](https://developers.deutschebahn.com/db-api-marketplace/apis/product/open-boards) | Register, open the OpenBoards product, press **Abonnieren / Subscribe** on the **Free** plan (10 requests per second), then read the client id and API key from your applications. Both values are needed. |
| `NS_API_KEY` | [NS API portaal](https://apiportal.ns.nl/) | Sign in at [apiportal.ns.nl/signin](https://apiportal.ns.nl/signin), subscribe to the NS App product, and copy the primary key (the secondary one works too). |
| `SWISS_OTD_TOKEN` | [api-manager.opentransportdata.swiss](https://api-manager.opentransportdata.swiss/) | Register, request the SIRI interface, and generate a token for it. |
| `TRAIN_ARCHIVE_TOKEN` | [train-archive.eu/account](https://www.train-archive.eu/account?new=1) | Create an account with a code sent to your email (no password), then copy a token from [your tokens](https://www.train-archive.eu/account/tokens). Open access covers the last 7 days and up to 5 sources per 30 days. |
| `MISTRAL_API_KEY` | [console.mistral.ai](https://console.mistral.ai/) | Optional — only `nightdesk text` uses it, and only when a case folder records consent. |

Fill in what you have, run `uv run nightdesk doctor`, and it will say which sources are ready and
which variable is still missing. Nothing else is required: every command refuses politely when a
key it needs is absent, rather than half-running.

The macOS Keychain is a convenience on this machine only, not a sharing mechanism — a teammate
never needs it, and a plain `.env` is the normal path.

---

## What the pipeline can fetch

![Flowchart: a source is fetched once, saved raw with its provenance, checked against a reviewed mapping, stored as an immutable revision, and compared with an earlier revision](docs/img/pipeline-flow.svg)

| Source | Country | What it gives | Key |
| --- | --- | --- | --- |
| Infrabel punctuality | Belgium | Monthly punctuality file, CC0 | none |
| Infrabel D-1 | Belgium | D-1 train reports | none |
| NS maintenance | Netherlands | Engineering works | `NS_API_KEY` |
| Rijden de Treinen archive | Netherlands | Saved archive reports, CC BY 4.0 | none |
| DB OpenBoards | Germany | Station departures and arrivals, planned and current | `DB_CLIENT_ID` + `DB_API_KEY` |
| Swiss SIRI | Switzerland | Planned disruptions | `SWISS_OTD_TOKEN` |
| Train Archive | Europe | Daily trips by train number | `TRAIN_ARCHIVE_TOKEN` |
| Local GTFS | any | Timetable file you already have | none |

**Status note.** The German source has two commands. `fetch-db-boards` uses OpenBoards, the
subscription you need now; `fetch-db-timetables` still calls the older Timetables endpoints, which
are being retired (new subscriptions closed in November 2026, switch-off planned for mid-2027), so
use the board command. One pull saves both a departures and an arrivals file for the station.

```sh
# one station, or several in one run
uv run nightdesk fetch-db-boards --bundle practice --eva 8000207 --eva 8011160 --limit 50
```

`--eva` is the station number. Verified on 2026-11-20: `8000207` is Köln Hbf and `8011160` is
Berlin Hauptbahnhof. A board covers a short window from the time you ask, so running the same
command each day builds a series of snapshots you can compare later.

To run it on a schedule, add one line to `crontab -e` (07:00 every day, log kept next to the data):

```
0 7 * * * cd /path/to/nightdesk && uv run nightdesk fetch-db-boards --bundle practice --eva 8000207 --eva 8011160 >> data/out/db-daily.log 2>&1
```

Each fetch saves a capture folder with the raw response, a hash, the source URL and the time it
was pulled. Later steps never re-fetch; they read the saved file. That is why the desk works on
a train with no wifi.

---

## How a planner uses the desk

![Flowchart: pick a folder, pick two pulls of one source, see which trains moved, open one train, record a decision, export the dossier, append to the history](docs/img/desk-flow.svg)

1. Pick the case folder and two pulls of the same source — an earlier file and a later file.
2. The desk lists the trains whose records changed, and why the checks gave a different answer.
3. Open one train: the changed field, the row it came from, the border-handover check and any
   engineering works on that route.
4. Record a decision — accepted, rejected or needs an answer — with a reason.
5. Export the dossier. Every action is appended to a hash-chained history that cannot be edited
   in place.

---

## What it will not do

- It never says "train 452 will be late". It shows two labelled facts and leaves the decision to
  a person.
- A train missing from a file is not a cancelled train. It may be outside what that file covers.
- A changed hash chain proves the history was not edited — not that the data is true.
- It never matches station names by similarity. A Dutch name and a Belgian name are linked only
  after someone confirms it, and the confirmation is recorded.

---

## Build on it

```
src/nightdesk/
  adapters/   one module per source: fetch, save a capture, never normalise silently
  intake/     read a file, check it against a mapping, store an immutable revision
  changes.py  compare two revisions of the same source
  border.py   one narrow consistency rule on adjacent linked path legs
  match.py    exposure grades: rejected, no match, unlocated, B, A, time unknown
  review.py   a local decision bound to a revision
  audit.py    append-only hash-chained history
  ui/         the Streamlit desk (presentation only; every number comes from a report)
tests/        the full suite, offline
mappings/     one reviewed YAML per source: columns, types, units, assumptions
```

Start here: run the tests, open `src/nightdesk/cli.py` to see every command, then read
`mappings/infrabel_punctuality.yaml` as a complete example of a reviewed mapping.

```sh
uv run pytest -q
```

---

## Data and licences

Captured data lives in `data/` and is git-ignored. Only reviewed mappings, code and synthetic
fixtures are committed. Files with unclear or restricted licences (German snapshots, ProRail,
ViaggiTreno, whereisthe.es) are never committed and never shown in the demo.
