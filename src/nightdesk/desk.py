"""Application selections for the plain queue/dossier. Core logic stays out of UI."""

from nightdesk.border import check_boundary, BORDER_RULE_VERSION
from nightdesk.changes import compare_captures, compare_revisions
from nightdesk.export import build_dossier
from nightdesk.intake.mapping import captures, load_capture
from nightdesk.links import load_link, coverage_by_train, link_id
from nightdesk.model import PathLeg, RunRow, ConsistencyFinding
from nightdesk.runs import build_runs, segments
from nightdesk.match import MATCH_RULE_VERSION
from nightdesk.store import load_revision, ReadSession


def snapshot(bundle, capture_id, *, reader=None):
    reader = reader or ReadSession(bundle)
    reader.check_bundle(bundle)
    import re
    if not re.fullmatch(r"[a-f0-9]{64}", capture_id):
        raise ValueError("invalid_capture_id")
    if (bundle.root / "batches" / capture_id).exists():
        from nightdesk.intake.batch import load_batch
        return load_batch(bundle, capture_id, reader=reader)
    return load_capture(bundle.root / "captures" / capture_id, bundle, reader=reader)


def snapshot_revisions(bundle, capture_id, *, reader=None):
    reader = reader or ReadSession(bundle)
    selected = snapshot(bundle, capture_id, reader=reader)
    revisions = [load_revision(bundle, identifier, reader=reader) for identifier in selected["capture"].revision_ids]
    if any(r.source.dataset != selected["capture"].dataset for r in revisions):
        raise ValueError("capture_revision_dataset_mismatch")
    return revisions


def selected_pairs(bundle, old_capture, new_capture, *, changed_only=True, include_one_sided=False, reader=None):
    reader = reader or ReadSession(bundle)
    old, new = snapshot_revisions(bundle, old_capture, reader=reader), snapshot_revisions(bundle, new_capture, reader=reader)
    def index(rows):
        out = {}
        for revision in rows:
            key = (revision.source.dataset, revision.subject_type, revision.subject_key)
            if key in out:
                raise ValueError("ambiguous_subjects_in_selected_capture")
            out[key] = revision
        return out
    a, b = index(old), index(new)
    keys = a.keys() | b.keys() if include_one_sided else a.keys() & b.keys()
    pairs = []
    for key in sorted(keys):
        left, right = a.get(key), b.get(key)
        if not isinstance((right or left).payload, PathLeg):
            continue
        if left and right and changed_only and not compare_revisions(left, right).field_diffs:
            continue
        pairs.append((left, right))
    return pairs


def _context(bundle, capture_id, *, works_id=None, run_id=None, reader=None, alias_table_id=None):
    reader = reader or ReadSession(bundle)
    selected = snapshot(bundle, capture_id, reader=reader)
    records = snapshot_revisions(bundle, capture_id, reader=reader)
    works_capture = snapshot(bundle, works_id, reader=reader) if works_id else selected
    works = snapshot_revisions(bundle, works_id, reader=reader) if works_id else records
    runs_capture = snapshot(bundle, run_id, reader=reader) if run_id else selected
    from nightdesk.stations import load_aliases
    return {"resolver": load_aliases(bundle, alias_table_id, reader=reader), "capture": selected["capture"], "legs": [r for r in records if isinstance(r.payload, PathLeg)],
            "works": [r for r in works if r.subject_type == "work"], "works_capture": works_capture["capture"],
            "runs": build_runs([r for r in runs_capture.get("typed_rows", []) if isinstance(r, RunRow)])}


def _index_context(context):
    """Index this selected capture once; there is no cross-operation cache."""
    if "legs_by_sequence" in context:
        return
    from collections import defaultdict
    by_sequence, run_index = defaultdict(list), defaultdict(list)
    sequences, positions = {}, {}
    for position, leg in enumerate(context["legs"]):
        sequence = leg.payload.sequence
        sequences[leg.revision_id] = sequence
        positions[leg.revision_id] = position
        if sequence is not None:
            by_sequence[sequence].append(leg)
    for run in context["runs"]:
        run_index[(run.train_no, run.service_date)].append(run)
    context.update(legs_by_sequence=by_sequence, leg_sequences=sequences,
                   leg_positions=positions, runs_by_train_date=run_index)


BOUNDARY_SCOPE_VERSION = "boundary-scope-v1"


