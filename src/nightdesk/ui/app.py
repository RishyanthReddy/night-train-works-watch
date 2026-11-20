"""Nightdesk: review what changed, check the evidence, decide."""

from datetime import date, datetime, time, timedelta
import getpass
from html import escape
import os
from pathlib import Path

import streamlit as st

from nightdesk.audit import read_events
from nightdesk.config import PUBLIC_DEMO_BUNDLE, PUBLIC_DEMO_ENV, PUBLIC_DEMO_MANIFEST, get_bundle, selected_bundle_name
from nightdesk.desk import dossier, queue, snapshot_revisions
from nightdesk.model import PathLeg
from nightdesk.store import ReadSession
from nightdesk.export import export_dossier
from nightdesk.intake.mapping import captures, confirm_mapping, ingest
from nightdesk.intake.batch import batches, confirm_batch, ingest_batch
from nightdesk.links import import_links, links, link_id
from nightdesk.review import record_decision, follow_up
from nightdesk.gates import capture_comparison_gate
from nightdesk.ui.scenario import render_scenario
from nightdesk.ui.review_desk import (
    REVIEW_LABELS, comparison_panel, queue_summary, reason_label, render_boundary_clocks, render_brand,
    render_change, review_label, time_value,
)


def main():
    st.set_page_config(page_title="Nightdesk", layout="wide")
    locked_demo = os.environ.get(PUBLIC_DEMO_ENV) == "1"
    if locked_demo:
        name = PUBLIC_DEMO_BUNDLE
        st.sidebar.text("Case folder: demo")
    else:
        name = st.sidebar.text_input("Case folder", value=selected_bundle_name(),
                             help="A folder holding the files for one set of trains.")
    try:
        bundle = get_bundle(name)
        bundle.real_root()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    key = lambda text: bundle.name + ":" + text
    if bundle.name != PUBLIC_DEMO_BUNDLE:
        st.sidebar.caption("Private data — never leaves this machine" if bundle.nda
                           else "Practice data")
    actor = st.sidebar.text_input("Your name", value="Demo reviewer" if bundle.name == PUBLIC_DEMO_BUNDLE else
                                  getpass.getuser(), key=key("actor"))
    demo_registry = None
    if bundle.name == PUBLIC_DEMO_BUNDLE or st.sidebar.checkbox("Demo mode", key=key("demo_mode"),
                                                 help="Show only the checked example files."):
        try:
            from nightdesk.demo import check_demo
            demo_registry = check_demo(PUBLIC_DEMO_MANIFEST, bundle)
            st.sidebar.caption("Demo mode: only files listed in the demo manifest are shown.")
        except (ValueError, OSError) as exc:
            st.error("Demo mode refused: " + str(exc))
            st.stop()
    mode = "Demo" if demo_registry else "Private data" if bundle.nda else "Local"
    render_brand(f"{mode} · {bundle.name}")
    if key("flash") in st.session_state:
        st.success(st.session_state.pop(key("flash")))
    with st.sidebar.expander("Add one file"):
        file = st.text_input("File path", key=key("input_file"))
        mapping = st.text_input("Column mapping (YAML)", key=key("mapping_file"))
        if st.button("Check the mapping", key=key("confirm_mapping")):
            try:
                if demo_registry: demo_registry.require(mapping)
                sha = confirm_mapping(mapping, bundle, actor)
                st.success("Mapping checked: " + sha)
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if st.button("Read the file", key=key("import_file")):
            try:
                if demo_registry:
                    demo_registry.require(file); demo_registry.require(mapping)
                result = ingest(file, mapping, bundle)
                if result.get("record_type") == "JourneyLinkMember":
                    import_links(bundle, result["capture_id"])
                st.session_state[key("flash")] = (
                    f"Read {result['accepted']} rows; {result['rejected']} were thrown out. "
                    "The original file is untouched.")
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(str(exc))
    with st.sidebar.expander("Add several files at once"):
        manifest = st.text_input("File list (YAML)", key=key("manifest"))
        if st.button("Check the file list", key=key("confirm_batch")):
            try:
                if demo_registry: demo_registry.require(manifest)
                confirm_batch(manifest, bundle, actor)
                st.success("File list checked.")
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if st.button("Read the files", key=key("import_batch")):
            try:
                if demo_registry: demo_registry.require(manifest)
                result = ingest_batch(manifest, bundle)
                for identifier in result["children"].values():
                    from nightdesk.desk import snapshot
                    if snapshot(bundle, identifier)["metadata"]["record_type"] == "JourneyLinkMember":
                        import_links(bundle, identifier)
                st.session_state[key("flash")] = "Read in: " + result["metadata"]["label"]
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(str(exc))
    with st.sidebar:
        render_text_intake(bundle, actor, key, demo_registry=demo_registry)
    try:
        reader = ReadSession(bundle)
        imported = captures(bundle, reader=reader) + batches(bundle, reader=reader)
    except (ValueError, OSError) as exc:
        st.error("This case folder could not be read: " + str(exc))
        st.stop()
    by_id = {c["capture"].capture_id: c for c in imported}
    def caption(identifier):
        c = by_id[identifier]
        capture = c["capture"]
        state = "complete" if capture.complete else "incomplete"
        label = c["metadata"].get("label", Path(c["metadata"]["path"]).name)
        if label == "capture.json":
            label = capture.dataset
        return f"{label} · {capture.captured_at.isoformat(timespec='seconds')} · {identifier[:10]} · {state}"
    def contains(c, record):
        return c["metadata"].get("record_type") == record or record in c["metadata"].get("record_types", [])
    path_ids = [i for i, c in by_id.items() if contains(c, "PathLeg") or c["metadata"].get("record_type") == "Batch"]
    old_id = st.sidebar.selectbox("Earlier file", path_ids, index=None, format_func=caption, key=key("before"))
    new_id = st.sidebar.selectbox("Later file", path_ids, index=None, format_func=caption, key=key("after"))
    works_id = st.sidebar.selectbox("Engineering works file (optional)", [i for i,c in by_id.items() if contains(c, "WorkNotice")],
                                    index=None, format_func=caption, key=key("works"))
    runs_id = st.sidebar.selectbox("Actual run file (optional)", [i for i,c in by_id.items() if contains(c, "RunRow")],
                                   index=None, format_func=caption, key=key("runs"))
    available_links = {link_id(link): link for link in links(bundle)}
    link_identifier = st.sidebar.selectbox("Confirmed train link (optional)", list(available_links), index=None,
            format_func=lambda i: available_links[i].journey_id + " · " + available_links[i].basis + " · " + i[:8], key=key("link"))
    reviewed_text = st.sidebar.text_input("Border handover points I checked (comma separated)",
                                          key=key("points"),
                                          help="The place where this train hands over from one country to the next.")
    reviewed = {p.strip() for p in reviewed_text.split(",") if p.strip()}
    if not st.sidebar.checkbox("I checked those handover points myself", key=key("reviewed")):
        reviewed = set()
    alias_ids = sorted({e.payload["table_id"] for e in read_events(bundle) if e.kind == "aliases_confirmed"})
    alias_table_id = st.sidebar.selectbox("Station name table (optional)", alias_ids, index=None,
        key=key("aliases"), help="Pick one checked table if this case folder has more than one.")
    boundary_options = {}
    if old_id and new_id:
        try:
            for side, identifier in (("before", old_id), ("after", new_id)):
                for revision in snapshot_revisions(bundle, identifier, reader=reader):
                    if isinstance(revision.payload, PathLeg):
                        leg = revision.payload
                        label = f"{side}: {leg.train_no} / leg {leg.sequence} / {leg.request_id or 'request unknown'} / {revision.revision_id[:10]}"
                        if revision.revision_id in boundary_options:
                            boundary_options[revision.revision_id] += " / also after"
                        else:
                            boundary_options[revision.revision_id] = label
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    boundary_ids = st.sidebar.multiselect("Border handover records (optional)", list(boundary_options),
        format_func=boundary_options.get, key=key(f"boundary_legs:{old_id}:{new_id}"),
        help="If more than one record matches the train number, say which one you mean for each file. A train that leaves and re-enters needs one choice per leg. Otherwise the handover stays unknown. Choosing here never creates a confirmed train link.")
    from nightdesk.desk import run_options
    try:
        dated_runs = run_options(bundle, [old_id, new_id, runs_id], reader=reader) if old_id and new_id else {}
    except (ValueError, OSError) as exc:
        st.error(str(exc)); dated_runs = {}
    run_selection_ids = st.sidebar.multiselect("Actual run records (optional)", list(dated_runs),
        format_func=dated_runs.get, key=key(f"run_choices:{old_id}:{new_id}:{runs_id}"),
        help="Pick a run if several trips match this train and date. Works checks compare against timetable times. The Run times tab keeps timetable, published and actual times apart.")
    queue_tab, dossier_tab, audit_tab, evidence_tab, work_tab, scenario_tab = st.tabs(
        ["Changes", "This change", "History", "Run times", "Works", "CO₂"],
        key=key("active_tab"), on_change="rerun")
    if not evidence_tab.open:
        run = st.session_state.get(key(f"source_run:{runs_id}"))
        retain_widget_values(key, "es_run_review", f"source_run:{runs_id}", f"clock_point:{runs_id}:{run}")
    if not work_tab.open:
        before = st.session_state.get(key(f"works_before:{works_id}"))
        classification = st.session_state.get(key("membership_classification"))
        query = st.session_state.get(key("work_search"), "").strip().casefold()
        validity = st.session_state.get(key("work_validity"))
        retain_widget_values(key, f"works_before:{works_id}", "membership_classification",
                             f"membership_page:{works_id}:{before}:{classification}", "work_search", "work_validity",
                             f"work_page:{works_id}:{query}:{validity}", "source_work")
    rows = []
    comparison_error = False
    selections = dict(works_capture_id=works_id, run_capture_id=runs_id, link_identifier=link_identifier,
                      reviewed_points=reviewed, boundary_revision_ids=boundary_ids, alias_table_id=alias_table_id,
                      run_selection_ids=run_selection_ids)
    if old_id and new_id:
        try:
            rows = queue(bundle, old_id, new_id, **selections)
        except (ValueError, OSError) as exc:
            comparison_error = True
            with queue_tab:
                st.error("Could not compare these captures.")
                st.text(str(exc))
    comparison_pair = (old_id, new_id)
    if st.session_state.get(key("comparison_pair")) != comparison_pair:
        st.session_state[key("comparison_pair")] = comparison_pair
        st.session_state.pop(key("selected"), None)
        st.session_state.pop(key("source_leg"), None)
    with queue_tab:
        left, right = st.columns([1, 2.7], gap="large")
        with left, st.container(key="nightdesk_queue"):
            selected = render_queue(rows, old_id, new_id, by_id, caption, comparison_error, key)
        with right:
            if not dossier_tab.open:
                render_selected_dossier(bundle, rows, selected, old_id, new_id, selections, actor, key)
    if dossier_tab.open:
        with dossier_tab:
            render_selected_dossier(bundle, rows, selected, old_id, new_id, selections, actor, key)
    with audit_tab:
        st.subheader("Rows the checks threw out")
        from nightdesk.audit import canonical_json
        rejected = list({canonical_json(r): r for c in imported for r in c["rejects"]}.values())
        if rejected:
            st.dataframe(rejected, hide_index=True)
        else:
            st.info("Every row passed the checks.")
        st.subheader("How much of the period each file covers")
        st.dataframe([{"capture": c["capture"].capture_id, "dataset": c["capture"].dataset,
                       "complete": c["capture"].complete, "reasons": c["capture"].incomplete_reasons} for c in imported], hide_index=True)
        st.subheader("Change history")
        st.caption("Every action is appended to a file on this machine. Earlier entries cannot be edited in place.")
        from nightdesk.audit import verify, upgrade_legacy
        copy_path = st.text_input("Saved copy of the history (optional)", key=key("audit_copy"),
                                  help="A path to an earlier copy of the history file, if you kept one.")
        seal = st.text_input("Seal from an earlier copy (optional)", key=key("audit_seal"))
        count = st.text_input("Event count from that copy (optional)", key=key("audit_count"))
        st.caption("If you wrote down a seal and count earlier, enter them here to prove nothing was added, removed or reordered since.")
        if st.button("Check the history", key=key("verify_audit")):
            try:
                st.json(verify(bundle, seal=seal.strip() or None, count=int(count) if count.strip() else None, copy_path=copy_path.strip() or None))
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if st.button("Upgrade an older history file", key=key("upgrade_audit")):
            try:
                st.json(upgrade_legacy(bundle, actor))
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        st.json([event.model_dump(mode="json") for event in read_events(bundle)[-50:]])
    with evidence_tab:
        if evidence_tab.open:
            render_run_evidence(bundle, runs_id, key, reader)
            if not demo_registry and not bundle.nda:
                render_es_run_comparison(bundle, key, reader)
    with work_tab:
        if work_tab.open:
            render_works_evidence(bundle, works_id, by_id, caption, key, reader)
    with scenario_tab:
        render_scenario(key)


