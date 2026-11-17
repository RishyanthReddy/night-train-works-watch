"""Local generic comparison as escaped Markdown and source-linked JSON."""

import html
import json
import re
from pathlib import Path
from urllib.parse import quote

from nightdesk.audit import append_event
from nightdesk.config import Bundle
from nightdesk.intake.mapping import digest, write_private


def escaped(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    # Plain Markdown text never enters an HTML attribute. Preserve apostrophes;
    # escaping them as numeric entities before escaping '#' corrupts rendering.
    text = html.escape(text, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text).replace("\r", " ").replace("\n", "<br>")


def _source(row):
    if row is None:
        return "—"
    ref = row["source"]
    # Absolute local path, URL-encoded so source data cannot inject Markdown links.
    url = quote(ref["url_or_path"], safe="/") + "#" + quote(ref["record_id"], safe="")
    return (f"[{escaped(ref['record_id'])}]({url}) "
            f"dataset={escaped(ref['dataset'])}, capture={escaped(ref['capture_id'])}, "
            f"sha256={ref['content_sha256']}, licence={escaped(ref['licence'])}")


def markdown(report: dict) -> str:
    lines = ["# Generic comparison", "", f"Data: {escaped(report['data_label'])}.",
             f"Bundle: {escaped(report['bundle'])}; status: {escaped(report['status'])}; "
             f"reason: {escaped(report['reason'])}; rule: {escaped(report['rule_version'])}.", "",
             "Changed between these selected files.", ""]
    for limit in report["limits"]:
        lines.append(f"- {escaped(limit)}")
    for side in ("old", "new"):
        info = report["inputs"][side]
        lines += ["", f"{side}: mode={escaped(info['mode'])}, excluded rejected rows={len({r['row'] for r in info['rejects']})}."]
        for reject in info["rejects"]:
            lines.append(f"- Rejected row {reject['row']}: field {escaped(reject['field'])}, reason {escaped(reject['reason'])}; "
                         f"source {_source({'source': reject['source']})}.")
    labels = {"changed": "Changed", "added": "Only in selected new file (added rows)",
              "unchanged": "Unchanged", "only_in_old": "Only in selected old file (meaning unknown)"}
    for group, label in labels.items():
        lines += ["", f"## {label}: {report['counts'][group]}", ""]
        for item in report[group]:
            lines += [f"### Row {escaped(item.get('key', 'identity_uncertain'))}", "",
                      f"Before source: {_source(item['old'])}", "", f"After source: {_source(item['new'])}", ""]
            for side in ("old", "new"):
                row = item[side]
                if row:
                    for name in ("fields", "extra", "unresolved"):
                        lines.append(f"{side} {name}: {escaped(row[name])}")
            for diff in item.get("field_diffs", []):
                lines.append(f"- {escaped(diff['field'])}: {escaped(diff['old'])} → {escaped(diff['new'])}")
            lines.append("")
    return "\n".join(lines) + "\n"


def export_comparison(report: dict, bundle: Bundle, out: str | Path) -> tuple[Path, Path]:
    if report["bundle"] != bundle.name:
        raise ValueError("report belongs to another bundle")
    folder = bundle.resolve(out)
    # A separate immutable export directory avoids partial overwrites and preserves history.
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    rendered = markdown(report)
    # Address the pair by both formats, so a rendering fix preserves old exports.
    stem = "comparison-" + digest(text.encode() + b"\0" + rendered.encode())
    folder.mkdir(parents=True, exist_ok=True)
    paths = (folder / f"{stem}.md", folder / f"{stem}.json")
    for path, contents in zip(paths, (rendered, text)):
        bundle.resolve(path)
        if path.is_symlink():
            raise ValueError("export target is a symlink")
        if path.exists():
            if path.read_text("utf-8") != contents:
                raise ValueError("existing export differs; refusing to overwrite")
        else:
            write_private(path, contents)
    append_event(bundle, "comparison_exported", {"rule_version": report["rule_version"],
                                              "status": report["status"], "counts": report["counts"],
                                              "json_sha256": digest(text.encode()),
                                              "paths": [str(p) for p in paths]})
    return paths


def build_dossier(bundle: Bundle, old, new, service_date, *, run=None, works=(), findings=(), capture_comparison=None, reader=None):
    """One selected train/date, with before/after, sourced checks and local review.

    All selection is explicit. This function never chooses a latest revision or
    invents a cross-border link. Unlocated works are shown separately.
    """
    from nightdesk.changes import compare_revisions
    from nightdesk.match import check_works
    from nightdesk.model import PathLeg, ChangeSet
    from nightdesk.review import decisions, follow_ups
    from nightdesk.store import load_revision, ReadSession
    reader = reader or ReadSession(bundle)
    present = [r for r in (old, new) if r is not None]
    for revision in [*present, *works]:
        stored = load_revision(bundle, revision.revision_id, reader=reader)
        if stored != revision:
            raise ValueError("dossier_revision_differs_from_stored_evidence")
    if not present or any(not isinstance(r.payload, PathLeg) for r in present) or service_date not in {d for r in present for d in r.payload.operating_dates}:
        raise ValueError("select_a_path_leg_operating_on_service_date")
    active = next((r for r in (new, old) if r and service_date in r.payload.operating_dates), present[0])
    selected_revision = new or old
    comparable = capture_comparison is not None and capture_comparison.status == "compared"
    presence = {"before": True if old else False if comparable else None,
                "after": True if new else False if comparable else None}
    if old and new:
        changes = compare_revisions(old, new)
    else:
        changes = ChangeSet(old_revision=old.revision_id if old else None, new_revision=new.revision_id if new else None,
            basis="selected_captures", old_capture=capture_comparison.old_capture if capture_comparison else None,
            new_capture=capture_comparison.new_capture if capture_comparison else None,
            status="compared" if comparable else "comparison_unavailable",
            reason=None if comparable else capture_comparison.reason if capture_comparison else "capture_completeness_unknown",
            added=[new.revision_id] if comparable and new else [], removed=[old.revision_id] if comparable and old else [],
            affected_dates=sorted(active.payload.operating_dates) if comparable else [], input_refs=[r.source for r in present])
    refs = [r.source for r in present]
    if run is not None:
        if run.train_no != active.payload.train_no or run.service_date != service_date:
            raise ValueError("run_does_not_match_selected_train_date")
        refs += run.input_refs
    for finding in findings:
        refs += finding.input_refs
    if any(ref.bundle != bundle.name for ref in refs):
        raise ValueError("cross_bundle_dossier")
    checks = check_works(list(works), run) if run is not None else {"exposures": [], "checked_pairs": 0, "no_match_checked_pairs": 0}
    selected = {r.revision_id for r in present}
    review = [d.model_dump(mode="json") for d in decisions(bundle, reader=reader) if d.revision_id in selected]
    questions = [f.model_dump(mode="json") for f in follow_ups(bundle, reader=reader) if f.revision_id in selected]
    labels = {ref.licence for ref in refs + [r.source for r in works]}
    return {"kind": "train_date_dossier", "rule_version": "dossier-v1", "bundle": bundle.name,
            "train_no": active.payload.train_no, "service_date": service_date.isoformat(),
            "selection_revision": selected_revision.revision_id, "source_presence": presence,
            "operating_date_presence": {"before": service_date in old.payload.operating_dates if old else presence["before"],
                                        "after": service_date in new.payload.operating_dates if new else presence["after"]},
            "data_label": "synthetic" if labels == {"synthetic"} else "see_each_source_licence",
            "before": old.model_dump(mode="json") if old else None, "after": new.model_dump(mode="json") if new else None,
            "changes": changes.model_dump(mode="json"),
            "capture_comparison": capture_comparison.model_dump(mode="json") if capture_comparison else None,
            "work_records": [w.model_dump(mode="json") for w in works],
            "work_records_before": [], "selected_run_before": None, "checks_before": None, "checks_after": None,
            "works_state_changes": [], "findings_before": [],
            "selected_run": run.model_dump(mode="json") if run else None,
            "works_exposures": [e.model_dump(mode="json") for e in checks["exposures"] if e.outcome != "unlocated"],
            "unlocated_checks_not_attached_to_train": [e.model_dump(mode="json") for e in checks["exposures"] if e.outcome == "unlocated"],
            "no_match_checked_pairs": checks["no_match_checked_pairs"], "checked_pairs": checks["checked_pairs"],
            "findings": [f.model_dump(mode="json") for f in findings], "local_reviews": review, "follow_ups": questions,
            "unknowns": (["leg_not_observed_in_selected_capture; operational_meaning_unknown"] if not old or not new else []) +
                        (["record_presence_comparison_unavailable"] if (not old or not new) and not comparable else []) +
                        (["no_scheduled_or_observed_run_selected"] if run is None else []) +
                        (["border_not_checked"] if not findings else []) +
                        [f.reason for f in findings if f.result == "unknown" and f.reason] +
                        [reason for e in checks["exposures"] if e.outcome in {"B", "time_unknown", "unlocated"} for reason in e.reasons],
            "assumptions": run.extra.get("assumptions", []) if run else [],
            "limits": ["Changed between these selected revisions; no automatic supersession.",
                       "Local review is not national approval. A checked boundary is not whole-journey feasibility.",
                       "Works grades describe exposure evidence, not delay or disruption predictions.",
                       "Unlocated is not clear. No match is not safe."]}


def dossier_markdown(report: dict) -> str:
    lines = ["# Train/date dossier", "", f"Data: {escaped(report['data_label'])}.",
             f"Train: {escaped(report['train_no'])}; service date: {escaped(report['service_date'])}.", ""]
    lines += ["- " + escaped(limit) for limit in report["limits"]]
    sections = [("Before", report["before"]), ("After", report["after"]), ("Changed fields", report["changes"]),
                ("Capture completeness comparison", report["capture_comparison"]),
                ("Source presence in selected captures", report["source_presence"]),
                ("Checks before", report["checks_before"]), ("Checks after", report["checks_after"]),
                ("Work check changes", report["works_state_changes"]),
                ("Earlier work records", report["work_records_before"]), ("Earlier run evidence", report["selected_run_before"]),
                ("Earlier boundary findings", report["findings_before"]),
                ("Work records and sources", report["work_records"]), ("Selected run evidence", report["selected_run"]),
                ("Operating date in each selected revision", report["operating_date_presence"]),
                ("Works exposures", report["works_exposures"]),
                ("Unlocated — not attached to train", report["unlocated_checks_not_attached_to_train"]),
                ("Boundary findings", report["findings"]), ("Local review decisions", report["local_reviews"]),
                ("Open, answered or reopened follow-ups", report["follow_ups"]),
                ("Unknowns", report["unknowns"]), ("Assumptions", report["assumptions"])]
    for title, contents in sections:
        lines += ["", "## " + title, "", escaped(contents)]
        if title in {"Before", "After"} and contents is not None:
            lines += ["", "Source: " + _source(contents)]
    lines += ["", f"No-match pairs: {report['no_match_checked_pairs']} of {report['checked_pairs']} checked pairs only."]
    return "\n".join(lines) + "\n"


def export_dossier(report: dict, bundle: Bundle, out: str | Path | None = None):
    """Local JSON/Markdown only. No messaging, publication or national approval."""
    if report.get("bundle") != bundle.name or report.get("kind") != "train_date_dossier":
        raise ValueError("invalid_dossier_bundle_or_kind")
    def check_refs(value):
        if isinstance(value, dict):
            if {"dataset", "record_id", "capture_id", "bundle"} <= value.keys() and value["bundle"] != bundle.name:
                raise ValueError("cross_bundle_dossier_reference")
            for item in value.values():
                check_refs(item)
        elif isinstance(value, list):
            for item in value:
                check_refs(item)
    check_refs(report)
    json_text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    md_text = dossier_markdown(report)
    key = digest(json_text.encode() + b"\0" + md_text.encode())
    folder = bundle.resolve(out or bundle.root / "exports")
    folder.mkdir(parents=True, exist_ok=True)
    paths = [folder / ("dossier-" + key + suffix) for suffix in (".md", ".json")]
    for path, text in zip(paths, (md_text, json_text)):
        bundle.resolve(path)
        if path.is_symlink():
            raise ValueError("export_target_is_symlink")
        if path.exists():
            if path.read_text("utf-8") != text:
                raise ValueError("existing_dossier_differs")
        else:
            write_private(path, text)
    append_event(bundle, "dossier_exported", {"json_sha256": digest(json_text.encode()), "rule_version": report["rule_version"],
                                            "revision_ids": [report[side]["revision_id"] for side in ("before", "after") if report[side] is not None],
                                            "paths": [str(p) for p in paths]})
    return tuple(paths)