def _boundary_scope(context, link, day):
    """Only explicitly linked members can be boundary candidates.

    The cache belongs to this operation's context and holds its link object.
    Operating dates are compared by the boundary rule, not filtered here:
    otherwise a removed operating date would hide its mismatch.
    """
    key = (id(link), day)
    cache = context.setdefault("boundary_scopes", {})
    if key in cache:
        return cache[key]
    from collections import defaultdict
    coverage = coverage_by_train(link, day)
    choices = context.get("boundary_revision_ids", frozenset())
    present, missing = defaultdict(list), defaultdict(list)
    ambiguous = {}
    excluded = defaultdict(list)
    def choose_members(legs):
        members = defaultdict(list)
        for leg in legs:
            members[(leg.payload.network, leg.payload.train_no)].append(leg)
        selected = []
        for candidates in members.values():
            chosen = [leg for leg in candidates if leg.revision_id in choices]
            if chosen:
                for leg in candidates:
                    if leg.revision_id not in choices and leg.payload.sequence is not None:
                        excluded[leg.payload.sequence].append(leg)
            candidates = chosen or candidates
            sequences = [leg.payload.sequence for leg in candidates]
            explicit_distinct_legs = bool(chosen) and None not in sequences and len(set(sequences)) == len(sequences)
            if len(candidates) > 1 and not explicit_distinct_legs:
                ambiguous.update({leg.revision_id: len(candidates) for leg in candidates})
            selected.extend(candidates)
        return selected
    eligible = [leg for leg in context["legs"]
        if coverage.get((leg.payload.network, leg.payload.train_no), (False, None))[0]]
    for leg in choose_members(eligible):
        if coverage.get((leg.payload.network, leg.payload.train_no), (False, None))[0]:
            sequence = context["leg_sequences"][leg.revision_id]
            if sequence is not None:
                present[sequence].append(leg)
    absent = [leg for legs in context.get("missing_legs_by_sequence", {}).values() for leg in legs
        if coverage.get((leg.payload.network, leg.payload.train_no), (False, None))[0]]
    for leg in choose_members(absent):
        missing[leg.payload.sequence].append(leg)
    # Only an explicit choice can narrow competing source legs. Request ids
    # may differ between networks and never establish a journey by themselves.
    for groups in (present, missing):
        for sequence, legs in groups.items():
            chosen = [leg for leg in legs if leg.revision_id in choices]
            if chosen:
                excluded[sequence].extend(leg for leg in legs if leg.revision_id not in choices)
                groups[sequence] = chosen
    scope = {"link": link, "link_id": link_id(link), "coverage": coverage,
             "present": present, "missing": missing, "ambiguous": ambiguous, "excluded": excluded}
    cache[key] = scope
    return scope


