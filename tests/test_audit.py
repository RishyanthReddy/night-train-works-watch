import json
import os
from datetime import datetime, timezone

import pytest

from nightdesk.audit import AuditError, append_event, audit_path, read_events
from nightdesk.config import BundleError, get_bundle
from nightdesk.model import SourceRef, source_ref_payload

UTC = timezone.utc


@pytest.fixture
def out(tmp_path):
    return tmp_path / "out"


def test_append_creates_and_reads(out):
    b = get_bundle("test-audit-a", out_root=out)
    e = append_event(b, "mapping_confirmed", {"sha256": "x"})
    assert e.seq == 0
    assert audit_path(b).resolve() == (out / "test-audit-a" / "audit.jsonl").resolve()
    assert read_events(b) == [e]


def test_append_preserves_prior_bytes(out):
    b = get_bundle("practice", out_root=out)
    append_event(b, "one", {"n": 1})
    before = audit_path(b).read_bytes()
    append_event(b, "two", {"n": 2})
    after = audit_path(b).read_bytes()
    assert after.startswith(before) and len(after) > len(before)
    events = read_events(b)
    assert [(e.seq, e.kind) for e in events] == [(0, "one"), (1, "two")]


def test_lines_are_canonical_json(out):
    b = get_bundle("practice", out_root=out)
    append_event(b, "k", {"z": 1, "a": "é"}, ts=datetime(2026, 11, 17, tzinfo=UTC))
    line = audit_path(b).read_text("utf-8").splitlines()[0]
    data = json.loads(line)
    assert line == json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert "é" in line


def test_bundles_isolated(out):
    p = get_bundle("practice", out_root=out)
    t = get_bundle("test-iso", out_root=out)
    append_event(p, "p")
    append_event(t, "t")
    append_event(t, "t2")
    assert [e.kind for e in read_events(p)] == ["p"]
    assert [e.kind for e in read_events(t)] == ["t", "t2"]
    assert all(e.bundle == "test-iso" for e in read_events(t))


def test_foreign_bundle_line_refused(out):
    p = get_bundle("practice", out_root=out)
    t = get_bundle("test-iso", out_root=out)
    append_event(t, "t")
    (out / "practice").mkdir(parents=True)
    audit_path(p).write_bytes(audit_path(t).read_bytes())
    with pytest.raises(AuditError):
        read_events(p)
    with pytest.raises(AuditError):
        append_event(p, "p")


def test_truncated_or_gapped_log_refused(out):
    b = get_bundle("practice", out_root=out)
    append_event(b, "k")
    path = audit_path(b)
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    with pytest.raises(AuditError):
        append_event(b, "k2")
    path.write_bytes(path.read_bytes().replace(b'"seq":0', b'"seq":5') + b"\n")
    with pytest.raises(AuditError):
        read_events(b)


def test_symlinked_root_refused(out):
    es = get_bundle("es", out_root=out)
    append_event(es, "secret")
    out.joinpath("practice").symlink_to(out / "es", target_is_directory=True)
    p = get_bundle("practice", out_root=out)
    with pytest.raises(BundleError):
        append_event(p, "x")
    with pytest.raises(BundleError):
        read_events(p)
    assert [e.kind for e in read_events(es)] == ["secret"]


def test_symlinked_audit_file_refused(out, tmp_path):
    es = get_bundle("es", out_root=out)
    append_event(es, "secret")
    (out / "practice").mkdir()
    # Points into another bundle: resolve() refuses.
    (out / "practice" / "audit.jsonl").symlink_to(out / "es" / "audit.jsonl")
    p = get_bundle("practice", out_root=out)
    with pytest.raises(BundleError):
        append_event(p, "x")
    # Points inside the root: O_NOFOLLOW still refuses writing through it.
    (out / "practice" / "audit.jsonl").unlink()
    (out / "practice" / "other.jsonl").write_bytes(b"")
    (out / "practice" / "audit.jsonl").symlink_to(out / "practice" / "other.jsonl")
    with pytest.raises(BundleError):
        append_event(p, "x")
    with pytest.raises(BundleError):
        read_events(p)
    assert (out / "practice" / "other.jsonl").read_bytes() == b""
    assert [e.kind for e in read_events(es)] == ["secret"]


def test_non_finite_payload_refused(out):
    b = get_bundle("practice", out_root=out)
    with pytest.raises(ValueError):
        append_event(b, "k", {"x": float("nan")})
    assert not audit_path(b).exists()


def test_naive_ts_refused(out):
    b = get_bundle("practice", out_root=out)
    with pytest.raises(ValueError):
        append_event(b, "k", ts=datetime(2026, 11, 17))


def test_source_reference_not_text_logged(out):
    b = get_bundle("es", out_root=out)
    ref = SourceRef(
        bundle="es", dataset="d", record_id="r1", capture_id="c1", content_sha256="b" * 64,
        captured_at=datetime(2026, 11, 17, tzinfo=UTC), url_or_path="data/raw/x.csv",
        licence="nda", field_evidence={"description": "RESTRICTED QUOTED SPAN"},
    )
    append_event(b, "ingested", {"source": source_ref_payload(ref)})
    text = audit_path(b).read_text("utf-8")
    assert "RESTRICTED QUOTED SPAN" not in text and "b" * 64 in text


def test_default_out_root_untouched(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    b = get_bundle("test-cwd")
    append_event(b, "k")
    assert (tmp_path / "data" / "out" / "test-cwd" / "audit.jsonl").is_file()
    assert os.listdir(tmp_path / "data" / "out") == ["test-cwd"]