def retain_widget_values(key, *names):
    """Keep inactive evidence inputs without inspecting or exporting their records."""
    for name in names:
        widget = key(name)
        if widget in st.session_state:
            st.session_state[widget] = st.session_state[widget]


def render_queue(rows, old_id, new_id, by_id, caption, comparison_error, key):
    st.subheader("Changes found")
    if not old_id or not new_id:
        st.info("Pick an earlier and a later file in the sidebar.")
        return None
    st.text("Before · " + caption(old_id) + "\nAfter  · " + caption(new_id))
    if by_id[new_id]["capture"].captured_at < by_id[old_id]["capture"].captured_at:
        st.warning("The file marked Later was recorded before the one marked Earlier. Swap them.")
    comparison = capture_comparison_gate(by_id[old_id]["capture"], by_id[new_id]["capture"])
    if not comparison.passed:
        st.warning("This comparison is incomplete — " + reason_label(comparison.reason_code).lower() + ".")
    if not rows:
        if not comparison_error:
            st.info("Nothing changed between these two files." if comparison.passed else
                    "These two files cannot be compared for train changes.")
        return None
    options = {(row["selection_revision"], row["service_date"]): row for row in rows}
    selected = st.selectbox("Open a train and date", options, index=None,
                            format_func=lambda choice: options[choice]["train_no"] + " / " + choice[1],
                            key=key("selected"),
                            on_change=lambda: st.session_state.pop(key("source_leg"), None))
    for choice, row in list(options.items())[:8]:
        with st.container(border=choice == selected):
            lines = [row["train_no"] + " · " + row["service_date"], queue_summary(row), review_label(row["local_review"])]
            if row["next_owner"] != "unassigned":
                lines.append("Follow-up · " + row["next_owner"])
            st.text("\n".join(lines))
    st.caption("Your decision covers every date this train runs, not just the one shown.")
    if len(options) > 8:
        st.caption(f"Showing 8 of {len(options)}. Use the picker above to find the rest.")
    return selected