def _boundary_findings(revision, day, context, link, reviewed_points):
    def unknown(reason, **detail):
        refs = [revision.source]
        if link and link.source:
            refs.append(link.source)
        return ConsistencyFinding(rule="boundary_check_scope", rule_version=BOUNDARY_SCOPE_VERSION,
            input_refs=refs, result="unknown", reason=reason,
            detail={"service_date": day.isoformat(), "selected_capture": context["capture"].capture_id,
                    "limits": "No boundary pair checked; no current event or cancellation inferred.", **detail})
    if revision.identity != "certain":
        return [unknown("identity_uncertain")]
    if link is None:
        return [unknown("unlinked")]
    _index_context(context)
    scope = _boundary_scope(context, link, day)
    covered, reason = scope["coverage"].get((revision.payload.network, revision.payload.train_no), (False, "unlinked"))
    if not covered:
        return [unknown(reason)]
    sequence = context["leg_sequences"].get(revision.revision_id)
    if sequence is None:
        return [unknown("leg_sequence_unknown")]
    own_group = scope["present"].get(sequence, [])
    if not any(leg.revision_id == revision.revision_id for leg in own_group):
        return [unknown("boundary_leg_not_selected", sequence=sequence)]
    own_count = max(len(own_group), scope["ambiguous"].get(revision.revision_id, 0))
    if own_count != 1:
        return [unknown("ambiguous_boundary_leg", sequence=sequence, candidate_count=own_count)]
    pairs, findings = [], []
    for neighbor_sequence in (sequence - 1, sequence + 1):
        neighbors = scope["present"].get(neighbor_sequence, [])
        count = max([len(neighbors), *(scope["ambiguous"].get(leg.revision_id, 0) for leg in neighbors)])
        if count > 1:
            findings.append(unknown("ambiguous_boundary_leg", sequence=neighbor_sequence, candidate_count=count))
        elif neighbors:
            neighbor = neighbors[0]
            pairs.append((neighbor, revision) if neighbor_sequence < sequence else (revision, neighbor))
        if not neighbors and scope["excluded"].get(neighbor_sequence):
            findings.append(unknown("boundary_leg_not_selected", sequence=neighbor_sequence))
        missing = scope["missing"].get(neighbor_sequence, [])
        count = max([len(missing), *(scope["ambiguous"].get(leg.revision_id, 0) for leg in missing)])
        if count > 1:
            findings.append(unknown("ambiguous_boundary_leg", sequence=neighbor_sequence,
                                    candidate_count=count, evidence="other_selected_capture"))
        elif missing:
            leg = missing[0]
            if leg.payload.network != revision.payload.network:
                findings.append(ConsistencyFinding(rule="adjacent_leg_presence", rule_version="border-presence-v1",
                    input_refs=[revision.source, leg.source, *(member.source for member in link.members)],
                    result="unknown", reason="adjacent_leg_not_observed", detail={
                        "service_date": day.isoformat(), "selected_capture": context["capture"].capture_id,
                        "other_capture_revision": leg.revision_id,
                        "limits": "Neighbour evidence is from the other selected capture; no current boundary check or cancellation is inferred."}))
    positions = context["leg_positions"]
    pairs.sort(key=lambda pair: (positions[pair[0].revision_id], positions[pair[1].revision_id]))
    return [check_boundary(a, b, day, link=link, reviewed_points=reviewed_points,
                left_capture=context["capture"], right_capture=context["capture"]) for a, b in pairs] + findings


def run_choice_id(run):
    """A selection key for one dated source observation, never a guessed join."""
    from nightdesk.store import hash_value
    return hash_value({"train": run.train_no, "date": run.service_date.isoformat(), "kind": run.kind,
        "trip_id": run.trip_id, "refs": [(r.dataset,r.capture_id,r.record_id,r.content_sha256) for r in run.input_refs]})


def run_options(bundle, capture_ids):
    reader = ReadSession(bundle)
    options = {}
    for identifier in dict.fromkeys(i for i in capture_ids if i):
        selected = snapshot(bundle, identifier, reader=reader)
        for run in build_runs([r for r in selected.get("typed_rows", []) if isinstance(r, RunRow)]):
            options[run_choice_id(run)] = f"{run.train_no} / {run.service_date} / {run.kind} / trip {run.trip_id or 'not stated'} / {identifier[:10]}"
    return options


def _checks(revision, day, context, link, reviewed_points, *, run_train=None):
    from nightdesk.match import match_work
    if revision is None:
        return {"run": None, "works": {}, "findings": [], "summary": {
            "works": {grade: 0 for grade in ("A", "B", "time_unknown", "unlocated")},
            "no_match": 0, "checked_pairs": 0, "unresolved": ["leg_not_observed"], "border": []}}
    train = run_train or revision.payload.train_no
    _index_context(context)
    candidates = context["runs_by_train_date"].get((train, day), [])
    choices = context.get("run_selection_ids", frozenset())
    chosen = [run for run in candidates if run_choice_id(run) in choices]
    run = chosen[0] if len(chosen) == 1 else candidates[0] if len(candidates) == 1 and not chosen else None
    run_reason = "run_selection_required" if len(candidates) > 1 and len(chosen) != 1 else "no_run_selected"
    points = {p.point_id for p in run.points} if run else set()
    lines = {s.line for s in segments(run) if s.line} if run else set()
    works, exposures = {}, []
    for work in context["works"]:
        exposure = match_work(work, run, resolver=context.get("resolver")) if run else None
        if exposure:
            exposures.append(exposure)
        # A verified no-match remains in the comparison state: otherwise an
        # exposure disappearing would disappear from the planner's queue too.
        works[(work.source.dataset, work.subject_key)] = {
            "outcome": exposure.outcome if exposure else "no_match" if run else "time_unknown",
            "reasons": exposure.reasons if exposure else [] if run else [run_reason],
            "overlap": exposure.model_dump(mode="json")["overlap_window"] if exposure else None,
            "place_resolution": exposure.place_resolution if exposure else {},
            "attached": bool(exposure and (exposure.outcome in {"A", "B"} or
                exposure.outcome == "time_unknown" and ({work.payload.from_point_id, work.payload.to_point_id} & points or work.payload.line in lines))),
            "revision": work.revision_id if exposure and exposure.outcome != "unlocated" else None}
    findings = _boundary_findings(revision, day, context, link, reviewed_points)
    summary = {"works": {grade: sum(e.outcome == grade for e in exposures) for grade in ("A", "B", "time_unknown", "unlocated")},
               "no_match": sum(w["outcome"] == "no_match" for w in works.values()), "checked_pairs": len(works) if run else 0,
               "unresolved": sorted({reason for w in works.values() if w["outcome"] == "time_unknown" for reason in w["reasons"]} |
                                    {f.reason for f in findings if f.result == "unknown" and f.reason}),
               "border": [{"result": f.result, "reason": f.reason} for f in findings]}
    if run is None:
        summary["unresolved"] = sorted(set(summary["unresolved"]) | {run_reason})
    summary["run_selection"] = run_choice_id(run) if run else None
    summary["run_candidates"] = [run_choice_id(r) for r in candidates] if len(candidates) > 1 else []
    return {"run": run, "works": works, "findings": findings, "summary": summary}


