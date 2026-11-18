# Infrabel D-1 capture

Fetch the public Infrabel daily punctuality rows for European Sleeper into a practice or test bundle.

```sh
nightdesk fetch-infrabel --bundle practice
nightdesk mapping confirm mappings/infrabel_d1.yaml --bundle practice --actor "Your name"
nightdesk ingest <capture-path-printed-by-fetch> --mapping mappings/infrabel_d1.yaml --bundle practice
```

Only the fetch command uses the network. Keep the capture directory for offline use. The manifest records request URLs, fetch times and SHA-256 hashes of the raw pages and
the intake file. In the Nightdesk sidebar, choose the imported capture under **Run capture
(optional)** together with path revisions for the same train and service date. The selected run
in the dossier includes planned and observed times, source URLs and page fetch times.

The D-1 records include point names and line numbers. Point labels are scoped to the D-1 feed
because it does not supply PTCAR numbers. The mapping interprets local times as Europe/Brussels.
Captures remain marked incomplete for operational comparisons. A run is punctuality evidence
for the listed service date. Path revisions are separate inputs.