def render_selected_dossier(bundle, rows, selected, old_id, new_id, selections, actor, key):
    if selected is None:
        st.info("Pick a train above to see what changed and decide what to do.")
        return
    try:
        task = next(row for row in rows if (row["selection_revision"], row["service_date"]) == selected)
        leg_choices = {leg["selection_revision"]: leg for leg in task["leg_changes"]}
        revision = selected[0]
        if len(leg_choices) > 1:
            revision = st.selectbox("Which record changed", list(leg_choices), index=None,
                                    format_func=lambda i: leg_choices[i]["subject_key"] + " · " + i[:10],
                                    key=key("source_leg"))
            if revision is None:
                st.info("Pick which record to inspect.")
                return
        report = dossier(bundle, old_id, new_id, revision, date.fromisoformat(selected[1]), **selections)
        render_dossier(bundle, report, actor, key)
    except (ValueError, OSError) as exc:
        st.error("This train could not be opened.")
        st.text(str(exc))


def render_provenance(report, *, expanded=True):
    with st.expander("Where these files came from", expanded=expanded):
        for row in report["provenance"]:
            coverage = "Whole period" if row["complete"] else "Part of period · " + ", ".join(
                reason_label(reason) for reason in row["incomplete_reasons"])
            recorded = "Time it was added here" if report.get("kind") == "run_evidence" and not report.get("capture_origin") else "Time the source recorded it"
            source = row["source"]
            if report.get("bundle") == PUBLIC_DEMO_BUNDLE and not source.startswith(("https://", "http://")):
                source = Path(source).name
            st.text(f"{row['role']} · {row['dataset']} · {row['licence']} · {coverage}\n"
                    f"{recorded} · {row['captured_at']}\nCapture {row['capture_id']}\n{source}")


