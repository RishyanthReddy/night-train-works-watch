# SUPERSEDED by KICKOFF.md (2026-11-17) — historical only; do not build from this file.

Replaces the earlier spec (cancelled build). User gave the go on 2026-11-14.
Pre-build for HACK THE RAILS Track 1 (European Sleeper, "ES"), Sat 2026-11-21.
Background: `.handoff/state.md`, `.handoff/decisions.md`, `.handoff/sources.md`.

## What the product does
For each ES train on each night, list the track works on its route that are active at the hour the
train passes, with a confidence and a link to the source record. Later phases add a run board, a
path dossier, an LLM step for free-text notices, and alerts. Phase A is the matched table, the
snapshot diff, and an honest test of whether matched works go with more delay.

ES trains: 452/453 (Brussels/Amsterdam-Berlin-Prague), 474/475 (Paris/Brussels-Berlin),
400/401 (Brussels-Milan).

## Rules
- Python 3.12 with `uv`. Package `nightdesk` in `src/`. Existing scaffold files may be rewritten.
  Add deps as needed (duckdb, networkx, shapely, pyproj, websockets, scipy are fine). Permissive
  licences only.
- Evidence rule: never invent data. An unresolved link stays `None` with a reason. Every output row
  carries its source (dataset, record id, snapshot date).
- No LLM in phase A. No UI in phase A.
- Tests run offline on small fixtures cut from the real downloads. Network only in `fetch` commands.
- Downloaded files are untrusted: keep them under `data/`, never run Python from inside `data/`.
- No credentials anywhere. Local git commits only; no remote, no push.
- Small, readable code: it will be edited under time pressure on the day.

## Verified facts to build on (checked 2026-11-14)
German works, strecken-info.de, no login:
- Get a revision number from `wss://strecken-info.de/api/websocket` (message `type` =
  `NEW_REVISION`, value at `revision.nummer`).
- POST `{"revision": r, "filter": F}` to `https://strecken-info.de/api/baustellen`,
  `/api/streckenruhen`, `/api/stoerungen`. Working filter:
  `{"baustellenAktiv":true,"baustellenNurTotalsperrung":false,"betriebsstellen":[],"regionalbereiche":["MITTE","NORD","OST","SUED","SUEDOST","SUEDWEST","WEST"],"stoerungenAktiv":true,"streckennummern":[],"streckenruhenAktiv":true,"wirkungsdauer":0,"zeitraum":{"type":"ROLLIEREND","stunden":2016}}`
- Past ranges are refused (HTTP 400 "Ungültiger Zeitraum"). The API has NO history. Works that have
  ended drop out. So snapshots must be archived daily from now on.
- Record fields: `baustellenID`, `streckennummern`, `richtung`, `regionen`, `wirkung`
  (TOTALSPERRUNG, FAHRZEITVERLAENGERUNG, ABWEICHUNG_VOM_FPL, GGL_MIT_ZS_6, GGL_MIT_ZS_8, SONSTIGES),
  `gleisEinschraenkung`, `arbeiten`, `zeitraum{beginn,ende}`,
  `gueltigkeiten[{vonDatum,bisDatum,wochentage,vonUhrzeit,bisUhrzeit}]`, `langnameVon/Bis`,
  `ril100Von/Bis`, `koordinaten` (Web Mercator x/y).
- A snapshot from 2026-11-14 is in `data/snapshots/de/2026-11-14/` (46,215 works; 2,610 overlap
  1-13 Nov). Terms of use of this API are NOT checked: be polite (one fetch per run, real
  User-Agent, no parallel hammering).

German network, DB GeoServer WFS (anonymous):
`https://geoviewer.deutschebahn.com/geoviewer-geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&outputFormat=application/json&srsName=EPSG:4326&typeNames=<layer>`
- `ISR:ISR_V_GEO_STRECKENABSCHNITTE` (19,879 sections): `ISR_STRE_NR` (line number, same numbering
  as `streckennummern`), `ISR_STEL_ID_VON`, `ISR_STEL_ID_BIS`, `ISR_KM_VON_I`, `ISR_KM_BIS_I`,
  `ALG_LAENGE_ABSCHNITT`, `BET_GESCHWINDIGKEIT`, `INF_GLEISANZAHL`, geometry MultiLineString.
- `ISR:ISR_V_GEO_BETRIEBSSTELLEN_PUNKT` (11,313): `STEL_ID`, `BST_RL100`, `BST_STELLE_NAME`,
  `STRNR`, `LAGE_KM_I`, `BST_STELLENART`, geometry.
- Licence of these layers: not checked. Record it in `.handoff/sources.md` if you find it.

ES actual running in Germany, piebro/deutsche-bahn-data (CC BY 4.0), no login:
- Monthly: `https://huggingface.co/datasets/piebro/deutsche-bahn-data/resolve/main/monthly_processed_data/data-YYYY-MM.parquet`
  (2026-10 exists, 2026-11 does not yet). Query with duckdb httpfs. `train_type='ES'`,
  `train_number` in 452,453,474,475,400,401. Columns include `station_name`, `eva`, `delay_in_min`,
  `time`, planned and changed arrival/departure times, cancel flags, `train_line_ride_id`.
- Daily raw: `raw_data/year=2026/month=11/day=N` exists for days 1-13. Format NOT inspected.

