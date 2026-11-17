"""RunRow -> dated ordered runs and segments, with no invented path lines."""

from collections import defaultdict
from datetime import datetime, timezone

from nightdesk.config import STATION_AREA_LINE_PREFIXES, DATASET_ASSUMPTIONS
from nightdesk.model import RunPoint, RunRow, TrainRun, Segment
from nightdesk.timeutil import utc, pass_window


def line_for_matching(value: str | None) -> str | None:
    if value is None:
        return None
    local = value.partition(":")[2]
    if local.startswith(STATION_AREA_LINE_PREFIXES):
        return None
    return value


def build_runs(rows: list[RunRow], *, kind: str | None = None) -> list[TrainRun]:
    groups = defaultdict(list)
    for row in rows:
        # Different captures/sources are different observations, never merged.
        groups[(row.source.bundle, row.source.dataset, row.source.capture_id, row.service_date, row.train_no)].append(row)
    runs = []
    for (_, dataset, _, service_date, train_no), points in sorted(groups.items()):
        point_order = lambda p: (utc(p.planned_dep or p.planned_arr)
                                  if p.planned_dep or p.planned_arr else datetime.max.replace(tzinfo=timezone.utc))
        ordered = sorted(points, key=point_order)
        unresolved = {}
        missing = [p.point_id for p in ordered if p.planned_dep is None and p.planned_arr is None]
        if missing:
            unresolved["point_order"] = {"reason": "missing_planned_time", "points": missing}
        if len({p.kind for p in ordered}) != 1 or len({p.trip_id for p in ordered}) != 1:
            raise ValueError("mixed_run_kinds_or_trip_ids")
        canonical = [RunPoint.model_validate(p.model_dump(exclude={"service_date", "train_no", "kind", "trip_id"})) for p in ordered]
        runs.append(TrainRun(service_date=service_date, train_no=train_no, kind=kind or ordered[0].kind,
                             trip_id=ordered[0].trip_id, points=canonical,
                             input_refs=[p.source for p in ordered],
                             extra={"assumptions": DATASET_ASSUMPTIONS.get(dataset, [])}, unresolved=unresolved,
                             path_unresolved=not any(line_for_matching(p.line_dep) or line_for_matching(p.line_arr) for p in ordered)))
    return runs


def segments(run: TrainRun) -> list[Segment]:
    out = []
    for a, b in zip(run.points, run.points[1:]):
        window = pass_window(a, b)
        duration = None
        if window.intervals:
            start, end = window.intervals[0]
            seconds = (end - start).total_seconds()
            if seconds.is_integer():
                duration = int(seconds)
        # A station-area code is not a line. Fall back only to the arrival at b.
        line = line_for_matching(a.line_dep) or line_for_matching(b.line_arr)
        out.append(Segment(a=a, b=b, line=line, planned_s=duration,
                           input_refs=[p.source for p in (a, b) if p.source is not None]))
    return out