def render_run_evidence(bundle, capture_id, key, reader):
    from nightdesk.desk import run_evidence, run_options
    from nightdesk.export import export_run_evidence
    st.subheader("Actual run")
    if not capture_id:
        st.info("Pick an actual run file in the sidebar.")
        return
    try:
        options = run_options(bundle, [capture_id], reader=reader)
        selection = st.selectbox("Which run", list(options), index=None, format_func=options.get,
                                 key=key(f"source_run:{capture_id}"))
        if selection is None:
            return
        report = run_evidence(bundle, capture_id, selection, reader=reader)
        run = report["run"]
        st.text(f"{run['train_no']} · {run['service_date']} · {run['kind']}")
        timed = [point for point in run["points"] if point["planned_dep"] and point["real_dep"]]
        if timed:
            choice = st.selectbox(
                "Compare departure at", range(len(timed)),
                format_func=lambda i: (timed[i]["name"] or timed[i]["point_id"]) + " · " + timed[i]["real_dep"],
                key=key(f"clock_point:{capture_id}:{selection}"),
            )
            point = timed[choice]
            comparison_panel("Departure at " + (point["name"] or point["point_id"]),
                             time_value(point["planned_dep"], show_seconds=True),
                             time_value(point["real_dep"], show_seconds=True),
                             labels=("Timetable", "Actually left"),
                             note="One stop, as recorded in the file you picked.")
        for assumption in run["extra"].get("assumptions", []):
            st.text("Assumption about times · " + assumption)
        render_provenance(report, expanded=False)
        st.caption(" · ".join(report["limits"]))
        origin = report["capture_origin"]
        if origin and origin["evidence"].get("coverage"):
            st.text(origin["evidence"]["coverage"])
        if origin and origin["evidence"].get("attribution"):
            st.text(origin["evidence"]["attribution"])
        if not report["capture"]["complete"]:
            st.warning("Partial file — " + ", ".join(
                reason_label(reason).lower() for reason in report["capture"]["incomplete_reasons"]))
        labels = {"point_id": "Point", "name": "Station", "planned_arr": "Timetable arrival",
                  "planned_dep": "Timetable departure", "real_arr": "Actual arrival", "real_dep": "Actual departure",
                  "published_arr": "Published arrival", "published_dep": "Published departure",
                  "delay_arr_s": "Arrival delay (s)", "delay_dep_s": "Departure delay (s)",
                  "line_arr": "Arrival line", "line_dep": "Departure line"}
        fields = [field for field in labels if field == "point_id" or any(point[field] is not None for point in run["points"])]
        display = [{labels[field]: point[field] for field in fields} for point in run["points"]]
        if "timetable_status" in report:
            for shown, status in zip(display, report["timetable_status"], strict=True):
                shown.update({"Arrival status": status["arrival"], "Departure status": status["departure"],
                              "Source feed": " + ".join(status["feeds"]), "Change messages": status["change_messages"]})
        if report["capture"]["dataset"] == "rijden_archive":
            for shown, point in zip(display, run["points"], strict=True):
                extra = point["extra"]
                shown.update({"Reported arrival delay (min)": extra.get("rdt_arrival_delay_min"),
                              "Reported departure delay (min)": extra.get("rdt_departure_delay_min"),
                              "Arrival cancelled": extra.get("Stop:Arrival cancelled"),
                              "Departure cancelled": extra.get("Stop:Departure cancelled"),
                              "Service partly cancelled": extra.get("Service:Partly cancelled"),
                              "Service completely cancelled": extra.get("Service:Completely cancelled"),
                              "Delay evidence": "; ".join(
                                  f"{side}: {reason}" for side, reason in extra.get("rdt_delay_warnings", {}).items()
                              ) if isinstance(extra.get("rdt_delay_warnings"), dict) else ""})
        elif run["kind"] == "archived_report":
            for shown, point in zip(display, run["points"], strict=True):
                warnings = point["extra"].get("archive_time_warnings")
                shown.update({"Reported arrival delay (min)": point["extra"].get("arrival_delay_min"),
                              "Reported departure delay (min)": point["extra"].get("departure_delay_min"),
                              "Delay source": point["extra"].get("delay_source"),
                              "Time evidence": ", ".join(f"{field} ({reason})" for field, reason
                                                        in warnings.items()) if isinstance(warnings, dict) else ""})
        if run["unresolved"].get("point_order"):
            st.text("Stop order unresolved · " + run["unresolved"]["point_order"]["reason"])
        if report["capture"]["dataset"] == "rijden_archive":
            st.text("Stops appear in the order the archive file lists them. Time between stops cannot be checked.")
        st.dataframe(display, hide_index=True)
        with st.expander("Raw records behind this view"):
            st.json(report)
        if st.button("Save this run (Markdown + JSON)", key=key("export_run_evidence")):
            paths = export_run_evidence(bundle, capture_id, selection)
            st.success("Saved: " + ", ".join(p.name for p in paths))
    except (ValueError, OSError) as exc:
        st.error("This run could not be opened.")
        st.text(str(exc))


