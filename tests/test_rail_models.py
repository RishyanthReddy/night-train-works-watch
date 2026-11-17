from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from nightdesk.model import (BoundaryEvent, ChangeSet, ConsistencyFinding, Exposure, FollowUp, JourneyLink,
                             JourneyLinkMember, PathLeg, Revision, ReviewDecision, RunPoint, RunRow, Segment,
                             SourceRef, TrainRun, WorkNotice)


def source(bundle="practice", dataset="synthetic"):
    return SourceRef(bundle=bundle, dataset=dataset, record_id="syn-1", capture_id="capture-a", content_sha256="a" * 64,
                     captured_at=datetime(2026, 11, 17, tzinfo=timezone.utc), url_or_path="synthetic.csv", licence="synthetic")


def work(**kwargs):
    return WorkNotice(**(dict(work_id="syn-work", country="zz", date_start="2026-11-17", date_end="2026-11-18",
                             from_point_id="syn:a", to_point_id="syn:b", line="zz:1") | kwargs))


def leg(**kwargs):
    return PathLeg(**(dict(request_id="syn-request", network="zz", train_no="zz:1", sequence=1,
                          operating_dates=["2026-11-17"], entry=BoundaryEvent(point_id="syn:a"),
                          exit=BoundaryEvent(point_id="syn:b"), source_status="offered") | kwargs))


def test_payload_roundtrips_keep_unknowns_extra_and_raw_time():
    w = work(extra={"nested": {"unknown_col": [None, 1]}}, unresolved={"clock_from": {"raw": "", "reason": "missing_time"}})
    assert WorkNotice.model_validate_json(w.model_dump_json()) == w
    b = BoundaryEvent(raw_time="2026-10-25 02:30", timezone="Europe/Brussels", unresolved_reason="ambiguous_local_time")
    assert b.at is None and b.unresolved_reason == "ambiguous_local_time"
    assert BoundaryEvent().unresolved_reason == "missing_time"
    assert leg().entry.at is None and leg().source_status == "offered"


@pytest.mark.parametrize("factory,kwargs", [(work, {"from_point_id": "A"}), (work, {"line": "37"}),
    (leg, {"train_no": "453"}), (BoundaryEvent, {"point_id": " "}),
    (RunPoint, {"point_id": "1"}), (work, {"effect": "made-up"})])
def test_rail_schema_rejects_bare_ids_and_invalid_enums(factory, kwargs):
    with pytest.raises(ValidationError):
        factory(**kwargs)


def test_naive_boundary_rejected_but_missing_boundary_kept():
    with pytest.raises(ValidationError):
        BoundaryEvent(at="2026-11-17T10:00")
    with pytest.raises(ValidationError):
        BoundaryEvent(at="2026-11-17T10:00Z", unresolved_reason="missing_time")
    assert BoundaryEvent(at=None).at is None


def test_revision_has_typed_payload_separate_source_import_and_local_statuses():
    r = Revision(revision_id="b" * 64, subject_type="path_leg", subject_key="syn-request|zz|1", payload=leg(),
                 source=source(), identity="certain", source_status="offered", import_status="accepted")
    assert isinstance(Revision.model_validate_json(r.model_dump_json()).payload, PathLeg)
    assert r.predecessor is None
    local = ReviewDecision(revision_id=r.revision_id, actor="Person A", disposition="needs_clarification",
                           reason="Synthetic question", at=source().captured_at)
    assert r.source_status == "offered" and r.import_status == "accepted" and local.disposition == "needs_clarification"
    with pytest.raises(ValidationError):
        Revision(**(r.model_dump() | {"subject_type": "work"}))
    with pytest.raises(ValidationError):
        Revision(**(r.model_dump() | {"predecessor": r.revision_id, "predecessor_basis": "human"}))
    with pytest.raises(ValidationError):
        r.import_status = "unresolved"


def member(bundle="practice"):
    return JourneyLinkMember(source=source(bundle), journey_id="syn-journey", network="zz", train_no="zz:1", service_date_rule="*")


def test_journey_links_need_evidence_and_cannot_cross_bundles():
    good = JourneyLink(journey_id="syn-journey", members=[member()], basis="source", source=source())
    assert JourneyLink.model_validate_json(good.model_dump_json()) == good
    assert JourneyLink(journey_id="syn-journey", members=[member()], basis="human", confirmed_by="Planner")
    for kwargs in [dict(basis="source"), dict(basis="human"), dict(basis="source", source=source("es"))]:
        with pytest.raises(ValidationError):
            JourneyLink(journey_id="syn-journey", members=[member()], **kwargs)


def test_followup_cannot_invent_deadline():
    common = dict(follow_up_id="syn-question", revision_id="b" * 64, owner="Person A", question="What changed?")
    assert FollowUp(**common).deadline is None
    with pytest.raises(ValidationError):
        FollowUp(**common, deadline="2026-11-18T10:00Z")
    assert FollowUp(**common, deadline="2026-11-18T10:00Z", deadline_source=source())


def test_derived_records_carry_input_refs_and_version():
    point = RunPoint(point_id="syn:a", source=source())
    run = TrainRun(service_date="2026-11-17", train_no="zz:1", kind="scheduled", points=[point], input_refs=[source()], path_unresolved=True)
    segment = Segment(a=point, b=point, planned_s=None, input_refs=[source()])
    row = RunRow(**(point.model_dump() | dict(service_date="2026-11-17", train_no="zz:1")))
    changes = ChangeSet(old_revision="old", new_revision="new", basis="selected_pair", status="comparison_unavailable", reason="incomplete", input_refs=[source()])
    finding = ConsistencyFinding(rule="same_event", rule_version="border-v1", input_refs=[source()], result="unknown", reason="unlinked")
    exposure = Exposure(service_date=run.service_date, train_no=run.train_no, work_revision="b" * 64,
                        outcome="time_unknown", reasons=["no_pass_window"], input_refs=[source()])
    for record in [run, segment, changes, finding, exposure]:
        assert record.rule_version and record.input_refs == [source()]
        assert type(record).model_validate_json(record.model_dump_json()) == record
    assert row.source == source()


def test_canonical_defaults_do_not_share_mutable_values():
    a, b = work(), work()
    a.extra["synthetic"] = 1
    assert b.extra == {}
