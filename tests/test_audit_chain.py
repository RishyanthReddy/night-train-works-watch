from datetime import datetime, timezone
import json

import pytest

from nightdesk.audit import AuditError, append_event, append_events, audit_path, event_hash, read_events, upgrade_legacy, verify
from nightdesk.cli import main
from nightdesk.config import get_bundle
from nightdesk.model import AuditEvent


def chain(bundle):
    append_events(bundle, [("one", {"n": 1}), ("two", {"n": 2}), ("three", {"n": 3})])
    return verify(bundle)


def test_chain_matches_canonical_hash_and_external_seal(tmp_path):
    b = get_bundle("practice", out_root=tmp_path)
    sealed = chain(b)
    events = read_events(b)
    assert events[0].prev_hash is None
    assert events[1].prev_hash == events[0].hash
    assert events[2].hash == event_hash(events[2])
    assert verify(b, seal=sealed["hash"], count=3)["external_seal_checked"]
    before = audit_path(b).read_bytes()
    append_event(b, "four")
    assert audit_path(b).read_bytes().startswith(before)


@pytest.mark.parametrize("attack", ["edit", "remove_middle", "remove_tail", "rewrite"])
def test_edits_missing_lines_truncation_and_full_rewrite_detected(tmp_path, attack):
    b = get_bundle("practice", out_root=tmp_path)
    sealed = chain(b)
    lines = audit_path(b).read_text().splitlines()
    if attack == "edit":
        lines[1] = lines[1].replace('"n":2', '"n":99')
    elif attack == "remove_middle":
        lines.pop(1)
    elif attack == "remove_tail":
        lines.pop()
    else:
        # Attacker recomputes a valid replacement chain, but cannot change trusted seal.
        rewritten, prev = [], None
        for line in lines:
            data = json.loads(line);data["payload"] = {"n": 99};data["prev_hash"] = prev
            event = AuditEvent.model_validate(data)
            data["hash"] = event_hash(event);prev = data["hash"]
            rewritten.append(json.dumps(data))
        lines = rewritten
    audit_path(b).write_text("\n".join(lines) + "\n")
    with pytest.raises(AuditError):
        verify(b, seal=sealed["hash"], count=sealed["count"])


def test_legacy_requires_explicit_upgrade_preserves_old_bytes(tmp_path):
    b = get_bundle("practice", out_root=tmp_path)
    b.root.mkdir()
    legacy = AuditEvent(seq=0, ts=datetime(2026, 11, 17, tzinfo=timezone.utc), bundle="practice", kind="phase0", payload={"ref": "synthetic"})
    original = b.root / "audit.jsonl"
    original.write_text(legacy.model_dump_json() + "\n")
    raw = original.read_bytes()
    with pytest.raises(AuditError, match="legacy_log_needs_upgrade"):
        append_event(b, "new")
    with pytest.raises(AuditError, match="legacy_log_needs_upgrade"):
        verify(b)
    upgraded = upgrade_legacy(b, "Planner")
    assert original.read_bytes() == raw
    assert audit_path(b).name == "audit-v1.jsonl"
    assert upgraded["count"] == 2
    assert read_events(b)[0].payload == legacy.payload
    append_event(b, "new")
    assert verify(b)["count"] == 3
    assert original.read_bytes() == raw
    assert upgrade_legacy(b, "Planner")["already_chained"]


def test_real_cli_prints_seal_then_verifies_it(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    b = get_bundle("test-cli-audit")
    sealed = chain(b)
    assert main(["audit", "seal", "--bundle", b.name]) == 0
    assert sealed["hash"] in capsys.readouterr().out
    assert main(["audit", "verify", "--bundle", b.name, "--seal", sealed["hash"], "--count", str(sealed["count"])]) == 0
    assert '"external_seal_checked": true' in capsys.readouterr().out
    assert main(["audit", "verify", "--bundle", b.name, "--seal", "f" * 64, "--count", "3"]) == 1


def test_unsealed_valid_prefix_does_not_claim_tail_check(tmp_path):
    b = get_bundle("practice", out_root=tmp_path)
    chain(b)
    lines = audit_path(b).read_text().splitlines()
    audit_path(b).write_text("\n".join(lines[:-1]) + "\n")
    assert verify(b)["external_seal_checked"] is False
    with pytest.raises(AuditError):
        verify(b, count=2)