def render_es_run_comparison(bundle, key, reader):
    from nightdesk.es_runs import compare_runs
    from nightdesk.export import export_es_run_comparison

    with st.expander("Compare against a checked European Sleeper review"):
        path = st.text_input("Path to the review JSON", key=key("es_run_review"))
        if not path:
            return
        try:
            report = compare_runs(bundle, path, reader=reader)
            st.text(f"ES {report['train']} · reviewed by {report['review']['reviewed_by']}")
            st.text(" · ".join(report["limits"]))
            render_provenance(report)
            counts = report["unreviewed_points"]
            st.text(f"Outside the review · scheduled points {counts['scheduled']} · observed points {counts['observed']}")
            st.dataframe([
                {"Timetable station": station["scheduled_name"], "Source stop ID": station["scheduled_native_stop_id"],
                 "Infrabel station": station["observed_name"],
                 **{f"{label} {side}": event[field]
                    for side in ("arrival", "departure")
                    for event in (station[side],)
                    for label, field in (("Timetable", "scheduled"), ("Infrabel planned", "infrabel_planned"),
                                         ("Actual", "observed"), ("Same planned instant for", "schedule_agrees"))}}
                for station in report["stations"]
            ], hide_index=True)
            with st.expander("Raw records behind this comparison"):
                st.json(report)
            if st.button("Save this comparison (Markdown + JSON)", key=key("export_es_run_comparison")):
                paths = export_es_run_comparison(bundle, path)
                st.success("Saved: " + ", ".join(p.name for p in paths))
        except (ValueError, OSError) as exc:
            st.error("This comparison could not be opened.")
            st.text(str(exc))


