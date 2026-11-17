"""Rail date/clock rules. All interval arithmetic uses UTC, with half-open ends.

Periodical weekdays describe the local date a window starts. That convention is
an explicit assumption until a source documents another one.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
TIME_RULE_VERSION = "time-v1"


@dataclass(frozen=True)
class LocalTime:
    at: datetime | None
    raw: str
    timezone: str | None
    reason: str | None


@dataclass(frozen=True)
class Windows:
    intervals: tuple[tuple[datetime, datetime], ...] = ()
    reason: str | None = None
    assumptions: tuple[str, ...] = ()


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone_required")
    return value.astimezone(UTC)


def localize(value: datetime | None, zone: str | None, raw: str = "") -> LocalTime:
    if value is None:
        return LocalTime(None, raw, zone, "missing_time")
    if not zone:
        return LocalTime(None, raw or value.isoformat(), zone, "timezone_unknown")
    tz = ZoneInfo(zone)
    if value.tzinfo is not None and value.utcoffset() is not None:
        # An explicit offset identifies an instant; preserve it.
        return LocalTime(value, raw or value.isoformat(), zone, None)
    a, b = (value.replace(tzinfo=tz, fold=fold) for fold in (0, 1))
    valid = [v for v in (a, b) if utc(v).astimezone(tz).replace(tzinfo=None) == value]
    if not valid or (len(valid) == 2 and valid[0].utcoffset() != valid[1].utcoffset()):
        return LocalTime(None, raw or value.isoformat(), zone, "ambiguous_local_time")
    return LocalTime(valid[0], raw or value.isoformat(), zone, None)


def parse_datetime(raw: str | None, fmt: str, zone: str | None) -> LocalTime:
    if raw is None or not raw.strip():
        return localize(None, zone, raw or "")
    try:
        value = datetime.strptime(raw, fmt)
    except ValueError:
        raise ValueError("invalid_datetime") from None
    return localize(value, zone, raw)


def parse_date(raw: str, fmt: str) -> date:
    try:
        return datetime.strptime(raw, fmt).date()
    except ValueError:
        raise ValueError("invalid_date") from None


def parse_clock(raw: str, fmt: str = "%H:%M") -> time:
    try:
        return datetime.strptime(raw, fmt).time()
    except ValueError:
        raise ValueError("invalid_time") from None


def overlap(a: tuple[datetime, datetime], b: tuple[datetime, datetime]):
    start, end = max(utc(a[0]), utc(b[0])), min(utc(a[1]), utc(b[1]))
    return (start, end) if start < end else None


def pass_window(a, b) -> Windows:
    """Objects supply planned_dep/planned_arr. Missing or reversed spans stay unknown."""
    start = a.planned_dep or a.planned_arr
    end = b.planned_arr or b.planned_dep
    if start is None or end is None:
        return Windows(reason="no_pass_window")
    try:
        start, end = utc(start), utc(end)
    except ValueError:
        return Windows(reason="no_pass_window")
    if start >= end:
        return Windows(reason="no_pass_window")
    return Windows(((start, end),))


def work_windows(*, date_start: date, date_end: date, clock_from: time | None,
                 clock_to: time | None, weekdays: list[int] | tuple[int, ...] | None,
                 recurrence: str, zone: str | None,
                 during: tuple[datetime, datetime]) -> Windows:
    """Return windows relevant to one planned pass; never expand years of days.

    date_end is an inclusive calendar date. A wrapping window is clipped at the
    midnight after date_end; the weekday belongs to its start date.
    """
    if date_end < date_start:
        raise ValueError("invalid_date_range")
    if recurrence not in {"periodical", "continuous"}:
        return Windows(reason="recurrence_unknown")
    if not zone:
        return Windows(reason="timezone_unknown")
    if clock_from is None or clock_to is None:
        return Windows(reason="missing_work_clock")
    if recurrence == "periodical" and not weekdays:
        return Windows(reason="weekdays_unknown")
    if weekdays is not None and any(type(d) is not int or d not in range(1, 8) for d in weekdays):
        raise ValueError("invalid_weekdays")
    tz = ZoneInfo(zone)
    span = (utc(during[0]), utc(during[1]))
    if span[0] >= span[1]:
        return Windows(reason="no_pass_window")
    lower = localize(datetime.combine(date_start, time.min), zone)
    upper = localize(datetime.combine(date_end + timedelta(days=1), time.min), zone)
    if lower.at is None or upper.at is None:
        return Windows(reason="ambiguous_local_time")
    bounds = (utc(lower.at), utc(upper.at))
    if overlap(span, bounds) is None:
        return Windows()
    if recurrence == "continuous":
        starts = [(datetime.combine(date_start, clock_from), datetime.combine(date_end, clock_to))]
        assumptions = ()
    else:
        lo = max(date_start, span[0].astimezone(tz).date() - timedelta(days=1))
        hi = min(date_end, span[1].astimezone(tz).date())
        starts = []
        while lo <= hi:
            if lo.isoweekday() in weekdays:
                end_date = lo + timedelta(days=1) if clock_to < clock_from else lo
                starts.append((datetime.combine(lo, clock_from), datetime.combine(end_date, clock_to)))
            lo += timedelta(days=1)
        assumptions = ("weekday_is_local_window_start; inclusive_date_end",)
    out = []
    for start, end in starts:
        a, b = localize(start, zone), localize(end, zone)
        if a.at is None or b.at is None:
            return Windows(reason="ambiguous_local_time", assumptions=assumptions)
        if utc(a.at) > utc(b.at):
            raise ValueError("invalid_continuous_window")
        clipped = overlap((a.at, b.at), bounds)
        if clipped is not None and overlap(clipped, span) is not None:
            out.append(clipped)
    return Windows(tuple(out), assumptions=assumptions)
