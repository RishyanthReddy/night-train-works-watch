"""Key setup: reading a local .env file and the doctor command."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from nightdesk.cli import main
from nightdesk.config import (CREDENTIAL_ENV_VARS, SOURCES, credential_present, env_file_path,
                              load_all_env_files, load_env_file, machine_env_file_path)


@pytest.fixture
def clean_keys(monkeypatch):
    for name in CREDENTIAL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_missing_env_file_loads_nothing_and_leaves_environment_alone(tmp_path):
    assert load_env_file(tmp_path / "absent.env") == []
    assert not any(name in os.environ for name in CREDENTIAL_ENV_VARS)


def test_env_file_sets_keys(tmp_path, clean_keys):
    path = tmp_path / ".env"
    path.write_text("# a comment\n\nNS_API_KEY=abc123\nDB_CLIENT_ID='client'\nDB_API_KEY=\"secret\"\n", encoding="utf-8")
    assert load_env_file(path) == ["NS_API_KEY", "DB_CLIENT_ID", "DB_API_KEY"]
    assert os.environ["NS_API_KEY"] == "abc123"
    assert os.environ["DB_CLIENT_ID"] == "client"
    assert os.environ["DB_API_KEY"] == "secret"


def test_empty_value_and_bare_word_are_skipped(tmp_path, clean_keys):
    path = tmp_path / ".env"
    path.write_text("NS_API_KEY=\nnot an assignment\n=orphan\nSWISS_OTD_TOKEN=  \n", encoding="utf-8")
    assert load_env_file(path) == []
    assert "NS_API_KEY" not in os.environ


def test_real_environment_wins_over_env_file(tmp_path, clean_keys):
    clean_keys.setenv("NS_API_KEY", "from-shell")
    path = tmp_path / ".env"
    path.write_text("NS_API_KEY=from-file\n", encoding="utf-8")
    assert load_env_file(path) == []
    assert os.environ["NS_API_KEY"] == "from-shell"


def test_export_prefix_is_tolerated(tmp_path, clean_keys):
    path = tmp_path / ".env"
    path.write_text("export TRAIN_ARCHIVE_TOKEN=token\n", encoding="utf-8")
    assert load_env_file(path) == ["TRAIN_ARCHIVE_TOKEN"]
    assert os.environ["TRAIN_ARCHIVE_TOKEN"] == "token"


def test_credential_present_never_returns_the_value(clean_keys):
    for name in CREDENTIAL_ENV_VARS:
        assert credential_present(name) is False
    clean_keys.setenv("NS_API_KEY", "")
    assert credential_present("NS_API_KEY") is False
    clean_keys.setenv("NS_API_KEY", "has space")
    assert credential_present("NS_API_KEY") is False
    clean_keys.setenv("NS_API_KEY", "value\x1f")
    assert credential_present("NS_API_KEY") is False
    clean_keys.setenv("NS_API_KEY", "good-key-123")
    assert credential_present("NS_API_KEY") is True


def test_env_file_path_defaults_to_dot_env(monkeypatch):
    monkeypatch.delenv("NIGHTDESK_ENV_FILE", raising=False)
    assert env_file_path() == ".env"
    monkeypatch.setenv("NIGHTDESK_ENV_FILE", "/tmp/other.env")
    assert env_file_path() == "/tmp/other.env"


def test_project_env_file_wins_over_the_machine_file(tmp_path, clean_keys):
    project, machine = tmp_path / "project.env", tmp_path / "machine.env"
    project.write_text("NS_API_KEY=from-project\n", encoding="utf-8")
    machine.write_text("NS_API_KEY=from-machine\nTRAIN_ARCHIVE_TOKEN=machine-token\n", encoding="utf-8")
    clean_keys.setenv("NIGHTDESK_ENV_FILE", str(project))
    clean_keys.setenv("NIGHTDESK_MACHINE_ENV_FILE", str(machine))
    loaded = load_all_env_files()
    assert loaded[project] == ["NS_API_KEY"]
    assert loaded[machine] == ["TRAIN_ARCHIVE_TOKEN"]
    assert os.environ["NS_API_KEY"] == "from-project"
    assert os.environ["TRAIN_ARCHIVE_TOKEN"] == "machine-token"


def test_machine_file_defaults_under_the_home_directory(monkeypatch):
    monkeypatch.delenv("NIGHTDESK_MACHINE_ENV_FILE", raising=False)
    assert machine_env_file_path() == Path.home() / ".agents" / "secrets" / "nightdesk.env"


def test_machine_file_is_read_without_a_project_file(tmp_path, clean_keys, capsys):
    machine = tmp_path / "machine.env"
    machine.write_text("SWISS_OTD_TOKEN=machine-value\n", encoding="utf-8")
    clean_keys.setenv("NIGHTDESK_MACHINE_ENV_FILE", str(machine))
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "machine-value" not in out
    assert "needs SWISS_OTD_TOKEN" not in out


def test_doctor_reports_ready_and_missing_without_printing_values(clean_keys, capsys):
    clean_keys.setenv("NS_API_KEY", "sentinel-value-must-not-appear")
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "sentinel-value-must-not-appear" not in out
    assert "NS_API_KEY" not in out  # present keys are not listed as a problem
    assert "ready (no key needed)" in out
    for name, _, _ in SOURCES:
        assert name in out
    assert "needs DB_CLIENT_ID + DB_API_KEY" in out
    assert "needs SWISS_OTD_TOKEN" in out
    assert "needs MISTRAL_API_KEY" in out


def test_doctor_reads_keys_from_the_env_file_it_is_given(tmp_path, clean_keys, capsys):
    path = tmp_path / "keys.env"
    path.write_text("SWISS_OTD_TOKEN=abc\n", encoding="utf-8")
    assert main(["doctor", "--env", str(path)]) == 0
    out = capsys.readouterr().out
    assert f"Key file: {path}" in out
    assert "needs SWISS_OTD_TOKEN" not in out


def test_doctor_says_what_to_do_when_no_key_file_exists(tmp_path, clean_keys, capsys):
    absent = tmp_path / "absent.env"
    assert main(["doctor", "--env", str(absent)]) == 0
    out = capsys.readouterr().out
    assert "copying .env.example" in out
    assert "To unlock the rest:" in out


def test_doctor_through_the_real_entry_point(tmp_path, clean_keys):
    absent = tmp_path / "absent.env"
    result = subprocess.run(
        [sys.executable, "-m", "nightdesk.cli", "doctor", "--env", str(absent)],
        capture_output=True, text=True, check=False,
        env={k: v for k, v in os.environ.items() if k not in CREDENTIAL_ENV_VARS},
    )
    assert result.returncode == 0, result.stderr
    assert "Nightdesk setup check" in result.stdout
