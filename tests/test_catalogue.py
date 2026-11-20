"""The catalogue lists what was captured and never marks unclear data as publishable."""

import json

from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_catalogue


def write_capture(root, bundle, folder, *, licence, url="https://example.test/feed"):
    target = root / bundle / "source-captures" / folder
    target.mkdir(parents=True)
    (target / "payload.json").write_text("[]\n", encoding="utf-8")
    (target / "capture.json").write_text(json.dumps({
        "_capture": {"captured_at": "2026-11-20T09:00:00+00:00",
                     "filter": {},
                     "evidence": {"licence": licence, "source_url": url}},
        "results": [],
    }), encoding="utf-8")
    return target


def entry_for(root, monkeypatch, folder):
    monkeypatch.setattr(build_catalogue, "OUT_ROOT", root)
    monkeypatch.setattr(build_catalogue, "SNAPSHOT_ROOT", root / "no-snapshots")
    return build_catalogue.capture_entry(root / "practice" / "source-captures" / folder)


def test_an_unknown_licence_is_listed_but_not_publishable(tmp_path, monkeypatch):
    write_capture(tmp_path, "practice", "db-openboards-abc", licence="UNKNOWN")
    entry = entry_for(tmp_path, monkeypatch, "db-openboards-abc")
    assert entry["licence"] == "UNKNOWN"
    assert entry["redistributable"] is False
    assert entry["files"][0]["name"] == "payload.json"
    assert len(entry["files"][0]["sha256"]) == 64


def test_cc0_and_cc_by_are_publishable(tmp_path, monkeypatch):
    write_capture(tmp_path, "practice", "infrabel-works-abc", licence="CC0")
    write_capture(tmp_path, "practice", "rijden-archive-abc", licence="CC BY 4.0")
    assert entry_for(tmp_path, monkeypatch, "infrabel-works-abc")["redistributable"] is True
    assert entry_for(tmp_path, monkeypatch, "rijden-archive-abc")["redistributable"] is True


def test_a_missing_licence_is_treated_as_unknown(tmp_path, monkeypatch):
    write_capture(tmp_path, "practice", "ns-maintenance-abc", licence=None)
    assert entry_for(tmp_path, monkeypatch, "ns-maintenance-abc")["redistributable"] is False


def test_the_built_catalogue_separates_publishable_from_kept_local(tmp_path, monkeypatch):
    write_capture(tmp_path, "practice", "infrabel-works-abc", licence="CC0")
    write_capture(tmp_path, "practice", "swiss-siri-abc", licence="UNKNOWN")
    monkeypatch.setattr(build_catalogue, "OUT_ROOT", tmp_path)
    monkeypatch.setattr(build_catalogue, "SNAPSHOT_ROOT", tmp_path / "no-snapshots")
    catalogue = build_catalogue.build()
    marks = {e["provider"]: e["redistributable"] for e in catalogue["captures"]}
    assert marks == {"infrabel-works": True, "swiss-siri": False}
    assert "no captured data is included" in catalogue["note"]
