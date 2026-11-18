# Nightdesk day-of runbook

Work from a local checkout. Keep the verified public demo ready while you review a partner brief or private files.

## 1. Define the task

Ask the rail operator to show one change from receipt to decision. Record the manual step they want to replace, the authoritative source, whether each export is complete, and who can approve a change. For a cross-border journey, ask which source IDs, service dates and boundary events they have verified. Agree on what may be included in a local export or shown to other people.

## 2. Import private files locally

Put private source files below `data/es/`. Inspect each file and use a mapping you have reviewed with the data owner. Commands below show the sequence for an example file and mapping.

```sh
uv sync --frozen --offline
uv run --offline nightdesk sniff data/es/paths.csv
uv run --offline nightdesk mapping confirm mappings/es_paths.yaml --bundle es --actor "Local reviewer"
uv run --offline nightdesk ingest data/es/paths.csv --mapping mappings/es_paths.yaml --bundle es
```

Inspect rejected rows and capture coverage before comparing. Repeat confirm and import for the other revision. For existing API snapshots, select the appropriate local practice bundle and existing captures. The sources, provider-specific constraints and saved-source workflow are documented in [Real data in Nightdesk](REAL_DATA.md).

## 3. Show the relevant view

```sh
NIGHTDESK_BUNDLE=es uv run --offline streamlit run src/nightdesk/ui/app.py \
  --server.address=127.0.0.1 --server.headless=true --browser.gatherUsageStats=false
```

- **Path revision.** Select the before and after captures. Open a train and date. Use a journey link or boundary point only when reviewed. Read the timing difference or the reason a check is unavailable.
- **Works.** Choose the works capture and open **Works evidence**. Compare it with a compatible earlier capture where one exists. Check capture-window findings and partial scope.
- **Running times.** Choose a run capture and open **Run evidence**. Read scheduled, published or observed labels, then open capture provenance.
- **Other tabular records.** Confirm the identity key with the operator. Compare two files locally with `uv run --offline nightdesk compare <before> <after> --key <column> --bundle es`.

Record a local decision, add an owner and question if useful, and export the Markdown and JSON dossier inside the same bundle. When a source cannot substantiate a change or estimated delay, show the reason in the app.

## 4. Run the public demo

Use the separate verified `demo` bundle and its manifest. Follow the clean setup, seal and preflight steps in [Nightdesk offline demo](DEMO.md). Lead with the real CC0 Infrabel observation. If the app is unavailable, play [the fallback recording](nightdesk-demo.mp4) locally. Keep private source files and bundles out of the public walkthrough.
