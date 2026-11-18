"""Plain Phase 1 queue and dossier. Styling/design research belongs to Phase 4."""

from datetime import date, datetime, time, timedelta
import getpass
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


def main():
    st.set_page_config(page_title="nightdesk")
    st.title("nightdesk")
    st.caption("Compare selected revisions, inspect sourced checks, record a local decision.")
    locked_demo = os.environ.get(PUBLIC_DEMO_ENV) == "1"
    if locked_demo:
        name = PUBLIC_DEMO_BUNDLE
        st.sidebar.text("Bundle: demo")
    else:
        name = st.sidebar.text_input("Bundle", value=selected_bundle_name())
    try:
        bundle = get_bundle(name)
        bundle.real_root()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    key = lambda text: bundle.name + ":" + text
    if bundle.name != PUBLIC_DEMO_BUNDLE:
        st.sidebar.caption("NDA: data stays local" if bundle.nda else "Local practice / test bundle")
    actor = st.sidebar.text_input("Local actor", value=getpass.getuser(), key=key("actor"))
    demo_registry = None
    if bundle.name == PUBLIC_DEMO_BUNDLE or st.sidebar.checkbox("Public demo mode", key=key("demo_mode")):
        try:
            from nightdesk.demo import check_demo
            demo_registry = check_demo(PUBLIC_DEMO_MANIFEST, bundle)
            st.sidebar.caption("Public demo: hashed manifest assets only; text proposals use local replay.")
        except (ValueError, OSError) as exc:
            st.error("Public demo refused: " + str(exc))
            st.stop()
    if key("flash") in st.session_state:
        st.success(st.session_state.pop(key("flash")))
    with st.sidebar.expander("Import local file"):
        file = st.text_input("Input file", key=key("input_file"))
        mapping = st.text_input("Mapping YAML", key=key("mapping_file"))
        if st.button("Confirm mapping", key=key("confirm_mapping")):
            try:
                if demo_registry: demo_registry.require(mapping)
                sha = confirm_mapping(mapping, bundle, actor)
                st.success("Confirmed " + sha)
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if st.button("Import file", key=key("import_file")):
            try:
                if demo_registry:
                    demo_registry.require(file); demo_registry.require(mapping)
                result = ingest(file, mapping, bundle)
                if result.get("record_type") == "JourneyLinkMember":
                    import_links(bundle, result["capture_id"])
                st.session_state[key("flash")] = f"Imported: accepted={result['accepted']}, rejected={result['rejected']}; source remains available."
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(str(exc))
    with st.sidebar.expander("Import declared capture"):
        manifest = st.text_input("Capture manifest YAML", key=key("manifest"))
        if st.button("Confirm capture mappings", key=key("confirm_batch")):
            try:
                if demo_registry: demo_registry.require(manifest)
                confirm_batch(manifest, bundle, actor)
                st.success("Confirmed the declared mappings in this bundle.")
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if st.button("Import capture", key=key("import_batch")):
            try:
                if demo_registry: demo_registry.require(manifest)
                result = ingest_batch(manifest, bundle)
                for identifier in result["children"].values():
                    from nightdesk.desk import snapshot
                    if snapshot(bundle, identifier)["metadata"]["record_type"] == "JourneyLinkMember":
                        import_links(bundle, identifier)
                st.session_state[key("flash")] = "Imported declared capture: " + result["metadata"]["label"]
                st.rerun()
            except (ValueError, OSError) as exc:
                st.error(str(exc))
    render_text_intake(bundle, actor, key, demo_registry=demo_registry)
    try:
        reader = ReadSession(bundle)
        imported = captures(bundle, reader=reader) + batches(bundle, reader=reader)
    except (ValueError, OSError) as exc:
        st.error("Cannot read this bundle: " + str(exc))
        st.stop()
    by_id = {c["capture"].capture_id: c for c in imported}
    def caption(identifier):
        c = by_id[identifier]
        capture = c["capture"]
        state = "complete" if capture.complete else "incomplete"
        label = c["metadata"].get("label", Path(c["metadata"]["path"]).name)
        if label == "capture.json":
            label = f"{capture.dataset} · {capture.captured_at.isoformat(timespec='minutes')}"
        return f"{label} · {identifier[:10]} · {state}"
    def contains(c, record):
        return c["metadata"].get("record_type") == record or record in c["metadata"].get("record_types", [])
    path_ids = [i for i, c in by_id.items() if contains(c, "PathLeg") or c["metadata"].get("record_type") == "Batch"]
    old_id = st.sidebar.selectbox("Before capture", path_ids, index=None, format_func=caption, key=key("before"))
    new_id = st.sidebar.selectbox("After capture", path_ids, index=None, format_func=caption, key=key("after"))
    works_id = st.sidebar.selectbox("Works capture (optional)", [i for i,c in by_id.items() if contains(c, "WorkNotice")],
                                    index=None, format_func=caption, key=key("works"))
    runs_id = st.sidebar.selectbox("Run capture (optional)", [i for i,c in by_id.items() if contains(c, "RunRow")],
                                   index=None, format_func=caption, key=key("runs"))
    available_links = {link_id(link): link for link in links(bundle)}
    link_identifier = st.sidebar.selectbox("Journey link (optional)", list(available_links), index=None,
            format_func=lambda i: available_links[i].journey_id + " · " + available_links[i].basis + " · " + i[:8], key=key("link"))
    reviewed_text = st.sidebar.text_input("Boundary points I reviewed (comma separated)", key=key("points"))
    reviewed = {p.strip() for p in reviewed_text.split(",") if p.strip()}
    if not st.sidebar.checkbox("I reviewed those boundary point identities", key=key("reviewed")):
        reviewed = set()
    from nightdesk.stations import load_aliases
    alias_ids = sorted({e.payload["table_id"] for e in read_events(bundle) if e.kind == "aliases_confirmed"})
    alias_table_id = st.sidebar.selectbox("Station alias table (optional)", alias_ids, index=None,
        key=key("aliases"), help="Choose one reviewed table if this bundle contains more than one.")
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
    boundary_ids = st.sidebar.multiselect("Boundary source legs (optional)", list(boundary_options),
        format_func=boundary_options.get, key=key(f"boundary_legs:{old_id}:{new_id}"),
        help="If several source records fit the linked train or leg number, choose the intended records for each selected capture. Multiple legs of a re-entering train need explicit choices with distinct leg numbers. Otherwise the boundary stays unknown. Choices never create a journey link.")
    from nightdesk.desk import run_options
    try:
        dated_runs = run_options(bundle, [old_id, new_id, runs_id], reader=reader) if old_id and new_id else {}
    except (ValueError, OSError) as exc:
        st.error(str(exc)); dated_runs = {}
    run_selection_ids = st.sidebar.multiselect("Run observations (optional)", list(dated_runs),
        format_func=dated_runs.get, key=key(f"run_choices:{old_id}:{new_id}:{runs_id}"),
        help="Choose a source run if several trips fit a train and date. Works checks use planned times. The Run evidence tab shows scheduled, published and observed times separately.")
    queue_tab, dossier_tab, audit_tab, evidence_tab, work_tab = st.tabs(
        ["Queue", "Dossier", "Rejects and audit", "Run evidence", "Works evidence"], key=key("active_tab"), on_change="rerun")
    rows = []
    if old_id and new_id:
        try:
            rows = queue(bundle, old_id, new_id, works_capture_id=works_id, run_capture_id=runs_id,
                         link_identifier=link_identifier, reviewed_points=reviewed, boundary_revision_ids=boundary_ids, alias_table_id=alias_table_id, run_selection_ids=run_selection_ids)
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    with queue_tab:
        st.subheader("Changed between selected captures")
        st.caption("Rows absent from a partial export have unknown meaning. No automatic supersession.")
        if not old_id or not new_id:
            st.info("Import files and choose a before and after capture.")
        elif not rows:
            st.info("No comparable changed path-leg rows in these selected captures. Review rejects and completeness.")
        else:
            st.dataframe([{k:v for k,v in row.items() if k not in {"old_revision", "new_revision", "selection_revision", "leg_changes"}} for row in rows], hide_index=True)
        choices = [(row["selection_revision"], row["service_date"]) for row in rows]
        labels = {choice: rows[i]["train_no"] + " / " + choice[1] for i, choice in enumerate(choices)}
        selected = st.selectbox("Open train/date", choices, index=None, format_func=lambda c: labels[c], key=key("selected"))
    with dossier_tab:
        st.subheader("Train/date dossier")
        st.caption("Local review is not national approval. A checked boundary is not whole-journey feasibility.")
        if selected is None:
            st.info("Open a changed train/date from the queue.")
        else:
            try:
                task = next(row for row in rows if (row["selection_revision"], row["service_date"]) == selected)
                leg_choices = {leg["selection_revision"]: leg for leg in task["leg_changes"]}
                revision = selected[0]
                if len(leg_choices) > 1:
                    revision = st.selectbox("Source leg revision", list(leg_choices), index=None,
                        format_func=lambda i: leg_choices[i]["subject_key"] + " · " + i[:10], key=key("source_leg"))
                    if revision is None:
                        st.info("Choose a source leg revision to inspect. No source leg is selected automatically.")
                if revision is not None:
                    report = dossier(bundle, old_id, new_id, revision, date.fromisoformat(selected[1]),
                                     works_capture_id=works_id, run_capture_id=runs_id, link_identifier=link_identifier,
                                     reviewed_points=reviewed, boundary_revision_ids=boundary_ids, alias_table_id=alias_table_id, run_selection_ids=run_selection_ids)
                    render_dossier(bundle, report, actor, key)
            except (ValueError, OSError) as exc:
                st.error(str(exc))
    with audit_tab:
        st.subheader("Rejected rows")
        from nightdesk.audit import canonical_json
        rejected = list({canonical_json(r): r for c in imported for r in c["rejects"]}.values())
        if rejected:
            st.dataframe(rejected, hide_index=True)
        else:
            st.info("No rejected rows in this bundle.")
        st.subheader("Capture completeness")
        st.dataframe([{"capture": c["capture"].capture_id, "dataset": c["capture"].dataset,
                       "complete": c["capture"].complete, "reasons": c["capture"].incomplete_reasons} for c in imported], hide_index=True)
        st.subheader("Audit")
        st.caption("Local append-only history; a log does not prove source truth.")
        from nightdesk.audit import verify, upgrade_legacy
        copy_path = st.text_input("Audit copy file (optional, inside this bundle)", key=key("audit_copy"))
        seal = st.text_input("Trusted external audit seal (optional)", key=key("audit_seal"))
        count = st.text_input("Trusted external event count (optional)", key=key("audit_count"))
        st.caption("Use a seal and count retained before the copy was changed. A log's own hash does not prove its history or source truth.")
        if st.button("Verify audit chain", key=key("verify_audit")):
            try:
                st.json(verify(bundle, seal=seal.strip() or None, count=int(count) if count.strip() else None, copy_path=copy_path.strip() or None))
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if st.button("Upgrade preserved Phase 0 audit", key=key("upgrade_audit")):
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