def _check_changes(before, after, old_context, new_context):
    from nightdesk.gates import capture_comparison_gate
    keys = before["works"].keys() & after["works"].keys()
    if capture_comparison_gate(old_context["works_capture"], new_context["works_capture"]).passed:
        keys = before["works"].keys() | after["works"].keys()
    works_changed = any(before["works"].get(k) != after["works"].get(k)
                        and (before["works"].get(k, {}).get("attached", False)
                             or after["works"].get(k, {}).get("attached", False)) for k in keys)
    border = lambda found: [(f.rule, f.result, f.reason,
        {k: v for k, v in f.detail.items() if k != "selected_capture"}) for f in found]
    return works_changed or border(before["findings"]) != border(after["findings"])


def _contexts(bundle, old_capture, new_capture, works_capture_id, run_capture_id, reader, boundary_revision_ids=None, alias_table_id=None, run_selection_ids=None):
    old_snapshot = snapshot(bundle, old_capture, reader=reader)
    old_records = snapshot_revisions(bundle, old_capture, reader=reader)
    old_context = _context(bundle, old_capture,
        works_id=None if any(r.subject_type == "work" for r in old_records) else works_capture_id,
        run_id=None if any(isinstance(r, RunRow) for r in old_snapshot.get("typed_rows", [])) else run_capture_id, reader=reader, alias_table_id=alias_table_id)
    new_context = _context(bundle, new_capture, works_id=works_capture_id, run_id=run_capture_id, reader=reader, alias_table_id=alias_table_id)
    if old_context["capture"].dataset != new_context["capture"].dataset:
        raise ValueError("capture_dataset_mismatch")
    run_choices = frozenset(run_selection_ids or ())
    allowed_runs = {run_choice_id(run) for c in (old_context,new_context) for run in c["runs"]}
    if not run_choices <= allowed_runs:
        raise ValueError("select_runs_from_these_captures")
    for c in (old_context,new_context): c["run_selection_ids"] = run_choices
    choices = frozenset(boundary_revision_ids or ())
    allowed = {leg.revision_id for context in (old_context, new_context) for leg in context["legs"]}
    if not choices <= allowed:
        raise ValueError("select_boundary_legs_from_these_captures")
    for context, other in ((old_context, new_context), (new_context, old_context)):
        context["boundary_revision_ids"] = choices
        _index_context(context)
        from collections import defaultdict
        present = {(leg.source.dataset, leg.subject_key) for leg in context["legs"]}
        missing = defaultdict(list)
        for leg in other["legs"]:
            if (leg.source.dataset, leg.subject_key) not in present and leg.payload.sequence is not None:
                missing[leg.payload.sequence].append(leg)
        context["missing_legs_by_sequence"] = missing
    return old_context, new_context