Belgium, Infrabel Opendatasoft (`https://opendata.infrabel.be/api/explore/v2.1/catalog/datasets/<id>/records`):
- `langetermijnplanning-tcr-spoornetwerk` (CC0, 9,536 rows, 2024-12-15 to 2030-12-16): `id`,
  `date_begin`, `date_end`, `time_begin`, `time_end`, `line`, `tracks`, `ptcar_from`, `ptcar_to`,
  `bk_from`, `bk_to`, `impact_level` (Minor 7,423 / Medium 1,911 / High 143 / Major 59),
  `impact_description`, `logically_deleted`, geometry. Only 16 rows overlap October 2026.
- `ruwe-gegevens-van-stiptheid-d-1` and `stiptheid-gegevens-maandelijksebestanden`: per-stop rows,
  filter `train_serv="EURSLEEPER"`; fields `datdep`, `train_no`, `line_no_dep`, `line_no_arr`,
  `ptcar_lg_nm_nl`, planned/real times, `delay_arr`, `delay_dep` (seconds). These give the Belgian
  line numbers the train actually used.

## Deliverables

### 1. Fetch (`nightdesk/fetch/`, CLI `nightdesk fetch <what>`)
- `works-de`: snapshot the three strecken-info endpoints into `data/snapshots/de/<YYYY-MM-DD>/`
  with a manifest (url, revision, sha256, fetched_at, counts). Safe to run daily; a second run on
  the same day writes a new time-stamped folder rather than overwriting.
- `works-be`: full export of the TCR dataset into `data/snapshots/be/<date>/`.
- `network-de`: page through the two WFS layers, keep only the properties listed above plus
  geometry, write to `data/ref/de/`.
- `running`: ES rows from the monthly parquet files (all 2026 months that exist) and from the
  November daily raw data (inspect the format first), plus Infrabel ES rows, into
  `data/running/*.parquet`.

### 2. Train model (`nightdesk/model.py`, `nightdesk/trains.py`)
- From the running data derive, per train number, the ordered stop pattern(s) with planned times,
  keeping variants (the pattern changed during 2026). A `TrainNight` is train number + service date
  + ordered stops with planned and actual times and delay.
- Times are timezone-aware; runs cross midnight.

### 3. Route inference, Germany (`nightdesk/route_de.py`)
- Build a graph from the sections (nodes = STEL_ID, edges = sections with line number, km range,
  length, speed).
- Map each ES stop in Germany to a Betriebsstelle. Prefer an exact, checkable key; say in the report
  which key you used and how many stops resolved.
- Between consecutive stops take the fastest path (length / speed) on lines open to passenger
  trains. Result: ordered list of (line number, km from, km to, section ids) with an estimated pass
  time interpolated between the planned times of the two stops.
- This is an INFERRED route, not the booked path. Mark it so in every output, and support a YAML
  override per train (`routes/*.yaml`: force or forbid line numbers between two stops), because ES
  will know the real path and we will not.
- Border stretches (first/last German stop to the border) must be covered too.

### 4. Matching (`nightdesk/match.py`)
- Germany: a work matches a train-night when (a) one of its `streckennummern` is on the route,
  (b) its location overlaps the route's km range on that line, resolving `ril100Von/Bis` to km via
  the Betriebsstellen layer, falling back to distance from `koordinaten` to the route geometry,
  (c) a `gueltigkeiten` entry (dates, weekdays, hours; hours may wrap midnight) overlaps the
  estimated pass window, with a tolerance parameter (default +-60 min; later, widen by the train's
  delay distribution).
- Confidence: `high` (line + km + time), `medium` (line + time, location by coordinates only),
  `low` (line + date only). Never drop a row silently: keep a `reason`.
- Belgium: match TCR rows on line number + date/time against the lines the train uses according to
  Infrabel punctuality rows; ptcar range if resolvable.
- Output one table `matches.parquet`: train, service date, country, work id, source, line, km range,
  work kind/impact, time overlap, confidence, reason, snapshot date.

### 5. Snapshot diff (`nightdesk/diff.py`)
- Compare two snapshots: works added, removed, or changed (dates, hours, effect, location), limited
  to those that match an ES train-night. Stable, explainable output.

### 6. Backtest (`nightdesk/backtest.py`, CLI `nightdesk backtest`)
Question: do train-nights with matched works collect more delay inside Germany / Belgium than
train-nights without?
- Period: 1-13 November 2026 against the 14 Nov snapshot (only works still open on 14 Nov exist, so
  short works that ended earlier are missing: state this bias in the report). If the monthly data
  and long-running works allow anything for October, add it and say how thin it is.
- Outcome per train-night and per leg between consecutive stops: delay gained (delay at leg end
  minus delay at leg start). Exposure: matched works on that leg, by effect and confidence.
- Report counts, medians, a permutation or Mann-Whitney test, and the per-leg table. With this
  sample the honest answer may be "no detectable signal" or "too few nights": write exactly what the
  numbers support, no more.
- Also check the known case: ES 453 on 2026-10-05 (diverted, about +296 min at Praha): what does the
  data show for that night?
- Write `.handoff/backtest.md` with the numbers and the commands that produced them.

### 7. CLI and tests
`uv run nightdesk fetch ...`, `route <train>`, `match --from <date> --to <date>`,
`diff <snapA> <snapB>`, `backtest`.
`uv run pytest` green and offline: validity-window logic (weekdays, midnight wrap), km overlap,
route override, diff kinds, one end-to-end match on a real fixture.

## Done means
- All commands above run; tests green.
- `.handoff/build-phaseA.md`: what works, what is stubbed, commands run with exit codes, every
  number you report and where it came from, and anything you could not verify.
- Update `.handoff/state.md` and `.handoff/sources.md` (evidence rule). Commit locally.
- Final reply: under 25 lines. Stop resolution counts, route sanity (which lines for each train),
  match counts by confidence, backtest result, open problems.
