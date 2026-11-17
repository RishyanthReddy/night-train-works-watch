from datetime import date, datetime, timezone
import json

import pytest

from nightdesk.audit import append_event, read_events
from nightdesk.config import BundleError, get_bundle
from nightdesk.export import build_dossier, export_dossier
from nightdesk.model import PathLeg, SourceRef
from nightdesk.review import record_decision, follow_up
from nightdesk.store import make_revision, save_revision


def source():
    return SourceRef(bundle="practice", dataset="synthetic", record_id="syn-1", capture_id="c",
                     content_sha256="a" * 64, captured_at=datetime(2026, 11, 17, tzinfo=timezone.utc),
                     url_or_path="/synthetic/path.csv", licence="synthetic")


def pair(bundle):
    out = []
    for status in ["requested", "offered"]:
        leg = PathLeg(request_id="syn-r", network="zz", train_no="zz:1", sequence=1, operating_dates=["2026-11-17"], source_status=status)
        r, _ = make_revision(bundle, source(), leg)
        save_revision(bundle, r)
        append_event(bundle, "revision_created", {"revision_id": r.revision_id})
        out.append(r)
    return out


def test_dossier_local_review_unknowns_sources_and_exports(tmp_path):
    bundle = get_bundle("practice", out_root=tmp_path)
    old, new = pair(bundle)
    record_decision(bundle, new.revision_id, "Planner", "needs_clarification", "Synthetic local decision")
    follow_up(bundle, new.revision_id, "Person A", "<script>bad()</script> ![x](https://evil)")
    report = build_dossier(bundle, old, new, date(2026, 11, 17))
    assert report["data_label"] == "synthetic"
    assert report["after"]["source_status"] == "offered"
    assert report["local_reviews"][0]["disposition"] == "needs_clarification"
    assert report["follow_ups"][0]["deadline"] is None
    assert report["unknowns"] == ["no_scheduled_or_observed_run_selected", "border_not_checked"]
    md, js = export_dossier(report, bundle)
    assert json.loads(js.read_text()) == report
    assert "<script>" not in md.read_text() and "![x](https://evil)" not in md.read_text()
    assert "row" not in report["after"]["payload"]
    assert "syn-1" in md.read_text() and "capture=c" in md.read_text()
    assert export_dossier(report, bundle) == (md, js)
    assert read_events(bundle)[-1].kind == "dossier_exported"
    with pytest.raises(BundleError):
        export_dossier(report, bundle, tmp_path / "es")


def test_cross_bundle_or_modified_dossier_sources_refused(tmp_path):
    bundle = get_bundle("practice", out_root=tmp_path)
    old, new = pair(bundle)
    with pytest.raises(ValueError, match="stored_evidence"):
        build_dossier(bundle, old, new.model_copy(update={"source_status": "fabricated"}), date(2026, 11, 17))
    report = build_dossier(bundle, old, new, date(2026, 11, 17))
    report["after"]["source"]["bundle"] = "es"
    with pytest.raises(ValueError, match="cross_bundle"):
        export_dossier(report, bundle)