def render_provenance(report):
    with st.expander("Capture provenance", expanded=True):
        for row in report["provenance"]:
            coverage = "Complete" if row["complete"] else "Partial · " + ", ".join(row["incomplete_reasons"])
            st.text(f"{row['role']} · {row['dataset']} · {row['licence']} · {row['captured_at']} · {coverage}\n"
                    f"Capture {row['capture_id']}\n{row['source']}")


def render_run_evidence(bundle, capture_id, key, reader):
    from nightdesk.desk import run_evidence, run_options
    from nightdesk.export import export_run_evidence
    st.subheader("Run evidence")
    if not capture_id:
        st.info("Choose a run capture in the sidebar.")
        return
    try:
        options = run_options(bundle, [capture_id], reader=reader)
        selection = st.selectbox("Source run", list(options), index=None, format_func=options.get,
                                 key=key(f"source_run:{capture_id}"))
        if selection is None:
            return
        report = run_evidence(bundle, capture_id, selection, reader=reader)
        render_provenance(report)
        st.caption(" · ".join(report["limits"]))
        origin = report["capture_origin"]
        if origin and origin["evidence"].get("coverage"):
            st.text(origin["evidence"]["coverage"])
        if origin and origin["evidence"].get("attribution"):
            st.text(origin["evidence"]["attribution"])
        if not report["capture"]["complete"]:
            st.warning("Partial capture: " + ", ".join(report["capture"]["incomplete_reasons"]))
        run = report["run"]
        st.text(f"{run['train_no']} · {run['service_date']} · {run['kind']}")
        labels = {"point_id": "Source point", "name": "Name", "planned_arr": "Scheduled arrival",
                  "planned_dep": "Scheduled departure", "real_arr": "Observed arrival", "real_dep": "Observed departure",
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
            st.text("Point order unresolved · " + run["unresolved"]["point_order"]["reason"])
        if report["capture"]["dataset"] == "rijden_archive":
            st.text("Stops are shown in archive file order. Interstation timing is unverified.")
        st.dataframe(display, hide_index=True)
        with st.expander("Source records and capture"):
            st.json(report)
        if st.button("Export run evidence", key=key("export_run_evidence")):
            paths = export_run_evidence(bundle, capture_id, selection)
            st.success("Saved locally: " + ", ".join(p.name for p in paths))
    except (ValueError, OSError) as exc:
        st.error("Could not open run evidence.")
        st.text(str(exc))


def render_es_run_comparison(bundle, key, reader):
    from nightdesk.es_runs import compare_runs
    from nightdesk.export import export_es_run_comparison

    with st.expander("Reviewed European Sleeper comparison"):
        path = st.text_input("Review JSON path inside this bundle", key=key("es_run_review"))
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
                {"Scheduled station": station["scheduled_name"], "Native stop ID": station["scheduled_native_stop_id"],
                 "Infrabel point": station["observed_name"],
                 **{f"{label} {side}": event[field]
                    for side in ("arrival", "departure")
                    for event in (station[side],)
                    for label, field in (("Scheduled", "scheduled"), ("Infrabel planned", "infrabel_planned"),
                                         ("Observed", "observed"), ("Same planned instant for", "schedule_agrees"))}}
                for station in report["stations"]
            ], hide_index=True)
            with st.expander("Comparison source records"):
                st.json(report)
            if st.button("Export ES comparison", key=key("export_es_run_comparison")):
                paths = export_es_run_comparison(bundle, path)
                st.success("Saved locally: " + ", ".join(p.name for p in paths))
        except (ValueError, OSError) as exc:
            st.error("Could not open reviewed ES comparison.")
            st.text(str(exc))


