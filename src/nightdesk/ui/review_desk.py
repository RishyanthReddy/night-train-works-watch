"""Presentation for the review desk. All findings come from existing reports."""

from datetime import datetime
from html import escape
import json

import streamlit as st


STYLE = """
<style>
.st-key-nightdesk_brand, .st-key-nightdesk_queue, .nd-times {
    --nd-ink: #202c25;
    --nd-quiet: #4f6055;
    --nd-green: #235b3e;
    color: var(--nd-ink);
    color-scheme: light;
}
.st-key-nightdesk_brand {
    background: #f2f4ee;
    border: 1px solid #dce1d8;
    border-radius: 12px;
    padding: .65rem .9rem;
}
.nd-brand { display: flex; align-items: center; gap: .65rem; flex-wrap: wrap; }
.nd-brand strong { font-size: 1.5rem; letter-spacing: -.045em; }
.nd-brand small { color: var(--nd-quiet); font-size: .88rem; }
main [data-baseweb="tab"][aria-selected="true"] { color: #235b3e; }
main [data-baseweb="tab-highlight"] { background-color: #235b3e; }
.nd-mark { display: inline-block; width: 30px; height: 30px; border-radius: 9px;
    background: #235b3e; position: relative; }
.nd-mark::before { content: ""; position: absolute; inset: 6px 10px;
    border-inline: 2px solid #fff; transform: skew(-19deg);
    background: repeating-linear-gradient(0deg,transparent 0 4px,#fff 4px 5px); }
.st-key-nightdesk_queue { background: #f2f4ee; border: 1px solid #dce1d8;
    border-radius: 12px; padding: 1rem; min-width: 0; }
.st-key-nightdesk_queue :is(h2, h3, p) { color: #202c25; }
.st-key-nightdesk_queue :is(h3, p) { margin-bottom: .25rem; }
.nd-times { padding: 1rem clamp(.9rem, 2.5vw, 2rem); border: 1px solid #d7e3d0;
    border-radius: 14px; background: linear-gradient(115deg, #f5f8ee, #edf4e7); }
.nd-times h3 { padding: 0; margin: 0 0 .7rem; font-size: 1rem; color: #365740; }
.nd-times dl { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: center; gap: .65rem; margin: 0; }
.nd-times dt, .nd-times p { font-size: .88rem; color: var(--nd-quiet); }
.nd-times dd { font-size: clamp(1.65rem, 4.2vw, 3rem); letter-spacing: -.055em;
    font-variant-numeric: tabular-nums; font-weight: 760; line-height: 1.12;
    margin: .15rem 0 0; overflow-wrap: anywhere; }
.nd-times .nd-after dd { color: var(--nd-green); }
.nd-times .nd-value-text { font-size: clamp(1rem, 2vw, 1.45rem); letter-spacing: -.025em; }
.nd-times p { margin: .7rem 0 0; }
@media(max-width: 380px) {
    .nd-times dl { gap: .35rem; }
    .nd-times dd { font-size: 1.42rem; }
}
</style>
"""

FIELD_LABELS = {
    "entry.at": "Entry time", "entry.raw_time": "Entry time as supplied", "entry.point_id": "Entry point",
    "exit.at": "Exit time", "exit.raw_time": "Exit time as supplied", "exit.point_id": "Exit point",
    "operating_dates": "Operating dates", "status": "Source status", "source_status": "Source status",
    "source_presence": "Record presence",
}
CHANGE_LABELS = {
    "checks_changed": "Evidence checks changed",
    "source_record_added": "Record present only in the after capture",
    "source_record_removed": "Record present only in the before capture",
    "record_presence_unknown": "Record missing, operating status unknown",
    "multiple_source_leg_changes": "Multiple source records changed",
}
REVIEW_LABELS = {
    "not_reviewed_locally": "Awaiting review", "needs_clarification": "Needs clarification",
    "accepted_locally": "Accepted locally", "rejected_locally": "Rejected locally",
    "mixed_source_leg_reviews": "Different reviews by source record",
}
REASON_LABELS = {
    "boundary_instants_differ": "Boundary times differ",
    "operating_dates_differ": "Operating dates differ",
    "different_boundary_points": "The two records name different boundary points",
    "different_event_kinds": "The two records describe different events",
    "boundary_point_not_reviewed": "Boundary point identity needs review",
    "incomplete_capture": "At least one capture is partial",
    "filter_mismatch": "The captures cover different filters",
    "unlinked": "No reviewed journey link selected",
    "ambiguous_boundary_leg": "More than one source record could fit",
    "boundary_leg_not_selected": "The adjacent source record was not selected",
    "adjacent_leg_not_observed": "The adjacent source record is missing",
    "missing_time": "The source time is missing",
    "no_run_selected": "No run selected",
    "no_scheduled_or_observed_run_selected": "No run selected",
    "run_selection_required": "Choose the source run to use",
    "border_not_checked": "Boundary could not be checked",
    "not_declared_complete": "Source did not declare complete coverage",
    "expired_out_of_window": "Left the rolling window after expiry",
    "entering_window": "Entered the rolling window",
    "leg_not_observed_in_selected_capture; operational_meaning_unknown": "Record missing, operating status unknown",
}


def label(value):
    return value.replace("_", " ").replace(".", " ")


