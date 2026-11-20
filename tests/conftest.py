"""Shared test setup.

Keys are read from .env at command start and from the macOS Keychain, so a
developer who has saved their own keys would otherwise change what the tests
see. Point every test at key files that do not exist and switch the Keychain off.
"""

import pytest


@pytest.fixture(autouse=True)
def _no_local_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("NIGHTDESK_ENV_FILE", str(tmp_path / "no-such.env"))
    monkeypatch.setenv("NIGHTDESK_MACHINE_ENV_FILE", str(tmp_path / "no-machine.env"))
    monkeypatch.setenv("NIGHTDESK_KEYCHAIN", "off")
