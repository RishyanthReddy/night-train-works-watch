# Synthetic admin practice fixtures

All rows are authored synthetic examples, not European Sleeper events.

- `admin_v1.csv`: four rows (`syn-001` through `syn-004`).
- `admin_v2.csv`: two changed rows, two unchanged, one added, one broken.
  `syn-001` changes owner; `syn-002` changes duration and state;
  `syn-003` and `syn-004` stay the same; `syn-005` is added;
  `syn-006` has the invalid seconds value `broken` and must be rejected.
- `admin_alt.csv`: exactly v1's canonical field values with renamed/reordered
  columns, abbreviated states and minutes instead of seconds.

The mapping retains `note` in `extra`. Every row has its own source reference.
The selected-table comparison must show 2 changed, 1 added, 2 unchanged and
0 only-in-old rows. These counts describe synthetic selected-file differences;
they do not establish operational removals, cancellations or withdrawals.

Use `mappings/admin_v1.yaml` for v1/v2 and `mappings/admin_alt.yaml` for alt.
Confirm each mapping's current hash in the chosen bundle before ingesting.
