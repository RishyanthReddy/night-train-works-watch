"""Presentation for the review desk. Every number shown comes from a report."""

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
    "entry.at": "Entering time", "entry.raw_time": "Entering time as supplied",
    "entry.point_id": "Entering point",
    "exit.at": "Leaving time", "exit.raw_time": "Leaving time as supplied",
    "exit.point_id": "Leaving point",
    "operating_dates": "Dates this train runs", "status": "Status in this file",
    "source_status": "Status in this file",
    "source_presence": "Listed in the file",
}
CHANGE_LABELS = {
    "checks_changed": "The checks gave a different answer",
    "source_record_added": "Appears only in the later file",
    "source_record_removed": "Appears only in the earlier file",
    "record_presence_unknown": "No longer listed — we cannot tell if it still runs",
    "multiple_source_leg_changes": "More than one record for this train changed",
}
REVIEW_LABELS = {
    "not_reviewed_locally": "Waiting for review", "needs_clarification": "Needs an answer",
    "accepted_locally": "Accepted by us", "rejected_locally": "Rejected by us",
    "mixed_source_leg_reviews": "Records for this train have different decisions",
}
REASON_LABELS = {
    "boundary_instants_differ": "The two sides give different handover times",
    "operating_dates_differ": "The two sides list different dates this train runs",
    "different_boundary_points": "The two records name different handover points",
    "different_event_kinds": "The two records describe different events",
    "boundary_point_not_reviewed": "Nobody has confirmed this handover point yet",
    "incomplete_capture": "At least one file only covers part of the period",
    "filter_mismatch": "The two files were pulled with different filters",
    "unlinked": "No confirmed train link was picked",
    "ambiguous_boundary_leg": "More than one record could match this train",
    "boundary_leg_not_selected": "The neighbouring record was not picked",
    "adjacent_leg_not_observed": "The neighbouring record is missing",
    "missing_time": "The file has no time for this",
    "no_run_selected": "No actual run was picked",
    "no_scheduled_or_observed_run_selected": "No actual run was picked",
    "run_selection_required": "Pick which run to use",
    "border_not_checked": "The handover could not be checked",
    "not_declared_complete": "The file does not claim to cover the whole period",
    "expired_out_of_window": "Dropped out of the rolling window after expiring",
    "entering_window": "Newly inside the rolling window",
    "leg_not_observed_in_selected_capture; operational_meaning_unknown": "No longer listed — we cannot tell if it still runs",
}


def label(value):
    return value.replace("_", " ").replace(".", " ")


def reason_label(reason):
    return REASON_LABELS.get(reason, label(reason))


def review_label(review):
    disposition, _, stale = review.partition(" (stale)")
    return "Decision needs another look" if stale else REVIEW_LABELS.get(disposition, label(disposition))


def queue_summary(row):
    kind = row["change_kind"]
    if kind in CHANGE_LABELS:
        return CHANGE_LABELS[kind]
    changed = row["changed_fields"]
    fields = ", ".join(dict.fromkeys(FIELD_LABELS.get(field, label(field)) for field in changed
                                     if not (field.endswith(".raw_time") and field.replace(".raw_time", ".at") in changed)))
    return fields + " changed" if fields else "Something in this record changed"


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
        return "No time given", ""
    observed = datetime.fromisoformat(value)
    if display_zone is not None:
        observed = observed.astimezone(display_zone)
    clock = observed.time().isoformat(timespec="microseconds" if observed.microsecond else
                                     "seconds" if show_seconds or observed.second else "minutes")
    offset = observed.strftime("%z")
    scope = observed.date().isoformat() + (f" · UTC{offset[:3]}:{offset[3:]}" if offset else " · Timezone not given")
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
        return "Nothing given", ""
    value = change[side]
    if change["field"].endswith(".at") and isinstance(value, str):
        return time_value(value)
    if value is None:
        return "Not stated", ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value), ""
    return str(value) if not isinstance(value, dict) else json.dumps(value, ensure_ascii=False), ""


def render_change(report):
    diffs = report["changes"]["field_diffs"]
    if report["before"] is None or report["after"] is None:
        comparison_panel(
            "Is this train in the file?",
            ("Listed" if report["before"] else "Not listed", ""),
            ("Listed" if report["after"] else "Not listed", ""),
            note="A train missing from a file is not a cancelled train. It may simply be outside what that file covers.",
        )
        for side, word in (("before", "earlier"), ("after", "later")):
            if report[side] is None:
                st.info(f"This train is not in the {word} file. "
                        "We cannot tell from that whether it still runs.")
    elif diffs:
        primary = next((item for item in diffs if item["field"] in ("exit.at", "entry.at")), diffs[0])
        field = primary["field"]
        comparison_panel(FIELD_LABELS.get(field, label(field)), _field_value(primary, "old"), _field_value(primary, "new"))
        if field in ("exit.at", "entry.at"):
            for side in ("before", "after"):
                payload = report[side]["payload"]
                event = payload.get(field.split(".")[0])
                if event and event["at"] and len(payload["operating_dates"]) > 1:
                    st.warning(f"The {'earlier' if side == 'before' else 'later'} file lists several dates this train runs "
                               f"but gives one timestamp, dated {datetime.fromisoformat(event['at']).date()}. "
                               "Which date that time belongs to cannot be checked.")
    else:
        st.info("The checks gave a different answer, but no field in the file itself changed.")
    if diffs:
        with st.expander("Every field that changed"):
            st.dataframe([{"Field": FIELD_LABELS.get(item["field"], label(item["field"])),
                           "Earlier": " · ".join(filter(None, _field_value(item, "old"))),
                           "Later": " · ".join(filter(None, _field_value(item, "new")))}
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
        "Handover point · " + detail["point_id"],
        time_value(detail["left_at"], display_zone=display_zone),
        time_value(detail["right_at"], display_zone=display_zone),
        labels=("Leaves", "Arrives"), transition=False,
        note=("Both times shown in the timezone this train's file uses." if display_zone
              else "Both times shown in UTC."),
    )