def render_works_evidence(bundle, capture_id, available, caption, key, reader):
    from collections import Counter
    from nightdesk.desk import works_evidence
    from nightdesk.export import export_works_evidence
    st.subheader("Engineering works")
    if not capture_id:
        st.info("Pick an engineering works file in the sidebar.")
        return
    capture = available[capture_id]["capture"]
    before = st.selectbox("Earlier works file (optional)", [
        identifier for identifier, selected in available.items()
        if identifier != capture_id and selected["capture"].dataset == capture.dataset
        and selected["capture"].captured_at < capture.captured_at
    ], index=None, format_func=caption, key=key(f"works_before:{capture_id}"))
    try:
        report = works_evidence(bundle, capture_id, before, reader=reader)
        render_provenance(report)
        if not capture.complete:
            st.warning("Partial file — " + ", ".join(reason_label(reason).lower() for reason in capture.incomplete_reasons))
        origin = report["capture_origin"]
        if origin:
            with st.expander("Where this file came from"):
                st.json(origin)
        result = report["comparison"]
        if result is not None:
            if result["reason"]:
                st.info("These files can only be partly compared: " + result["reason"])
            groups = Counter(item["classification"] for item in result["membership_changes"])
            if groups:
                st.caption("What changed in this file")
                st.dataframe([{"Finding": reason_label(name), "Records": count} for name, count in sorted(groups.items())],
                             hide_index=True)
                classification = st.selectbox("Change type", sorted(groups), format_func=reason_label,
                                              key=key("membership_classification"))
                selected = [row for row in result["membership_changes"] if row["classification"] == classification]
                page = evidence_page(selected, "Page", key(f"membership_page:{capture_id}:{before}:{classification}"))
                st.dataframe([{"version": item["revision_id"][:12], "why": reason_label(item["reason"]),
                               "row in file": item["source"]["record_id"]} for item in page], hide_index=True)
        query = st.text_input("Search by work ID, line or place", key=key("work_search")).strip().casefold()
        validity = st.date_input("On this date (optional)", value=None, key=key("work_validity"))
        keys = ("work_id", "line", "from_place", "to_place")
        records = [item for item in report["records"]
                   if (not validity or _has_validity_date(item["work"], validity))
                   and (not query or any(query in str(item["work"][field] or "").casefold() for field in keys))]
        st.caption(f"{len(records)} works match")
        page = evidence_page(records, "Page", key(f"work_page:{capture_id}:{query}:{validity}"))
        st.dataframe([{field: item["work"][field] for field in (*keys, "date_start", "date_end", "effect", "description")}
                      | {"source row": item["source"]["record_id"]} for item in page], hide_index=True)
        items = {f"{item['source']['capture_id']}:{item['source']['record_id']}": item for item in page}
        chosen = st.selectbox("Open one work", list(items), index=None, key=key("source_work"),
                              format_func=lambda row: f"{items[row]['work']['work_id'] or 'Unknown ID'} · {row}")
        if chosen:
            st.json(items[chosen])
        if st.button("Save these works (Markdown + JSON)", key=key("export_works_evidence")):
            paths = export_works_evidence(bundle, capture_id, before)
            st.success("Saved: " + ", ".join(p.name for p in paths))
    except (ValueError, OSError) as exc:
        st.error("These works files could not be opened.")
        st.text(str(exc))


def evidence_page(items, label, key):
    size = 100
    pages = (len(items) + size - 1) // size
    if pages <= 1:
        return items
    page = st.number_input(label, min_value=1, max_value=pages, value=1, step=1, key=key)
    return items[(page - 1) * size:page * size]


def _has_validity_date(work, day):
    if "siri_validity_periods" in work["extra"]:
        from zoneinfo import ZoneInfo
        from nightdesk.timeutil import explicit_validity_periods, overlap
        try:
            tz = ZoneInfo(work["timezone"])
            day_window = (datetime.combine(day, time.min, tz), datetime.combine(day + timedelta(days=1), time.min, tz))
            return any(overlap(period, day_window) is not None
                       for period in explicit_validity_periods(work["extra"]["siri_validity_periods"]))
        except (ValueError, OverflowError, TypeError, KeyError):
            return False
    return work["date_start"] <= day.isoformat() <= work["date_end"]