def render_works_evidence(bundle, capture_id, available, caption, key, reader):
    from collections import Counter
    from nightdesk.desk import works_evidence
    from nightdesk.export import export_works_evidence
    st.subheader("Works evidence")
    if not capture_id:
        st.info("Choose a works capture in the sidebar.")
        return
    capture = available[capture_id]["capture"]
    before = st.selectbox("Earlier works capture (optional)", [
        identifier for identifier, selected in available.items()
        if identifier != capture_id and selected["capture"].dataset == capture.dataset
        and selected["capture"].captured_at < capture.captured_at
    ], index=None, format_func=caption, key=key(f"works_before:{capture_id}"))
    try:
        report = works_evidence(bundle, capture_id, before, reader=reader)
        render_provenance(report)
        if not capture.complete:
            st.warning("Partial capture: " + ", ".join(capture.incomplete_reasons))
        origin = report["capture_origin"]
        if origin:
            with st.expander("Capture origin"):
                st.json(origin)
        result = report["comparison"]
        if result is not None:
            if result["reason"]:
                st.info("Comparison limit: " + result["reason"])
            groups = Counter(item["classification"] for item in result["membership_changes"])
            if groups:
                st.caption("Source window and membership findings")
                st.dataframe([{"classification": name, "records": count} for name, count in sorted(groups.items())], hide_index=True)
                classification = st.selectbox("Membership finding", sorted(groups), key=key("membership_classification"))
                selected = [row for row in result["membership_changes"] if row["classification"] == classification]
                page = evidence_page(selected, "Membership findings page", key(f"membership_page:{capture_id}:{before}:{classification}"))
                st.dataframe([{"revision": item["revision_id"], "reason": item["reason"],
                               "source row": item["source"]["record_id"]} for item in page], hide_index=True)
        query = st.text_input("Filter by work ID, line or place", key=key("work_search")).strip().casefold()
        validity = st.date_input("Validity date (optional)", value=None, key=key("work_validity"))
        keys = ("work_id", "line", "from_place", "to_place")
        records = [item for item in report["records"]
                   if (not validity or _has_validity_date(item["work"], validity))
                   and (not query or any(query in str(item["work"][field] or "").casefold() for field in keys))]
        st.caption(f"{len(records)} matching source works")
        page = evidence_page(records, "Works page", key(f"work_page:{capture_id}:{query}:{validity}"))
        st.dataframe([{field: item["work"][field] for field in (*keys, "date_start", "date_end", "effect", "description")}
                      | {"source row": item["source"]["record_id"]} for item in page], hide_index=True)
        items = {f"{item['source']['capture_id']}:{item['source']['record_id']}": item for item in page}
        chosen = st.selectbox("Inspect source work", list(items), index=None, key=key("source_work"),
                              format_func=lambda row: f"{items[row]['work']['work_id'] or 'Unknown ID'} · {row}")
        if chosen:
            st.json(items[chosen])
        if st.button("Export works evidence", key=key("export_works_evidence")):
            paths = export_works_evidence(bundle, capture_id, before)
            st.success("Saved locally: " + ", ".join(p.name for p in paths))
    except (ValueError, OSError) as exc:
        st.error("Could not open works evidence.")
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
    with st.expander("Text notice — manual entry or optional proposal"):
        st.caption("Proposals do not import a record or record a review. Every nonempty field needs an exact source quote. Missing facts stay missing.")
        st.caption("Mistral consent: " + ("allowed for this bundle" if allowed(bundle) else "off for this bundle"))
        if demo_registry:
            replay_path = st.selectbox("Public synthetic replay", demo_registry.paths("replay"), key=key("demo_replay"))
            if st.button("Replay checked notice", key=key("demo_replay_button")):
                demo_registry.require(replay_path)
                body = json.loads(replay_path.read_text())
                result = propose(bundle, body["source_text"], demo_registry.paths("text_mapping")[0], provider="replay", replay_path=replay_path)
                st.json(result)
                if not result["accepted"]: st.error("Proposal refused: " + ", ".join(result["reasons"]))
            return
        mapping = st.text_input("Text dataset mapping", key=key("text_mapping"))
        raw = st.text_area("Source notice text", key=key("notice_text"))
        provider = st.selectbox("Text proposal provider", ["off", "replay", "mistral"], key=key("text_provider"))
        replay_path = st.text_input("Replay file (local)", key=key("text_replay"))
        if st.button("Get proposal only", key=key("text_propose")):
            result = propose(bundle, raw, mapping, provider=provider, replay_path=replay_path or None)
            st.session_state[key("text_proposal_result")] = result
            if result["accepted"] and isinstance(result["proposal"], dict):
                st.session_state[key("drafted_by")] = "llm" if provider == "mistral" else "replay"
                st.session_state[key("text_fields")] = json.dumps(result["proposal"].get("fields", {}), ensure_ascii=False, indent=2)
                st.session_state[key("text_quotes")] = json.dumps(result["proposal"].get("quotes", {}), ensure_ascii=False, indent=2)
        result = st.session_state.get(key("text_proposal_result"))
        if result:
            if result["accepted"]: st.info("Proposal passed the checks. Inspect its fields and quotes before importing.")
            else: st.error("Proposal refused: " + ", ".join(result["reasons"]))
        with st.form(key("manual_text_form")):
            drafted_by = st.selectbox("Drafting origin", ["manual", "llm", "replay"], key=key("drafted_by"))
            fields = st.text_area("Work fields JSON (manual or proposed)", value="{}", key=key("text_fields"))
            quotes = st.text_area("Exact source quotes JSON, keyed by field", value="{}", key=key("text_quotes"))
            st.caption("Use canonical WorkNotice names, ISO dates, HH:MM clocks, and a declared timezone. German DD.MM.YYYY date quotes are also supported. No key is needed for manual entry.")
            if st.form_submit_button("Check and import this work locally"):
                try:
                    result = submit_text(bundle, raw, {"fields": json.loads(fields), "quotes": json.loads(quotes)}, mapping, actor=actor, mode=drafted_by)
                    if result.get("rejected"):
                        st.error("Rejected: " + ", ".join(result.get("reasons", ["record_gate_failed"])))
                    else:
                        st.session_state[key("flash")] = "Imported checked work locally; no review or national approval recorded."
                        st.rerun()
                except (ValueError, OSError):
                    st.error("Text import refused: check the mapping, fields and exact source quotes.")


