# Nightdesk offline demo

Run the setup in a clean local checkout on macOS. It uses the named `demo` bundle and the project's hashed demo manifest. The demo launcher locks the app to that bundle. Disconnect external networking for the presentation and keep loopback available for Streamlit.

```sh
uv sync --frozen --offline
for scenario in v1 v2 syn_bad; do
  fixture="tests/fixtures/syn/$scenario/capture.yaml"
  uv run --offline nightdesk capture confirm "$fixture" --bundle demo --actor "Demo reviewer"
  uv run --offline nightdesk capture import "$fixture" --bundle demo
done
uv run --offline nightdesk mapping confirm mappings/infrabel_punctuality.yaml --bundle demo --actor "Demo reviewer"
uv run --offline nightdesk ingest tests/fixtures/runs/cc0_2026.csv --mapping mappings/infrabel_punctuality.yaml --bundle demo
uv run --offline nightdesk demo check --bundle demo
uv run --offline nightdesk audit seal --bundle demo
mkdir -p data/out/demo/audit-copies
cp data/out/demo/audit.jsonl data/out/demo/audit-copies/before-demo.jsonl
```

Record the printed hash and count separately before editing any audit copy. The preflight checks both the saved copy and the current audit against those values. Run it from the checkout root before opening the app. If you intentionally change the demo bundle during setup, verify the change and take a new copy and seal before rerunning preflight.

```sh
sh scripts/demo_preflight.sh data/out/demo/audit-copies/before-demo.jsonl '<saved hash>' '<saved count>'
uv run --offline nightdesk demo serve
```

### Five-minute walkthrough

1. **Real run.** Select the `cc0_2026.csv` run capture, open **Run evidence**, and select **be:400 / 2026-10-01**. At Hergenrath, show **09:05:00 scheduled** and **09:59:40 observed**. Open **Capture provenance** to show Infrabel, CC0 and partial coverage. This is an observation at a selected Belgian point on one service. [Source file from Infrabel](https://fr.ftp.opendatasoft.com/infrabel/PunctualityHistory/Data_raw_punctuality_202610.csv)
2. **Review queue.** Clear the optional run selection to keep the examples separate. Select **Synthetic v1** before and **Synthetic v2** after. Select **syn-journey**, enter `syn:border1,syn:border2` in the boundary points field, and confirm those identities. Open **aa:101 / 2026-11-17**. The adjacent detail shows the changed exit time, scoped boundary check, works evidence and unresolved items.
3. **Local review.** Show the delay request returning `prediction_not_validated`. Open **Capture provenance**, record a local decision and export the dossier. The synthetic pair demonstrates the workflow when dated path revisions and reviewed links are available.
4. **Rejects.** In **Rejects and audit**, show `invalid_work_dates` from the deliberately malformed capture. In the sidebar’s **Text notice** section, select `injected.json` under **Public synthetic replay**, click **Replay checked notice**, and show `text_addresses_model`.
5. **CO₂ scenario.** Open **CO₂ scenario**, change the alternative from car to long-distance coach, and show the changed result, the assumption controls and the 2024 source.
6. **Audit.** In **Rejects and audit**, type `data/out/demo/audit-copies/before-demo.jsonl` into **Audit copy file**. Enter the saved hash and count and click **Verify audit chain**. Make a separate truncated copy with the command below, replace the file field with `data/out/demo/audit-copies/tail-cut.jsonl`, and verify again with the same hash and count. Expect `external_seal_or_count_mismatch`.

```sh
sed '$d' data/out/demo/audit-copies/before-demo.jsonl > data/out/demo/audit-copies/tail-cut.jsonl
```

The [fallback recording](nightdesk-demo.mp4) shows the local demo screens and can be played offline. For a private rehearsal using saved provider captures, use the practice workflow in [Real data in Nightdesk](REAL_DATA.md).