def render_text_intake(bundle, actor, key, demo_registry=None):
    import json
    from nightdesk.llm.client import propose, allowed
    from nightdesk.intake.text import submit_text
    with st.expander("Paste a notice (optional)"):
        st.caption("A draft never imports anything by itself. Every filled field must quote the notice exactly. Anything the notice does not say stays blank.")
        st.caption("AI drafting: " + ("on for this case folder" if allowed(bundle) else "off for this case folder"))
        if demo_registry:
            replay_path = st.selectbox("Recorded example", demo_registry.paths("replay"),
                                       format_func=lambda path: path.name, key=key("demo_replay"))
            if st.button("Replay the example", key=key("demo_replay_button")):
                demo_registry.require(replay_path)
                body = json.loads(replay_path.read_text())
                result = propose(bundle, body["source_text"], demo_registry.paths("text_mapping")[0], provider="replay", replay_path=replay_path)
                st.json(result)
                if not result["accepted"]: st.error("Draft rejected: " + ", ".join(result["reasons"]))
            return
        mapping = st.text_input("Notice mapping (YAML)", key=key("text_mapping"))
        raw = st.text_area("Notice text", key=key("notice_text"))
        provider = st.selectbox("Who drafts the fields", ["off", "replay", "mistral"], key=key("text_provider"))
        replay_path = st.text_input("Recorded example file (local)", key=key("text_replay"))
        if st.button("Draft the fields only", key=key("text_propose")):
            result = propose(bundle, raw, mapping, provider=provider, replay_path=replay_path or None)
            st.session_state[key("text_proposal_result")] = result
            if result["accepted"] and isinstance(result["proposal"], dict):
                st.session_state[key("drafted_by")] = "llm" if provider == "mistral" else "replay"
                st.session_state[key("text_fields")] = json.dumps(result["proposal"].get("fields", {}), ensure_ascii=False, indent=2)
                st.session_state[key("text_quotes")] = json.dumps(result["proposal"].get("quotes", {}), ensure_ascii=False, indent=2)
        result = st.session_state.get(key("text_proposal_result"))
        if result:
            if result["accepted"]: st.info("The draft passed the checks. Read the fields and quotes before you import.")
            else: st.error("Draft rejected: " + ", ".join(result["reasons"]))
        with st.form(key("manual_text_form")):
            drafted_by = st.selectbox("Who drafted this", ["manual", "llm", "replay"], key=key("drafted_by"))
            fields = st.text_area("Work fields (JSON)", value="{}", key=key("text_fields"))
            quotes = st.text_area("Exact quotes from the notice, one per field (JSON)", value="{}", key=key("text_quotes"))
            st.caption("Use the standard field names, dates as YYYY-MM-DD, clocks as HH:MM, and say which timezone. German DD.MM.YYYY dates in quotes are also accepted. Typing the fields yourself needs no API key.")
            if st.form_submit_button("Check and add this work"):
                try:
                    result = submit_text(bundle, raw, {"fields": json.loads(fields), "quotes": json.loads(quotes)}, mapping, actor=actor, mode=drafted_by)
                    if result.get("rejected"):
                        st.error("Rejected: " + ", ".join(result.get("reasons", ["record_gate_failed"])))
                    else:
                        st.session_state[key("flash")] = "Work added. Nobody has reviewed it yet."
                        st.rerun()
                except (ValueError, OSError):
                    st.error("Nothing was added. Check the mapping, the fields, and that every quote is word for word.")