def _group_rows(rows):
    """A train/date is one task; competing source legs stay explicit inside it."""
    from nightdesk.audit import canonical_json
    grouped = {}
    for row in rows:
        grouped.setdefault((row["train_no"], row["service_date"]), []).append(row)
    result = []
    for key, legs in sorted(grouped.items()):
        row = dict(legs[0])
        row["leg_changes"] = legs
        if len(legs) > 1:
            row["change_kind"] = "multiple_source_leg_changes"
            row["changed_fields"] = sorted({field for leg in legs for field in leg["changed_fields"]})
            row["unresolved_fields"] = sorted({field for leg in legs for field in leg["unresolved_fields"]})
            row["checks_changed"] = any(leg["checks_changed"] for leg in legs)
            for field in ("before_operating", "after_operating"):
                values = [leg[field] for leg in legs]
                row[field] = True if True in values else None if None in values else False
            row["next_owner"] = "; ".join(sorted({leg["next_owner"] for leg in legs if leg["next_owner"] != "unassigned"})) or "unassigned"
            labels = {leg["local_review"] for leg in legs}
            row["local_review"] = next(iter(labels)) if len(labels) == 1 else "mixed_source_leg_reviews"
            for side in ("checks_before", "checks_after"):
                summaries = [leg[side] for leg in legs]
                row[side] = dict(summaries[0])
                row[side]["unresolved"] = sorted({reason for summary in summaries for reason in summary["unresolved"]})
                row[side]["border"] = list({canonical_json(f): f for summary in summaries for f in summary["border"]}.values())
                if any(summary[field] != summaries[0][field] for summary in summaries for field in ("works", "no_match", "checked_pairs")):
                    for field in ("works", "no_match", "checked_pairs"):
                        row[side][field] = None
                    row[side]["per_source_leg"] = [{"revision": leg["selection_revision"], "checks": leg[side]} for leg in legs]
        result.append(row)
    return result


def _audit_queue_row(row):
    return {key: [_audit_queue_row(leg) for leg in value] if key == "leg_changes" else value
            for key, value in row.items() if key not in {"next_owner", "local_review", "unresolved_fields"}}


def queue(bundle, old_capture, new_capture, *, works_capture_id=None, run_capture_id=None,
          link_identifier=None, reviewed_points=None, boundary_revision_ids=None, alias_table_id=None, run_selection_ids=None):
    """One row per selected leg/date changed by path fields or sourced checks."""
    from nightdesk.review import decisions, follow_ups
    from nightdesk.audit import append_once
    reader = ReadSession(bundle)
    reviews, questions = decisions(bundle, reader=reader), follow_ups(bundle, reader=reader)
    # Batch captures explicitly contain their old/new works and run observations.
    # A separately selected works/run capture supplies missing context or an
    # explicit after-side override; nothing chooses a newest capture implicitly.
    old_context, new_context = _contexts(bundle, old_capture, new_capture, works_capture_id, run_capture_id, reader, boundary_revision_ids, alias_table_id, run_selection_ids)
    link = load_link(bundle, link_identifier) if link_identifier else None
    rows, checked_rows = [], []
    for old, new in selected_pairs(bundle, old_capture, new_capture, changed_only=False, include_one_sided=True, reader=reader):
        anchor = new or old
        change = compare_revisions(old, new) if old and new else None
        if change is not None and change.status != "compared":
            continue
        from nightdesk.gates import capture_comparison_gate
        comparable = capture_comparison_gate(old_context["capture"], new_context["capture"]).passed
        for day in sorted({d for r in (old, new) if r for d in r.payload.operating_dates}):
            active = new if new and day in new.payload.operating_dates else old or anchor
            before = _checks(old, day, old_context, link, reviewed_points)
            after = _checks(new, day, new_context, link, reviewed_points, run_train=active.payload.train_no)
            checked_rows.append({"old_revision": old.revision_id if old else None, "new_revision": new.revision_id if new else None,
                "service_date": day.isoformat(), "before": before["summary"], "after": after["summary"],
                "works_before": [{"dataset": k[0], "subject_key": k[1], **v} for k, v in sorted(before["works"].items())],
                "works_after": [{"dataset": k[0], "subject_key": k[1], **v} for k, v in sorted(after["works"].items())]})
            checks_changed = _check_changes(before, after, old_context, new_context)
            if old and new and not change.field_diffs and not checks_changed:
                continue
            owners = sorted({f.owner for f in questions if f.revision_id in {r.revision_id for r in (old, new) if r} and f.status != "answered"})
            local = [d for d in reviews if d.revision_id == anchor.revision_id]
            kind = ("changed" if change.field_diffs else "checks_changed") if change else (
                "source_record_added" if new else "source_record_removed") if comparable else "record_presence_unknown"
            rows.append({"train_no": active.payload.train_no, "service_date": day.isoformat(),
                         "before_operating": day in old.payload.operating_dates if old else False if comparable else None,
                         "after_operating": day in new.payload.operating_dates if new else False if comparable else None,
                         "old_revision": old.revision_id if old else None, "new_revision": new.revision_id if new else None,
                         "selection_revision": anchor.revision_id, "subject_key": anchor.subject_key, "change_kind": kind,
                         "changed_fields": [d.field for d in change.field_diffs] if change else ["source_presence"] if comparable else [], "checks_changed": checks_changed,
                         "checks_before": before["summary"], "checks_after": after["summary"],
                         "next_owner": ", ".join(owners) or "unassigned",
                         "local_review": (local[-1].disposition + (" (stale)" if local[-1].stale else "")) if local else "not_reviewed_locally",
                         "unresolved_fields": list(anchor.payload.unresolved) + (["record_presence_unknown"] if not change and not comparable else [])})
    rows = _group_rows(rows)
    append_once(bundle, "comparison_checked", {
        "old_capture": old_capture, "new_capture": new_capture, "rule_version": "changes-v2",
        "works_capture": works_capture_id, "run_capture": run_capture_id,
        "journey_link": link_identifier, "reviewed_points": sorted(reviewed_points or set()),
        "run_selection_ids": sorted(run_selection_ids or ()), "boundary_revision_ids": sorted(boundary_revision_ids or ()), "alias_table_id": new_context["resolver"].table_id,
        "check_rule_versions": {"works": MATCH_RULE_VERSION, "border": BORDER_RULE_VERSION, "boundary_presence": "border-presence-v1", "boundary_scope": BOUNDARY_SCOPE_VERSION, "time": "time-v1"},
        "check_results": checked_rows,
        "changes": [_audit_queue_row(row) for row in rows]})
    return rows


