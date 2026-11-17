from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from nightdesk.model import AuditEvent, Capture, GateResult, GenericRow, SourceRef, source_ref_payload

SHA = "a" * 64
UTC = timezone.utc


def ref(**kw):
    base = dict(
        bundle="practice", dataset="synthetic-admin", record_id="A1", capture_id="cap-1",
        content_sha256=SHA, captured_at=datetime(2026, 11, 17, 12, tzinfo=UTC),
        url_or_path="tests/fixtures/admin/admin_v1.csv", licence="synthetic",
    )
    base.update(kw)
    return SourceRef(**base)


def test_source_ref_complete():
    r = ref(field_evidence={"status": "open"})
    assert r.bundle == "practice" and r.field_evidence == {"status": "open"}


@pytest.mark.parametrize("field", ["bundle", "dataset", "record_id", "capture_id",
                                   "content_sha256", "captured_at", "url_or_path", "licence"])
def test_source_ref_missing_field_refused(field):
    data = ref().model_dump()
    del data[field]
    with pytest.raises(ValidationError):
        SourceRef(**data)


@pytest.mark.parametrize("field", ["dataset", "record_id", "capture_id", "url_or_path", "licence"])
def test_source_ref_empty_string_refused(field):
    with pytest.raises(ValidationError):
        ref(**{field: ""})


@pytest.mark.parametrize("bad", ["A" * 64, "a" * 63, "a" * 65, "g" * 64, ""])
def test_bad_sha_refused(bad):
    with pytest.raises(ValidationError):
        ref(content_sha256=bad)


@pytest.mark.parametrize("bundle", ["other", "../es", "test-", "ES"])
def test_unknown_bundle_refused(bundle):
    with pytest.raises(ValidationError):
        ref(bundle=bundle)


def test_test_bundle_accepted():
    assert ref(bundle="test-unit").bundle == "test-unit"


def test_naive_datetimes_refused():
    naive = datetime(2026, 11, 17, 12)
    with pytest.raises(ValidationError):
        ref(captured_at=naive)
    with pytest.raises(ValidationError):
        Capture(capture_id="c", bundle="practice", dataset="d", captured_at=naive)
    with pytest.raises(ValidationError):
        AuditEvent(seq=0, ts=naive, bundle="practice", kind="k")
    with pytest.raises(ValidationError):
        ref(captured_at="2026-11-17T12:00:00")


def test_aware_offset_preserved():
    cet = timezone(timedelta(hours=1))
    r = ref(captured_at="2026-11-17T12:00:00+01:00")
    assert r.captured_at.utcoffset() == cet.utcoffset(None)


def test_extra_fields_forbidden_and_frozen():
    with pytest.raises(ValidationError):
        ref(unknown="x")
    r = ref()
    with pytest.raises(ValidationError):
        r.record_id = "B2"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_json_values_refused(bad):
    with pytest.raises(ValidationError):
        GenericRow(source=ref(), fields={"x": bad})
    with pytest.raises(ValidationError):
        GenericRow(source=ref(), fields={}, extra={"nested": {"list": [1, bad]}})
    with pytest.raises(ValidationError):
        AuditEvent(seq=0, ts=datetime.now(UTC), bundle="practice", kind="k", payload={"x": [bad]})


def test_non_json_value_refused():
    with pytest.raises(ValidationError):
        GenericRow(source=ref(), fields={"x": object()})


def test_generic_row_roundtrip_keeps_extra_and_types():
    row = GenericRow(
        source=ref(),
        fields={"status": "open", "duration_s": 300, "ratio": 0.5, "flag": True, "none": None},
        extra={"notes": "synthetic row", "nested": {"a": [1, "two", {"b": None}]}},
    )
    back = GenericRow.model_validate_json(row.model_dump_json())
    assert back == row
    assert back.fields["duration_s"] == 300 and type(back.fields["duration_s"]) is int
    assert type(back.fields["flag"]) is bool
    assert back.extra["nested"] == {"a": [1, "two", {"b": None}]}


def test_mutable_defaults_not_shared():
    a = GenericRow(source=ref(), fields={})
    b = GenericRow(source=ref(), fields={})
    a.extra["x"] = 1  # frozen blocks reassignment, not mutation of the dict
    assert b.extra == {}
    c1 = Capture(capture_id="c1", bundle="practice", dataset="d", captured_at=datetime.now(UTC))
    c2 = Capture(capture_id="c2", bundle="practice", dataset="d", captured_at=datetime.now(UTC))
    c1.incomplete_reasons.append("r")
    c1.files.append(SHA)
    c1.revision_ids.append("rev")
    assert c2.incomplete_reasons == [] and c2.files == [] and c2.revision_ids == []
    e1 = AuditEvent(seq=0, ts=datetime.now(UTC), bundle="practice", kind="k")
    e1.payload["x"] = 1
    assert AuditEvent(seq=0, ts=datetime.now(UTC), bundle="practice", kind="k").payload == {}


def test_capture_defaults_and_file_shas():
    c = Capture(capture_id="c", bundle="es", dataset="d", captured_at=datetime.now(UTC))
    assert c.declared_complete is False and c.complete is False
    with pytest.raises(ValidationError):
        Capture(capture_id="c", bundle="es", dataset="d", captured_at=datetime.now(UTC), files=["nothex"])


def test_gate_result():
    g = GateResult(gate="C2", passed=False, reason_code="missing_source", detail="no SourceRef")
    assert GateResult.model_validate_json(g.model_dump_json()) == g


def test_audit_event_seq_and_hash_validated():
    with pytest.raises(ValidationError):
        AuditEvent(seq=-1, ts=datetime.now(UTC), bundle="practice", kind="k")
    with pytest.raises(ValidationError):
        AuditEvent(seq=0, ts=datetime.now(UTC), bundle="practice", kind="")
    e = AuditEvent(seq=0, ts=datetime.now(UTC), bundle="practice", kind="k")
    assert e.prev_hash is None and e.hash is None


def test_source_ref_payload_drops_quoted_text():
    r = ref(field_evidence={"notes": "RESTRICTED QUOTED SPAN"})
    payload = source_ref_payload(r)
    assert "field_evidence" not in payload
    assert "RESTRICTED QUOTED SPAN" not in str(payload)
    assert payload["content_sha256"] == SHA and payload["record_id"] == "A1"
