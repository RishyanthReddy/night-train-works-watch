**CHANGES REQUESTED — 8/10.** Two reproducible Phase 0 correctness issues:

1. **P2 — Missing times violate C4.** [mapping.py:315](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/mapping.py:315), particularly line 327. With CSV `id,at\na,\n`, map `at` using `datetime:%Y-%m-%d %H:%M`, declare `Europe/Brussels`, and require `[id, at]`. After confirmation, ingest exits **0** but reports `accepted=0 rejected=1`; rejects reports `field=at reason=required_missing`. C4 requires missing times to remain unresolved without rejecting the record. Making `at` optional accepts it but leaves `unresolved={}`, losing the required raw value/reason. Handle missing temporal values through the unresolved path.

2. **P2 — JSON normalization hides field-presence changes.** [table.py:224](/Users/rishyanthreddy/.t3/scratch/2026-11-14-i-regsitered-for-this-hackathon-db1ef81a/src/nightdesk/intake/table.py:224). Compare old `[{"id":"a"},{"id":"b","note":"keep"}]` with new `[{"id":"a","note":null},{"id":"b","note":"keep"}]` using `nightdesk compare old.json new.json --key id`. It exits **0**, reporting `changed=0 unchanged=2`. Padding absent keys with `None` erases the change and fabricates fields in retained source content/`extra`. Preserve each JSON record’s original keys; use missing-aware lookup for profiling.

Independent checks executed:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/nightdesk-review-sol-pytest' uv run --offline pytest -q
```

Exit **0**: **171 passed**.

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --offline python tests/phase0_acceptance.py
```

Exit **0**: six acceptance steps passed, including OS network denial. Actual comparison: `changed=2 added=1 unchanged=2 only_in_old=0`. Pre-confirm refusal exited **1**, as expected.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS='-p no:cacheprovider --basetemp=/tmp/nightdesk-review-sol-offline-pytest' /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' /usr/bin/env -u MISTRAL_API_KEY -u NS_API_KEY -u SWISS_OTD_TOKEN -u DB_CLIENT_ID -u DB_API_KEY -u TRAIN_ARCHIVE_TOKEN uv run --offline pytest -q
```

Exit **0**: **171 passed**.

All **28 snapshot hashes matched**. Review used code and synthetic temporary inputs only; no source or handoff edits, delegation, commit, or push. P0.9 and Phase 1+ excluded.