def dossier(bundle, old_capture_id, new_capture_id, new_revision_id, service_date, *,
            works_capture_id=None, run_capture_id=None, link_identifier=None, reviewed_points=None, boundary_revision_ids=None, alias_table_id=None, run_selection_ids=None, rolling_window_hours=None):
    reader = ReadSession(bundle)
    pair = next(((a, b) for a, b in selected_pairs(bundle, old_capture_id, new_capture_id, changed_only=False, include_one_sided=True, reader=reader)
                 if (b or a).revision_id == new_revision_id), None)
    if pair is None:
        raise ValueError("select_a_path_leg_from_these_captures")
    old, new = pair
    old_capture = snapshot(bundle, old_capture_id, reader=reader)["capture"]
    new_capture = snapshot(bundle, new_capture_id, reader=reader)["capture"]
    old_context, context = _contexts(bundle, old_capture_id, new_capture_id, works_capture_id, run_capture_id, reader, boundary_revision_ids, alias_table_id, run_selection_ids)
    link = load_link(bundle, link_identifier) if link_identifier else None
    active = new if new and service_date in new.payload.operating_dates else old or new
    before_checked = _checks(old, service_date, old_context, link, reviewed_points)
    # Boundary membership always uses the selected after revision, even when
    # display/run fallback for a removed date uses the before train number.
    checked = _checks(new, service_date, context, link, reviewed_points, run_train=active.payload.train_no)
    works, findings, run = context["works"], checked["findings"], checked["run"]
    report = build_dossier(bundle, old, new, service_date, run=run,
                           works=works, findings=findings, capture_comparison=compare_captures(bundle, old_capture, new_capture, reader=reader, rolling_window_hours=rolling_window_hours), reader=reader, resolver=context["resolver"])
    work_before, work_after = old_context["works_capture"], context["works_capture"]
    membership = None
    if work_before is not None and work_after is not None:
        membership = report["capture_comparison"] if (work_before.capture_id, work_after.capture_id) == (old_capture.capture_id, new_capture.capture_id) else compare_captures(
            bundle, work_before, work_after, reader=reader, rolling_window_hours=rolling_window_hours).model_dump(mode="json")
    report["work_membership_comparison"] = ({k: membership[k] for k in
        ("old_capture", "new_capture", "status", "reason", "rule_version", "membership_changes", "added", "removed")} if membership else None)
    if "run_selection_required" in checked["summary"]["unresolved"]:
        report["unknowns"] = sorted(set(report["unknowns"]) | {"run_selection_required"})
    report["checks_before"], report["checks_after"] = before_checked["summary"], checked["summary"]
    report["work_records_before"] = [r.model_dump(mode="json") for r in old_context["works"]]
    report["selected_run_before"] = before_checked["run"].model_dump(mode="json") if before_checked["run"] else None
    report["findings_before"] = [f.model_dump(mode="json") for f in before_checked["findings"]]
    labels = {r.source.licence for r in [old, new, *works, *old_context["works"]] if r is not None}
    for result in (before_checked, checked):
        if result["run"]:
            labels.update(ref.licence for ref in result["run"].input_refs)
        labels.update(ref.licence for finding in result["findings"] for ref in finding.input_refs)
    labels.update(ref["licence"] for exposure in report["works_exposures"] + report["unlocated_checks_not_attached_to_train"] for ref in exposure["input_refs"])
    report["data_label"] = "synthetic" if labels == {"synthetic"} else "see_each_source_licence"
    from nightdesk.gates import capture_comparison_gate
    keys = before_checked["works"].keys() & checked["works"].keys()
    if capture_comparison_gate(old_context["works_capture"], context["works_capture"]).passed:
        keys = before_checked["works"].keys() | checked["works"].keys()
    report["works_state_changes"] = [{"dataset": k[0], "subject_key": k[1],
        "before": before_checked["works"].get(k), "after": checked["works"].get(k)} for k in sorted(keys)
        if before_checked["works"].get(k) != checked["works"].get(k)]
    report["selections"] = {"old_capture": old_capture_id, "new_capture": new_capture_id,
                            "rolling_window_hours": rolling_window_hours,
                            "works_capture": works_capture_id, "run_capture": run_capture_id,
                            "journey_link": link_identifier, "reviewed_points": sorted(reviewed_points or set()),
                            "run_selection_ids": sorted(run_selection_ids or ()), "boundary_revision_ids": sorted(boundary_revision_ids or ()), "alias_table_id": context["resolver"].table_id}
    from nightdesk.audit import append_once
    from nightdesk.model import source_ref_payload
    refs = {r.revision_id: source_ref_payload(r.source) for r in [old, new, *works, *old_context["works"]] if r is not None}
    payload = {"selections": report["selections"], "revision_refs": refs,
               "run_refs": [source_ref_payload(ref) for ref in run.input_refs] if run else [],
               "run_refs_before": [source_ref_payload(ref) for ref in before_checked["run"].input_refs] if before_checked["run"] else [],
               "service_date": service_date.isoformat(), "checks_before": report["checks_before"], "checks_after": report["checks_after"],
               "works_state_changes": report["works_state_changes"], "findings_before": [
                    {"rule": f.rule, "result": f.result, "reason": f.reason, "input_refs": [source_ref_payload(ref) for ref in f.input_refs]} for f in before_checked["findings"]],
               "rule_versions": {"comparison": report["changes"]["rule_version"],
               "works": MATCH_RULE_VERSION, "border": BORDER_RULE_VERSION, "boundary_presence": "border-presence-v1", "boundary_scope": BOUNDARY_SCOPE_VERSION, "time": "time-v1", "runs": "runs-v1"},
               "capture_comparison": {k: report["capture_comparison"][k] for k in ("status", "reason", "rule_version", "membership_changes")},
               "work_membership_comparison": report["work_membership_comparison"],
               "exposures": [{k: e[k] for k in ("work_revision", "outcome", "reasons")} for e in report["works_exposures"] + report["unlocated_checks_not_attached_to_train"]],
               "checked_pairs": report["checked_pairs"], "no_match_checked_pairs": report["no_match_checked_pairs"],
               "findings": [{"rule": f.rule, "rule_version": f.rule_version, "result": f.result, "reason": f.reason,
                             "input_refs": [source_ref_payload(ref) for ref in f.input_refs]} for f in findings]}
    event = append_once(bundle, "dossier_checked", payload)
    report["check_audit"] = {"seq": event.seq, "hash": event.hash}
    return report
