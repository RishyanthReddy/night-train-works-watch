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

Record the printed hash and count separately before editing any audit copy. Run the preflight from the checkout root with the recorded values, then open the local URL printed by Streamlit.

```sh
sh scripts/demo_preflight.sh data/out/demo/audit-copies/before-demo.jsonl '<saved hash>' '<saved count>'
uv run --offline nightdesk demo serve
```

### Five-minute walkthrough

1. **Queue.** Select **Synthetic v1** before and **Synthetic v2** after. Select **syn-journey**, enter `syn:border1,syn:border2` in the boundary points field, and confirm those identities. Open **aa:101 / 2026-11-17**.
2. **Dossier.** Open the **Dossier** tab. Point out capture provenance, the changed exit time, works grades A and B, the separate unlocated work, and `boundary_instants_differ`. Show the delay request returning `prediction_not_validated` without a delay estimate. Record a local decision and export the dossier.
3. **Rejects.** In **Rejects and audit**, show `invalid_work_dates` from the deliberately malformed capture. In **Text notice**, select `injected.json` under **Public synthetic replay** and click **Replay checked notice**. Show `text_addresses_model`.
4. **Real run.** Select the `cc0_2026.csv` run capture, open **Run evidence**, and select **be:400 / 2026-10-01**. The CC0 Infrabel excerpt shows an observed Hergenrath departure at 09:59:40 against 09:05:00 planned. This separate capture supplies observed point times for one train in Belgium.
5. **Audit.** Verify the intact copy using the saved hash and count. Make a separate truncated copy with the command below. In **Rejects and audit**, select that copy, enter the same hash and count, and verify again. Expect `external_seal_or_count_mismatch`.

```sh
sed '$d' data/out/demo/audit-copies/before-demo.jsonl > data/out/demo/audit-copies/tail-cut.jsonl
```

The comparison and decisions use synthetic fixtures. The observed-run example uses a hashed CC0 fixture. For a private rehearsal with broader coverage, use the practice workflow in [Real data in Nightdesk](REAL_DATA.md).