def reason_label(reason):
    return REASON_LABELS.get(reason, label(reason))


def review_label(review):
    disposition, _, stale = review.partition(" (stale)")
    return "Review needs updating" if stale else REVIEW_LABELS.get(disposition, label(disposition))


def queue_summary(row):
    kind = row["change_kind"]
    if kind in CHANGE_LABELS:
        return CHANGE_LABELS[kind]
    changed = row["changed_fields"]
    fields = ", ".join(dict.fromkeys(FIELD_LABELS.get(field, label(field)) for field in changed
                                     if not (field.endswith(".raw_time") and field.replace(".raw_time", ".at") in changed)))
    return fields + " changed" if fields else "Source record changed"


def render_brand(workspace):
    st.html(STYLE)
    with st.container(key="nightdesk_brand"):
        st.html(
            '<div class="nd-brand"><span class="nd-mark" aria-hidden="true"></span>'
            f'<strong>Nightdesk</strong><small>{escape(workspace)}</small></div>'
        )


def time_value(value, *, show_seconds=False, display_zone=None):
    """Render the recorded instant and its date and offset."""
    if not value:
        return "Time unavailable", ""
    observed = datetime.fromisoformat(value)
    if display_zone is not None:
        observed = observed.astimezone(display_zone)
    clock = observed.time().isoformat(timespec="microseconds" if observed.microsecond else
                                     "seconds" if show_seconds or observed.second else "minutes")
    offset = observed.strftime("%z")
    scope = observed.date().isoformat() + (f" · UTC{offset[:3]}:{offset[3:]}" if offset else " · Offset unknown")
    return clock, scope


def comparison_panel(title, before, after, *, labels=("Before", "After"), note="", transition=True):
    def cell(name, value):
        text, context = value
        kind = "" if text[:1].isdigit() else ' class="nd-value-text"'
        detail = f"<dt>{escape(context)}</dt>" if context else ""
        return f"<dt>{escape(name)}</dt><dd{kind}>{escape(text)}</dd>{detail}"
    st.html(
        f'<section class="nd-times"><h3>{escape(title)}</h3><dl>'
        f'<div>{cell(labels[0], before)}</div><span aria-hidden="true">{"→" if transition else "·"}</span>'
        f'<div class="{"nd-after" if transition else ""}">{cell(labels[1], after)}</div></dl>'
        + (f"<p>{escape(note)}</p>" if note else "") + "</section>"
    )


def _field_value(change, side):
    if not change[f"{side}_present"]:
        return "Field missing", ""
    value = change[side]
    if change["field"].endswith(".at") and isinstance(value, str):
        return time_value(value)
    if value is None:
        return "Value unknown", ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value), ""
    return str(value) if not isinstance(value, dict) else json.dumps(value, ensure_ascii=False), ""


def render_change(report):
    diffs = report["changes"]["field_diffs"]
    if report["before"] is None or report["after"] is None:
        comparison_panel(
            "Source record presence",
            ("Record present" if report["before"] else "Record missing", ""),
            ("Record present" if report["after"] else "Record missing", ""),
            note="Operating status cannot be inferred from a missing source record.",
        )
        for side in ("before", "after"):
            if report[side] is None:
                st.info(f"Source record not observed in the selected {side} capture. Operating status is unknown.")
    elif diffs:
        primary = next((item for item in diffs if item["field"] in ("exit.at", "entry.at")), diffs[0])
        field = primary["field"]
        comparison_panel(FIELD_LABELS.get(field, label(field)), _field_value(primary, "old"), _field_value(primary, "new"))
        if field in ("exit.at", "entry.at"):
            for side in ("before", "after"):
                payload = report[side]["payload"]
                event = payload.get(field.split(".")[0])
                if event and event["at"] and len(payload["operating_dates"]) > 1:
                    st.warning(f"{side.title()} source lists several service dates with one timestamp dated "
                               f"{datetime.fromisoformat(event['at']).date()}. Its applicability to individual "
                               "service dates is unverified.")
    else:
        st.info("Evidence checks changed. The source fields shown here have no recorded differences.")
    if diffs:
        with st.expander("All changed fields"):
            st.dataframe([{"Field": FIELD_LABELS.get(item["field"], label(item["field"])),
                           "Before": " · ".join(filter(None, _field_value(item, "old"))),
                           "After": " · ".join(filter(None, _field_value(item, "new")))}
                          for item in diffs], hide_index=True)


def render_boundary_clocks(report, finding):
    detail = finding["detail"]
    sources = finding["input_refs"][:2]
    if not detail.get("left_at") or not detail.get("right_at"):
        return
    display_zone = None
    after = report["after"]
    if after:
        for source, event_kind in zip(sources, ("exit", "entry")):
            event = after["payload"].get(event_kind)
            if source == after["source"] and event and event["at"]:
                display_zone = datetime.fromisoformat(event["at"]).tzinfo
                break
    comparison_panel(
        "Reviewed point · " + detail["point_id"],
        time_value(detail["left_at"], display_zone=display_zone),
        time_value(detail["right_at"], display_zone=display_zone),
        labels=("Exit", "Entry"), transition=False,
        note=("Both instants shown in this train’s source offset." if display_zone else "Both instants shown in UTC."),
    )
