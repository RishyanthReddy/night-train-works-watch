"""Plain Phase 1 queue and dossier. Styling/design research belongs to Phase 4."""

from datetime import date
import getpass
from pathlib import Path

import streamlit as st

from nightdesk.audit import read_events
from nightdesk.config import get_bundle, selected_bundle_name
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
    name = st.sidebar.text_input("Bundle", value=selected_bundle_name())
    try:
        bundle = get_bundle(name)
        bundle.real_root()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    key = lambda text: bundle.name + ":" + text
    st.sidebar.caption("NDA: data stays local" if bundle.nda else "Local practice / test bundle")
    actor = st.sidebar.text_input("Local actor", value=getpass.getuser(), key=key("actor"))
    demo_registry = None
    if st.sidebar.checkbox("Public demo mode", key=key("demo_mode")):
        try:
            from nightdesk.demo import check_demo
            demo_registry = check_demo("mappings/demo.yaml", bundle)
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
        imported = captures(bundle) + batches(bundle)
    except (ValueError, OSError) as exc:
        st.error("Cannot read this bundle: " + str(exc))
        st.stop()
    by_id = {c["capture"].capture_id: c for c in imported}
    def caption(identifier):
        c = by_id[identifier]
        state = "complete" if c["capture"].complete else "incomplete"
        return f"{c['metadata'].get('label', Path(c['metadata']['path']).name)} · {identifier[:10]} · {state}"
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
            reader = ReadSession(bundle)
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
        dated_runs = run_options(bundle, [old_id, new_id, runs_id])
    except (ValueError, OSError) as exc:
        st.error(str(exc)); dated_runs = {}
    run_selection_ids = st.sidebar.multiselect("Run observations (optional)", list(dated_runs),
        format_func=dated_runs.get, key=key(f"run_choices:{old_id}:{new_id}:{runs_id}"),
        help="Choose one source trip per train and service date when several fit. Until then works checks stay unknown; no trip is chosen automatically.")
    queue_tab, dossier_tab, audit_tab = st.tabs(["Queue", "Dossier", "Rejects and audit"], key=key("active_tab"), on_change="rerun")
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
        if st.button("Verify audit chain", key=key("verify_audit")):
            try:
                st.json(verify(bundle))
            except ValueError as exc:
                st.error(str(exc))
        if st.button("Upgrade preserved Phase 0 audit", key=key("upgrade_audit")):
            try:
                st.json(upgrade_legacy(bundle, actor))
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        st.json([event.model_dump(mode="json") for event in read_events(bundle)[-50:]])


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
