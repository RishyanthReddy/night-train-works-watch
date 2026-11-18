CC0 subset of the saved deryclem/european-sleeper-gtfs feed, not an official
booked path. Selection, source ZIP hash and per-file hashes/counts: manifest.json.
The upstream README licences the feed and station data CC0:
https://github.com/deryclem/european-sleeper-gtfs#license

The adapter reads these as scheduled times only. Its point namespace is explicit;
it does not guess correspondence to national point ids, actual times or lines.
The path is unresolved, so works exposure is capped at B. GTFS service days can
extend beyond24hours. Time is elapsed from local agency-timezone noon minus12h,
including on clock-change days, as defined by the GTFS Time type:
https://gtfs.org/documentation/schedule/reference/#field-types

Fixtures are not modified to simulate operational changes. Exception/removal,
malformed-time and clock-change tests create separate authored synthetic copies.
