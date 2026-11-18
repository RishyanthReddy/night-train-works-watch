# Phase3 German rolling-window rehearsal (local practice only)

Authorised by the user2026-11-18 before Phase3 closes. No network, new dependency,
fetcher or German production adapter. Restricted/unknown-licence source JSON stays
under data/snapshots/de; never committed, copied to the public demo or sent to a reviewer.

Recheck: phase3-german-recheck.log records source file SHA256 values and aggregate
counts only.17→18:44,952 shared full records equal;776 only old,456 only new. Both
manifests complete=false; works version2026-11-16T13:16:21.432552 unchanged. The old
row ends fall on17/18Nov; entering starts on9/10Feb.14→17:3,496 absent;199 have an
envelope end after18Nov. This does not make those199 proven removals.

Rule changes-v2:
- Old-only works: every stated overall/individual validity end must precede the
  newer capture instant for expired_out_of_window. Canonical dates are inclusive;
  absent end clocks keep the entire final date. Later or unresolved periods block
  an expiry conclusion. Missing/invalid zone or time stays membership_unknown. Canonical/raw date conflicts also stay unknown; matching date projections still permit precise raw clocks.
- New-only works: every stated start at/after the older capture's forward edge
  gives entering_window. The previous edge is used because these rows were outside
  the earlier export. Elapsed hours use UTC. No declaration means no inferred edge.
- The window is explicit canonical Capture.filter evidence (the saved rolling
  filter), or an explicit rolling_window_hours comparison selection, recorded as
  such in evidence/audit. Mapping.filter is a row-selection predicate and is not
  repurposed into metadata. No public adapter/ingest contract is changed.
- R2 completeness/source/filter rules still gate added/removed. These partial
  captures cannot conclude either. Expiry may still be described across a changed
  or unknown filter; entering-window attribution cannot. No publication,
  cancellation, withdrawal or newly announced work is inferred.
- Unknown window/validity is a note: if R2 passes, its source row remains in added/removed. Only proved expired_out_of_window/entering_window exclusions leave those lists. An explicit hours choice may fill absent policy only; differing retained window declarations give rolling_window_conflict.
- Every one-sided work remains source-linked in membership_changes with its
  classification/reason. Dossier JSON/Markdown and append-once comparison audit
  retain the excluded rows; source files and immutable revisions are unchanged.

Tests: authored minimal tests/fixtures/window-membership.json plus mandatory
synthetic edge/inclusive/multiple-period/malformed-zone/filter/export/audit cases.
Optional on-disk regression reads minimal dates/ids in memory, licence UNKNOWN,
no descriptions/locations retained; asserts776 expired/456 entering and no
added/removed. The local test explicitly declares Europe/Berlin for naive source
clocks, not a claim that the feed declares it. The14th has no manifest or proved
capture instant/filter; no forward edge is invented for it. A known later instant
is only an analytical reference, while R2 refuses the unknown/mismatched filter.
The199 long-validity absences must never enter the expired group.

Builder run outcomes are in phase3-*-tests.log; use the latest successful log,
not earlier failed fixture/cleanup runs. Council/commit still pending.