def render_dossier(bundle, report, actor, key):
    st.text(report["train_no"] + " / " + report["service_date"] + " — " + report["data_label"])
    render_provenance(report)
    left, right = st.columns(2)
    with left:
        st.write("Before")
        if report["before"] is None:
            st.info("Source record not observed in the selected before capture; operational meaning unknown.")
        else:
            st.json(report["before"])
    with right:
        st.write("After")
        if report["after"] is None:
            st.info("Source record not observed in the selected after capture; operational meaning unknown.")
        else:
            st.json(report["after"])
    st.write("Source presence in each selected capture")
    st.json(report["source_presence"])
    st.caption("An absent source record does not establish cancellation or withdrawal. Null presence means comparison unavailable.")
    st.write("Operating date in each selected revision")
    st.json(report["operating_date_presence"])
    st.caption("A removed operating date is a source-field change, not an inferred cancellation.")
    st.write("Changed fields")
    st.dataframe(report["changes"]["field_diffs"], hide_index=True)
    st.write("Checks between selected captures")
    st.json({"before": report["checks_before"], "after": report["checks_after"], "work_changes": report["works_state_changes"]})
    st.write("Works exposures — evidence grades, no delay prediction")
    st.dataframe([{"grade": e["outcome"], "work_revision": e["work_revision"], "reasons": e["reasons"],
                   "overlap": e["overlap_window"]} for e in report["works_exposures"]], hide_index=True)
    st.caption(f"No-match pairs: {report['no_match_checked_pairs']} of {report['checked_pairs']} checked pairs only. No match is not safe.")
    if report["unlocated_checks_not_attached_to_train"]:
        st.warning("Unlocated works: not attached to this train; unlocated is not clear.")
        st.json(report["unlocated_checks_not_attached_to_train"])
    with st.expander("Inspect work records, sources and extra fields"):
        st.json(report["work_records"])
    with st.expander("Inspect earlier work records, run and boundary evidence"):
        st.json({"works": report["work_records_before"], "run": report["selected_run_before"], "findings": report["findings_before"]})
    with st.expander("Inspect selected run and source points"):
        st.json(report["selected_run"])
    if st.button("Ask for a delay estimate", key=key("delay_request")):
        from nightdesk.estimate import estimate_delay
        from nightdesk.audit import append_event
        refusal = estimate_delay()
        append_event(bundle, "delay_request_refused", {"revision_id": report["selection_revision"], **refusal.model_dump(mode="json")})
        st.warning(refusal.detail)
        st.text(refusal.reason_code)
        st.text(refusal.what_would_fix_it)
    st.write("Boundary checks")
    if any(f["reason"] == "unlinked" for f in report["findings"]):
        st.info("Journey not linked — boundary not checked.")
    if any(f["reason"] in {"ambiguous_boundary_leg", "boundary_leg_not_selected"} for f in report["findings"]):
        st.warning("Boundary source leg choice needed. Choose the intended before/after records in Boundary source legs.")
    for finding in report["findings"]:
        st.text(finding["result"] + (": " + finding["reason"] if finding["reason"] else ""))
        st.json(finding)
    st.write("Unknowns and assumptions")
    st.json({"unknowns": report["unknowns"], "assumptions": report["assumptions"], "capture_comparison": report["capture_comparison"]})
    st.write("Local review history and follow-ups")
    if any(d["stale"] for d in report["local_reviews"]):
        st.warning("Stale local review: another revision of this subject arrived. Review the selected evidence again.")
    st.json({"local_reviews": report["local_reviews"], "follow_ups": report["follow_ups"]})
    with st.form(key("review_form")):
        disposition = st.selectbox("Local disposition", ["needs_clarification", "accepted_locally", "rejected_locally"])
        reason = st.text_area("Local reason")
        owner = st.text_input("Question owner (optional)")
        question = st.text_area("Question (optional)")
        if st.form_submit_button("Record local review"):
            if not actor.strip() or not reason.strip() or bool(owner.strip()) != bool(question.strip()):
                st.error("Give an actor/reason and both an owner and question for a follow-up.")
            else:
                identifier = report["selection_revision"]
                record_decision(bundle, identifier, actor, disposition, reason)
                if question.strip():
                    follow_up(bundle, identifier, owner, question)
                st.session_state[key("flash")] = "Recorded local review on this revision. No national approval is implied."
                st.rerun()
    if st.button("Export local dossier", key=key("export")):
        md, js = export_dossier(report, bundle)
        st.success("Saved local Markdown and JSON dossier.")
        st.text(str(md));st.text(str(js))
        st.download_button("Download Markdown", md.read_text("utf-8"), file_name=md.name, mime="text/markdown")
        st.download_button("Download JSON", js.read_text("utf-8"), file_name=js.name, mime="application/json")


if __name__ == "__main__":
    main()
