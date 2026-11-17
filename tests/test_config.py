from pathlib import Path

import pytest

from nightdesk.config import BundleError, get_bundle, selected_bundle_name


def test_fixed_bundles_nda_flags():
    assert get_bundle("practice").nda is False
    assert get_bundle("es").nda is True


def test_bundle_root_under_out():
    assert get_bundle("practice").root == Path("data/out/practice")


@pytest.mark.parametrize("name", ["test-a", "test-offline-p0", "test-" + "a" * 48])
def test_safe_test_bundles(name):
    b = get_bundle(name)
    assert b.nda is False
    assert b.root.name == name


@pytest.mark.parametrize(
    "name",
    ["", "ES", "other", "test-", "test--x", "test-A", "test-" + "a" * 49,
     "../practice", "test-a/../es", "test-a\n", "practice/"],
)
def test_unknown_or_unsafe_bundle_refused(name):
    with pytest.raises(BundleError):
        get_bundle(name)


def test_resolve_refuses_escape(tmp_path):
    b = get_bundle("practice", out_root=tmp_path)
    assert b.resolve(tmp_path / "practice" / "x.json") == (tmp_path / "practice" / "x.json").resolve()
    for bad in [tmp_path / "es" / "x.json", tmp_path / "practice" / ".." / "es", tmp_path / "practice-2"]:
        with pytest.raises(BundleError):
            b.resolve(bad)


def test_selected_bundle_env(monkeypatch):
    monkeypatch.delenv("NIGHTDESK_BUNDLE", raising=False)
    assert selected_bundle_name() == "practice"
    monkeypatch.setenv("NIGHTDESK_BUNDLE", "es")
    assert selected_bundle_name() == "es"
