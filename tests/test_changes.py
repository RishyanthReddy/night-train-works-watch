from datetime import datetime, timezone

import pytest

from nightdesk.changes import compare_captures, compare_revisions, field_diffs
from nightdesk.config import get_bundle
from nightdesk.model import Capture, PathLeg, SourceRef, WorkNotice
from nightdesk.store import make_revision, save_revision


def source(dataset="synthetic", capture="c1", bundle="practice"):
    return SourceRef(bundle=bundle, dataset=dataset, record_id="syn-1", capture_id=capture,
                     content_sha256="a" * 64, captured_at=datetime(2026, 11, 17, tzinfo=timezone.utc),
                     url_or_path="synthetic", licence="synthetic")


def revision(bundle, *, capture="c1", dataset="synthetic", **updates):
    payload = PathLeg(**(dict(request_id="syn-request", network="zz", train_no="zz:1", sequence=1,
                            operating_dates=["2026-11-17"], source_status="offered") | updates))
    r, _ = make_revision(bundle, source(dataset=dataset, capture=capture, bundle=bundle.name), payload)
    return save_revision(bundle, r)[0]


def capture(*rs, complete=True, **updates):
    return Capture(**(dict(capture_id="synthetic-capture", bundle="practice", dataset="synthetic",
                          captured_at=source().captured_at, declared_complete=True, complete=complete,
                          filter={}, revision_ids=[r.revision_id for r in rs]) | updates))


def test_selected_status_change_dates_and_no_change_reimport(tmp_path):
    bundle = get_bundle("practice", out_root=tmp_path)
    a = revision(bundle)
    b = revision(bundle, capture="c2", source_status="confirmed", operating_dates=["2026-11-18"])
    c = compare_revisions(a, b)
    assert c.status == "compared" and {d.field for d in c.field_diffs} == {"source_status", "operating_dates"}
    assert [d.isoformat() for d in c.affected_dates] == ["2026-11-17", "2026-11-18"]
    assert c.input_refs == [a.source, b.source]
    same = compare_revisions(a, revision(bundle, capture="c3"))
    assert not same.field_diffs and not same.affected_dates
    assert a.predecessor is None and b.predecessor is None


def test_uncertain_or_different_subject_blocks_field_comparison(tmp_path):
    bundle = get_bundle("practice", out_root=tmp_path)
    a = revision(bundle)
    for b, status, reason in [(revision(bundle, sequence=None), "identity_uncertain", "identity_uncertain"),
                              (revision(bundle, dataset="other"), "comparison_unavailable", "different_subject"),
                              (revision(bundle, network="aa"), "comparison_unavailable", "different_subject")]:
        c = compare_revisions(a, b)
        assert c.status == status and c.reason == reason and c.field_diffs == []


def test_added_removed_only_for_two_effectively_complete_same_source_and_filter(tmp_path):
    bundle = get_bundle("practice", out_root=tmp_path)
    a, b = revision(bundle), revision(bundle, request_id="different-request")
    complete = compare_captures(bundle, capture(a), capture(b))
    assert complete.added == [b.revision_id] and complete.removed == [a.revision_id]
    for new, reason in [(capture(b, complete=False), "incomplete_capture"),
                        (capture(b, filter={"network": "zz"}), "filter_mismatch"),
                        (capture(b, dataset="different"), "dataset_mismatch")]:
        c = compare_captures(bundle, capture(a), new)
        assert c.status == "comparison_unavailable" and c.reason == reason
        assert c.added == c.removed == []


def test_capture_status_only_change_and_subject_duplicate_or_uncertain(tmp_path):
    bundle = get_bundle("practice", out_root=tmp_path)
    a, b = revision(bundle), revision(bundle, source_status="confirmed")
    c = compare_captures(bundle, capture(a), capture(b))
    assert len(c.field_diffs) == 1 and c.added == c.removed == []
    c = compare_captures(bundle, capture(a, b), capture(a))
    assert c.status == "identity_uncertain" and c.reason == "duplicate_subject"
    c = compare_captures(bundle, capture(a), capture(revision(bundle, sequence=None)))
    assert c.status == "identity_uncertain" and c.field_diffs == []


def test_deep_fields_keep_absent_vs_null_distinction():
    changes = field_diffs({"entry": {"at": None}}, {"entry": {"at": "2026-11-17T10:00Z", "point_id": None}})
    assert changes[0].field == "entry.at"
    assert changes[1].field == "entry.point_id" and not changes[1].old_present and changes[1].new_present


def test_comparison_cannot_cross_bundles(tmp_path):
    a = revision(get_bundle("practice", out_root=tmp_path))
    b = revision(get_bundle("es", out_root=tmp_path))
    assert compare_revisions(a, b).reason == "bundle_mismatch"