def render_dossier(bundle, report, actor, key):
    st.html(f"<h2>Train {escape(report['train_no'])}</h2>")
    st.text(report["train_no"] + " / " + report["service_date"] + " · " +
            ("Make-believe data" if report["data_label"] == "synthetic" else "Licences are listed under Where these files came from"))
    render_change(report)
    if report["capture_comparison"] and report["capture_comparison"]["reason"]:
        st.warning("This comparison is incomplete — " +
                   reason_label(report["capture_comparison"]["reason"]).lower() + ".")
    status = report["operating_date_presence"]
    if status["before"] != status["after"]:
        descriptions = {True: "Listed", False: "Not listed", None: "Unknown"}
        st.caption(f"Is this date in the file? · Earlier: {descriptions[status['before']]} · "
                   f"Later: {descriptions[status['after']]}")

    st.subheader("Evidence")
    st.markdown("**Border handover checks**")
    if not report["findings"]:
        st.info("There is no neighbouring record to check this train against.")
    if any(f["reason"] in {"ambiguous_boundary_leg", "boundary_leg_not_selected"} for f in report["findings"]):
        st.warning("More than one record could match this train. Pick the right one in the sidebar.")
    for finding in report["findings"]:
        reason = finding["reason"]
        if finding["result"] == "unknown":
            st.info("The handover could not be checked. " + (reason_label(reason) + "." if reason else ""))
        else:
            st.text(reason_label(reason) if reason else "Both sides agree on the fields that were checked.")
        render_boundary_clocks(report, finding)
        with st.expander("Handover records"):
            st.text(finding["result"] + (" · " + reason if reason else ""))
            if finding["detail"].get("left_at") and finding["detail"].get("right_at"):
                for role, source in zip(("Exit", "Entry"), finding["input_refs"][:2]):
                    st.text(f"{role} · row {source['record_id']} · file {source['capture_id'][:12]}")
            st.json(finding)

    st.markdown("**Engineering works on this route**")
    if report["works_exposures"]:
        works = {work["revision_id"]: work["payload"] for work in report["work_records"]}
        labels = {"A": "Same route, times overlap", "B": "Same route, may overlap",
                  "time_unknown": "Times could not be checked"}
        st.dataframe([{
            "Work": works.get(item["work_revision"], {}).get("work_id", item["work_revision"]),
            "What this means": labels.get(item["outcome"], item["outcome"]),
            "Code": item["outcome"],
            "Why": ", ".join(reason_label(reason) for reason in item["reasons"]),
        } for item in report["works_exposures"]], hide_index=True)
    if report["checked_pairs"]:
        st.caption(f"Checked {report['no_match_checked_pairs']} of {report['checked_pairs']} route pairs and found no overlap. "
                   "Finding no match is not proof that the route is clear.")
    if report["unlocated_checks_not_attached_to_train"]:
        st.warning(f"{len(report['unlocated_checks_not_attached_to_train'])} works record(s) name a place "
                   "that could not be located, so they were not checked against this train.")
    unknowns = list(dict.fromkeys(reason_label(reason) for reason in report["unknowns"]))
    if unknowns:
        st.text("Still unknown · " + " · ".join(unknowns))
    render_provenance(report, expanded=False)
    with st.expander("Raw records behind these checks"):
        st.json({name: report[name] for name in (
            "before", "after", "source_presence", "operating_date_presence", "checks_before", "checks_after",
            "works_state_changes", "work_records", "work_records_before", "unlocated_checks_not_attached_to_train",
            "selected_run", "selected_run_before", "findings_before", "unknowns", "assumptions", "capture_comparison",
        )})
    if st.button("Ask for a delay estimate", key=key("delay_request")):
        from nightdesk.estimate import estimate_delay
        from nightdesk.audit import append_event
        refusal = estimate_delay()
        append_event(bundle, "delay_request_refused", {"revision_id": report["selection_revision"], **refusal.model_dump(mode="json")})
        st.warning(refusal.detail)
        st.text(refusal.reason_code)
        st.text(refusal.what_would_fix_it)

    st.subheader("Your decision")
    revision = report["after"] or report["before"]
    operating_dates = revision["payload"]["operating_dates"]
    st.caption("Your decision covers every date this record lists.")
    if len(operating_dates) > 1:
        st.warning(f"This decision covers all {len(operating_dates)} dates this train runs.")
        with st.expander("Dates this covers"):
            st.text(", ".join(operating_dates))
    if any(item["stale"] for item in report["local_reviews"]):
        st.warning("A newer version of this record arrived after that decision. It needs another look.")
    if report["local_reviews"] or report["follow_ups"]:
        with st.expander("Earlier decisions and open questions", expanded=True):
            for item in report["local_reviews"]:
                st.text(f"{review_label(item['disposition'])} · {item['actor']} · {item['at']}\n{item['reason']}")
            for item in report["follow_ups"]:
                st.text(f"{item['owner']} · {reason_label(item['status'])}\n{item['question']}")
    review_key = f"review_form:{report['selection_revision']}"
    with st.form(key(review_key), clear_on_submit=False):
        disposition = st.selectbox("Decision", ["needs_clarification", "accepted_locally", "rejected_locally"],
                                   format_func=REVIEW_LABELS.get, key=key(review_key + ":decision"))
        reason = st.text_area("Why", key=key(review_key + ":reason"))
        owner = st.text_input("Who should answer (optional)", key=key(review_key + ":owner"))
        question = st.text_area("What needs answering (optional)", key=key(review_key + ":question"))
        if st.form_submit_button("Record this decision"):
            if not actor.strip() or not reason.strip() or bool(owner.strip()) != bool(question.strip()):
                st.error("Add your name and a reason. If you are raising a question, add both the person and the question.")
            else:
                identifier = report["selection_revision"]
                record_decision(bundle, identifier, actor, disposition, reason)
                if question.strip():
                    follow_up(bundle, identifier, owner, question)
                st.session_state[key("flash")] = "Decision recorded. This is your team's call — no national approval was given."
                st.rerun()
    if st.button("Export this change", key=key("export")):
        md, js = export_dossier(report, bundle)
        st.success("Saved as Markdown and JSON.")
        st.text(md.name if bundle.name == PUBLIC_DEMO_BUNDLE else str(md))
        st.text(js.name if bundle.name == PUBLIC_DEMO_BUNDLE else str(js))
        st.download_button("Download Markdown", md.read_text("utf-8"), file_name=md.name, mime="text/markdown",
                           on_click="ignore")
        st.download_button("Download JSON", js.read_text("utf-8"), file_name=js.name, mime="application/json",
                           on_click="ignore")


if __name__ == "__main__":
    main()
